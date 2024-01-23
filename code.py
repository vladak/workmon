"""
XXX
"""

import json
import ssl
import time
import traceback


import adafruit_logging as logging
import adafruit_requests
import adafruit_us100
import board
import busio

# pylint: disable=import-error
import displayio
import microcontroller
import neopixel
import supervisor
import terminalio

# For storing import exceptions so that they can be raised from main().
IMPORT_EXCEPTION = None

try:
    import wifi
except MemoryError as e:
    # Let this fall through to main() so that appropriate reset can be performed.
    IMPORT_EXCEPTION = e

# pylint: disable=import-error
import socketpool
from adafruit_display_text import label

from logutil import get_log_level
from mqtt import mqtt_client_setup

try:
    from secrets import secrets
except ImportError:
    print("WiFi credentials are kept in secrets.py, please add them there!")
    raise

# First set some parameters used for shapes and text
BORDER = 5
FONTSCALE = 2
TEXT_COLOR_BASE = 0xFFFF00
TEXT_COLOR_ALERT = 0xFF0000

BROKER_PORT = "broker_port"
LOG_TOPIC = "log_topic"
MQTT_TOPIC_ENV = "mqtt_topic_env"
MQTT_TOPIC_POWER = "mqtt_topic_power"
BROKER = "broker"
PASSWORD = "password"
SSID = "SSID"
LOG_LEVEL = "log_level"
ICON_PATH = "icon_path"
TZ = "timezone"
POWER_THRESH = "power_threshold_watts"
LAST_UPDATE_THRESH = "last_update_threshold"
CO2_THRESH = "co2_threshold"

MANDATORY_SECRETS = [
    BROKER,
    BROKER_PORT,
    MQTT_TOPIC_POWER,
    MQTT_TOPIC_ENV,
    PASSWORD,
    SSID,
    ICON_PATH,
    TZ,
    POWER_THRESH,
    LAST_UPDATE_THRESH,
    CO2_THRESH,
]

CO2 = "co2"
TEMPERATURE = "temp"
HUMIDITY = "humidity"
POWER = "power"
LAST_UPDATE = "time"
TABLE_STATE_DURATION = "table_state_duration"


def blink(pixel):
    """
    Blink the Neo pixel blue.
    """
    pixel.brightness = 0.1
    pixel.fill((0, 0, 255))
    time.sleep(0.5)
    pixel.brightness = 0


def on_message_with_env_metrics(mqtt, topic, msg):
    """
    handle messages with environment sensor metrics
    """
    logger = logging.getLogger(__name__)

    logger.debug(f"got MQTT message on {topic}: {msg}")
    try:
        metrics = json.loads(msg)
        mqtt.user_data[CO2] = metrics.get("co2_ppm")
        mqtt.user_data[TEMPERATURE] = metrics.get("temperature")
        mqtt.user_data[HUMIDITY] = metrics.get("humidity")
        mqtt.user_data[LAST_UPDATE] = time.monotonic_ns()
    except json.decoder.JSONDecodeError as e:
        logger.error(f"failed to parse {msg}: {e}")


# pylint: disable=unused-argument
def on_message_with_power(mqtt, topic, msg):
    """
    handle messages with environment sensor metrics
    """
    logger = logging.getLogger(__name__)

    logger.debug(f"got MQTT message on {topic}: {msg}")
    try:
        metrics = json.loads(msg)
        mqtt.user_data[POWER] = metrics.get("current_power")
    except json.decoder.JSONDecodeError as e:
        logger.error(f"failed to parse {msg}: {e}")


def refresh_text(
    co2_value_area, text_area, user_data, last_update_threshold, co2_threshold
):
    """
    change the contents of the text label used to draw on the display
    """

    logger = logging.getLogger(__name__)

    # Multiply in order to preserve precision over time ?
    # (time.monotonic() is float so not a good fit for long-running programs)
    if user_data.get(LAST_UPDATE) is None or (
        time.monotonic_ns() - user_data.get(LAST_UPDATE)
        > last_update_threshold * 1_000_000_000
    ):
        logger.warning(f"last update was before {last_update_threshold} seconds")
        user_data[CO2] = None
        user_data[TEMPERATURE] = None
        user_data[HUMIDITY] = None

    co2_value = user_data.get(CO2)
    if co2_value:
        co2_value_area.text = f"{co2_value} ppm"
        # Draw with different color when above certain threshold.
        if int(co2_value) > co2_threshold:
            logger.debug(f"CO2 above threshold ({co2_value} > {co2_threshold})")
            co2_value_area.color = TEXT_COLOR_ALERT
        else:
            co2_value_area.color = TEXT_COLOR_BASE
    else:
        co2_value_area.text = "N/A"

    prefix = "Temp: "
    temp = user_data.get(TEMPERATURE)
    if temp:
        # TODO: the small circle is not drawn with the current font
        temp_text = prefix + f"{temp}°C"
    else:
        temp_text = prefix + "N/A"

    prefix = "Hum: "
    val = user_data.get(HUMIDITY)
    if val:
        hum_text = prefix + f"{val}%"
    else:
        hum_text = prefix + "N/A"

    prefix = "Tbl: "
    val = user_data.get(TABLE_STATE_DURATION)
    if val:
        hrs = val // 3600
        mins = (val % 3600) // 60
        # TODO: the 02 assumes that the table will not stay in the same position for days.
        time_val = f"{hrs:02}:{mins:02}"
        table_text = prefix + f"{time_val}"
    else:
        table_text = prefix + "N/A"

    text_area.text = f"{temp_text}\n{hum_text}\n{table_text}"


def parse_time(datetime_str):
    # Extract the time part from the datetime string
    # TODO: parse this properly (ISO time) or use the 'unixtime' field of the response
    time_str = datetime_str.split("T")[1].split(".")[0]
    hour, minute, _ = map(int, time_str.split(":"))

    return hour, minute


def get_time(requests, time_url):
    """
    return current hour:minute or None
    TODO: use MQTT based time to avoid outside request
    """
    logger = logging.getLogger(__name__)

    # The default timeout is 60 seconds which is too much.
    response = requests.get(time_url, timeout=3)
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        logger.error(f"failed to parse {response.text}: {e}")
        return None

    # Parse the time from the datetime string
    current_hour, current_minute = parse_time(data["datetime"])
    # Display the time
    logger.debug("time: {:2}:{:02}".format(current_hour, current_minute))

    return current_hour, current_minute


def hard_reset(exception):
    """
    Sometimes soft reset is not enough. Perform hard reset.
    """
    print(f"Got exception: {exception}")
    reset_time = 15
    print(f"Performing hard reset in {reset_time} seconds")
    time.sleep(reset_time)
    microcontroller.reset()  # pylint: disable=no-member


def mqtt_setup(pool, user_data, mqtt_log_level):
    """
    connect to MQTT server, subscribe to the topics and setup callbacks
    """
    logger = logging.getLogger(__name__)

    broker_addr = secrets[BROKER]
    broker_port = secrets[BROKER_PORT]
    mqtt_client = mqtt_client_setup(
        pool, broker_addr, broker_port, mqtt_log_level, user_data=user_data
    )
    logger.info(f"Connecting to MQTT broker {broker_addr}:{broker_port}")
    mqtt_client.connect()
    topic = secrets[MQTT_TOPIC_ENV]
    mqtt_client.add_topic_callback(topic, on_message_with_env_metrics)
    logger.info(f"subscribing to {topic}")
    mqtt_client.subscribe(topic)
    topic = secrets[MQTT_TOPIC_POWER]
    mqtt_client.add_topic_callback(topic, on_message_with_power)
    logger.info(f"subscribing to {topic}")
    mqtt_client.subscribe(topic)
    return mqtt_client


def main():
    """
    setup and main loop
    """
    if IMPORT_EXCEPTION:
        raise IMPORT_EXCEPTION

    logger = logging.getLogger(__name__)

    # Check all mandatory secrets are present.
    for secret in MANDATORY_SECRETS:
        if secrets.get(secret) is None:
            logger.error(f"secret {secret} is missing")
            return

    log_level = get_log_level(secrets[LOG_LEVEL])
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

    logger.info("Running")

    logger.debug(f"MAC address: {wifi.radio.mac_address}")

    # Connect to Wi-Fi
    logger.info("Connecting to wifi")
    wifi.radio.connect(secrets[SSID], secrets[PASSWORD], timeout=10)
    logger.info(f"Connected to {secrets[SSID]}")
    logger.debug(f"IP: {wifi.radio.ipv4_address}")

    # Create a socket pool
    pool = socketpool.SocketPool(wifi.radio)  # pylint: disable=no-member

    user_data = {}
    mqtt_client = mqtt_setup(pool, user_data, log_level)

    uart = busio.UART(board.TX, board.RX, baudrate=9600)
    us100 = adafruit_us100.US100(uart)

    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    # This provides daylight savings time automatically.
    time_url = "https://worldtimeapi.org/api/timezone/" + secrets.get(TZ)

    # pylint: disable=no-member
    display = board.DISPLAY
    logger.debug(f"display resolution: w: {display.width} h: {display.height}")

    grp = displayio.Group()
    display.root_group = grp

    splash = displayio.Group()
    grp.append(splash)

    # Subgroup for text scaling
    text_group = displayio.Group(
        scale=FONTSCALE,
    )
    splash.append(text_group)

    text = "CO2: "
    co2_prefix_area = label.Label(terminalio.FONT, text=text, color=TEXT_COLOR_BASE)
    co2_prefix_area.anchor_point = (0, 0)
    co2_prefix_area.anchored_position = (BORDER, BORDER)
    text_group.append(co2_prefix_area)

    co2_value_area = label.Label(terminalio.FONT, text="", color=TEXT_COLOR_BASE)
    co2_value_area.anchor_point = (0, 0)
    co2_value_area.anchored_position = (
        BORDER + co2_prefix_area.bounding_box[2],
        BORDER,
    )
    text_group.append(co2_value_area)

    # remaining text
    text_area = label.Label(terminalio.FONT, text="", color=TEXT_COLOR_BASE)
    text_area.anchor_point = (0, 0)
    text_area.anchored_position = (BORDER, 2 * BORDER + co2_prefix_area.bounding_box[3])
    text_group.append(text_area)

    display_icon(display, splash)

    start_hr = secrets.get("start_hr")
    end_hr = secrets.get("end_hr")

    distance_threshold = secrets.get("distance_threshold")
    stamp = time.monotonic_ns()
    prev_table_state = None
    table_state_duration = 0

    while True:
        distance = us100.distance
        if distance > distance_threshold:
            table_state = "up"
        else:
            table_state = "down"
        logger.info(f"distance: {distance} cm (table {table_state})")
        mqtt_client.publish(
            secrets.get("mqtt_topic_distance"), json.dumps({"distance": distance})
        )

        # Record the duration of table position.
        if prev_table_state:
            if prev_table_state == table_state:
                table_state_duration += (time.monotonic_ns() - stamp) // 1_000_000_000
                logger.debug(
                    f"table state '{table_state}' preserved (for {table_state_duration} sec)"
                )
            else:
                logger.debug(f"table state changed {prev_table_state} -> {table_state}")
                table_state_duration = 0
        prev_table_state = table_state
        user_data.update({TABLE_STATE_DURATION: table_state_duration})
        stamp = time.monotonic_ns()

        # TODO:
        #   blank the display during certain hours
        #   unless a button is pressed - then leave it on for bunch of iterations
        cur_hr, _ = get_time(requests, time_url)
        if start_hr <= cur_hr < end_hr:
            display.brightness = 1
            refresh_text(
                co2_value_area,
                text_area,
                user_data,
                secrets.get(LAST_UPDATE_THRESH),
                secrets.get(CO2_THRESH),
            )
            logger.debug(f"user data = {user_data}")
            power = user_data.get(POWER)
            if power:
                if power > secrets.get(POWER_THRESH):
                    logger.debug("power on")
                    # TODO: change the icon if table in the same position above threshold
                    #       corner case: start of work in the morning
                else:
                    logger.debug("power off")
            else:
                logger.debug("power N/A")
            blink(pixel)
        else:
            logger.debug("outside of working hours, setting the display off")
            display.brightness = 0

        mqtt_client.loop(1)


def display_icon(display, splash):
    """
    Display icon in the bottom right corner.
    """

    logger = logging.getLogger(__name__)

    icon_path = secrets.get(ICON_PATH)
    try:
        with open(icon_path, "rb"):
            #
            # Technically the OnDiskBitmap should allow file object
            # for file opened in binary mode (for backward compatibility),
            # however this does not seem to be the case.
            #
            icon_bitmap = displayio.OnDiskBitmap(icon_path)
            default_tile_grid = displayio.TileGrid(
                icon_bitmap,
                pixel_shader=icon_bitmap.pixel_shader,
                x=display.width - icon_bitmap.width + 10,
                y=display.height - icon_bitmap.height,
            )
            splash.append(default_tile_grid)
    except Exception as e:
        logger.error(f"cannot display {icon_path}: {e}")


try:
    main()
except ConnectionError as e:
    # When this happens, it usually means that the microcontroller's wifi/networking is botched.
    # The only way to recover is to perform hard reset.
    hard_reset(e)
except MemoryError as e:
    # This is usually the case of delayed exception from the 'import wifi' statement,
    # possibly caused by a bug (resource leak) in CircuitPython that manifests
    # after a sequence of ConnectionError exceptions thrown from withing the wifi module.
    # Should not happen given the above 'except ConnectionError',
    # however adding that here just in case.
    hard_reset(e)
except Exception as e:  # pylint: disable=broad-except
    # This assumes that such exceptions are quite rare.
    # Otherwise, this would drain the battery quickly by restarting
    # over and over in a quick succession.
    print("Code stopped by unhandled exception:")
    print(traceback.format_exception(None, e, e.__traceback__))
    RELOAD_TIME = 10
    print(f"Performing a supervisor reload in {RELOAD_TIME} seconds")
    time.sleep(RELOAD_TIME)
    supervisor.reload()
