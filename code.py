"""
workmon main code
"""

import json
import time
import traceback

import adafruit_logging as logging
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ntp
import adafruit_us100
import board
import busio
import digitalio

# pylint: disable=import-error
import displayio
import microcontroller
import neopixel

# pylint: disable=import-error
import socketpool
import supervisor
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

from binarystate import BinaryState
from blinker import Blinker
from button import Button
from logutil import get_log_level
from mqtt import mqtt_client_setup
from timeutil import get_time

# For storing import exceptions so that they can be raised from main().
IMPORT_EXCEPTION = None

try:
    import wifi
except MemoryError as e:
    # Let this fall through to main() so that appropriate reset can be performed.
    IMPORT_EXCEPTION = e

try:
    from secrets import secrets
except ImportError:
    print("WiFi credentials are kept in secrets.py, please add them there!")
    raise

# First set some parameters used for shapes and text
BORDER = 5
TEXT_COLOR_BASE = 0xFFFF00
TEXT_COLOR_ALERT = 0xFF0000

BROKER_PORT = "broker_port"
LOG_TOPIC = "log_topic"
MQTT_TOPIC = "mqtt_topic"
MQTT_TOPIC_ENV = "mqtt_topic_env"
MQTT_TOPIC_POWER = "mqtt_topic_power"
BROKER = "broker"
PASSWORD = "password"
SSID = "SSID"
LOG_LEVEL = "log_level"
ICON_PATHS = "icon_paths"
POWER_THRESH = "power_threshold_watts"
LAST_UPDATE_THRESH = "last_update_threshold"
CO2_THRESH = "co2_threshold"
TABLE_STATE_DUR_THRESH = "table_state_dur_threshold"
FONT_FILE_NAME = "font_file_name"

MANDATORY_SECRETS = [
    BROKER,
    BROKER_PORT,
    MQTT_TOPIC,
    MQTT_TOPIC_POWER,
    MQTT_TOPIC_ENV,
    PASSWORD,
    SSID,
    ICON_PATHS,
    POWER_THRESH,
    LAST_UPDATE_THRESH,
    CO2_THRESH,
    TABLE_STATE_DUR_THRESH,
    FONT_FILE_NAME,
]

CO2 = "co2"
TEMPERATURE = "temp"
HUMIDITY = "humidity"
POWER = "power"
LAST_UPDATE = "time"
TABLE_STATE_DURATION = "table_state_duration"

TEMP_PREFIX = "Temp: "
HUM_PREFIX = "Hum: "
TBL_PREFIX = "Tbl: "

RED = (255, 0, 0)  # CO2 alert
GREEN = (0, 255, 0)  # break alert
BLUE = (0, 0, 255)  # table alert

# Higher number means higher priority.
COLOR_PRIORITY = {RED: 30, GREEN: 20, BLUE: 10}


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
    except json.decoder.JSONDecodeError as json_error:
        logger.error(f"failed to parse {msg}: {json_error}")


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
    except json.decoder.JSONDecodeError as json_error:
        logger.error(f"failed to parse {msg}: {json_error}")


def has_priority(color_current, color_new):
    """
    Check whether new color has precedence over the current color.
    """
    if color_current == color_new:
        return True

    return COLOR_PRIORITY.get(color_new) > COLOR_PRIORITY.get(color_current)


def can_blink(blinker, color):
    """
    Check whether the blinker can blink with given color based on its state
    and color priority.
    """
    if not blinker.is_blinking:
        return True

    return has_priority(blinker.color, color)


# pylint: disable=too-many-locals,too-many-branches,too-many-arguments
def refresh_text(
    co2_value_area,
    temp_area,
    hum_area,
    tbl_area,
    user_data,
    last_update_threshold,
    co2_threshold,
    blinker,
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
            if can_blink(blinker, RED):
                blinker.set_blinking(True, color=RED)
        else:
            co2_value_area.color = TEXT_COLOR_BASE
            blinker.set_blinking(False, color=RED)
    else:
        co2_value_area.text = "N/A"

    prefix = TEMP_PREFIX
    temp = user_data.get(TEMPERATURE)
    if temp:
        temp_text = prefix + f"{temp}°C"
    else:
        temp_text = prefix + "N/A"
    temp_area.text = temp_text

    prefix = HUM_PREFIX
    val = user_data.get(HUMIDITY)
    if val:
        hum_text = prefix + f"{val}%"
    else:
        hum_text = prefix + "N/A"
    hum_area.text = hum_text

    prefix = TBL_PREFIX
    val = user_data.get(TABLE_STATE_DURATION)
    if val:
        hours = val // 3600
        minutes = (val % 3600) // 60
        if hours > 24:
            time_val = f"{hours // 24} days"
        else:
            time_val = f"{hours:02}:{minutes:02}"
        table_text = prefix + f"{time_val}"
    else:
        table_text = prefix + "N/A"
    tbl_area.text = table_text


def hard_reset(exception):
    """
    Sometimes soft reset is not enough. Perform hard reset.
    """
    print(f"Got exception: {exception}")
    reset_time = 15
    print(f"Performing hard reset in {reset_time} seconds")
    time.sleep(reset_time)
    microcontroller.reset()  # pylint: disable=no-member


def mqtt_setup(pool, user_data, mqtt_log_level, socket_timeout):
    """
    connect to MQTT server, subscribe to the topics and setup callbacks
    """
    logger = logging.getLogger(__name__)

    broker_addr = secrets[BROKER]
    broker_port = secrets[BROKER_PORT]
    mqtt_client = mqtt_client_setup(
        pool,
        broker_addr,
        broker_port,
        mqtt_log_level,
        user_data=user_data,
        socket_timeout=socket_timeout,
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


def get_font(file_name):
    """
    Try to load a bitmap font. If not successful, fall back to terminal font.
    Return font and font and border scale factor.
    """

    logger = logging.getLogger(__name__)

    font = terminalio.FONT
    try:
        font_scale = 1
        border_scale = 2
        font_file = file_name
        logger.debug(f"loading font from {font_file}")
        font = bitmap_font.load_font(font_file)
        font.load_glyphs(
            # pylint: disable=line-too-long
            code_points="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890- ().,:!?/\\%+@~"
        )
        font.load_glyphs("°³µ₂")  # preload glyphs for fast printing
    # pylint: disable=broad-exception-caught
    except Exception as exception:
        border_scale = 1
        font_scale = 2
        logger.warning(f"Cannot load bitmap font, will use terminal font: {exception}")

    return font, font_scale, border_scale


# pylint: disable=too-many-locals,too-many-statements
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
    blinker = Blinker(pixel)

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
    # The timeout has to be so low for the main loop to record button presses.
    mqtt_loop_timeout = 0.05
    # pylint: disable=no-member
    mqtt_client = mqtt_setup(pool, user_data, logging.ERROR, mqtt_loop_timeout)

    logger.debug("setting NTP up")
    # The code is supposed to be running in specific time zone
    # with NTP server running on the default router.
    ntp = adafruit_ntp.NTP(pool, server=str(wifi.radio.ipv4_gateway), tz_offset=1)

    logger.debug("setting up US100")
    uart = busio.UART(board.TX, board.RX, baudrate=9600)
    us100 = adafruit_us100.US100(uart)

    # pylint: disable=no-member
    display = board.DISPLAY
    logger.debug(f"display resolution: w: {display.width} h: {display.height}")

    logger.debug("setting display elements")
    grp = displayio.Group()
    display.root_group = grp

    splash = displayio.Group()
    grp.append(splash)

    # The images should have transparent background, however that does not seem
    # to work with BMPs, so display the icon first so that the text can be displayed on the top.
    image_tile_grid = display_icon(display, None, secrets.get(ICON_PATHS)[0])
    if image_tile_grid:
        splash.append(image_tile_grid)

    font, font_scale, border_scale = get_font(secrets.get(FONT_FILE_NAME))

    # Subgroup for text scaling can be created only once a font is determined,
    # because scaling depends on the chosen font.
    text_group = displayio.Group(
        scale=font_scale,
    )
    splash.append(text_group)

    # The CO2 text has 2 groups so that the value can be displayed in different color.
    if font is terminalio.FONT:
        text = "CO2: "
    else:
        text = "CO₂: "
    co2_prefix_area = label.Label(font, text=text, color=TEXT_COLOR_BASE)
    co2_prefix_area.anchor_point = (0, 0)
    co2_prefix_area.anchored_position = (BORDER, BORDER)
    text_group.append(co2_prefix_area)

    co2_value_area = label.Label(font, text="", color=TEXT_COLOR_BASE)
    co2_value_area.anchor_point = (0, 0)
    co2_value_area.anchored_position = (
        BORDER + co2_prefix_area.bounding_box[2],
        BORDER,
    )
    y_offset = co2_prefix_area.bounding_box[3]
    text_group.append(co2_value_area)

    temp_area = label.Label(font, text=TEMP_PREFIX, color=TEXT_COLOR_BASE)
    temp_area.anchor_point = (0, 0)
    if border_scale > 1:
        border_scale += 2
    temp_area.anchored_position = (BORDER, BORDER * border_scale + y_offset)
    y_offset += temp_area.bounding_box[3]
    text_group.append(temp_area)

    hum_area = label.Label(font, text=HUM_PREFIX, color=TEXT_COLOR_BASE)
    hum_area.anchor_point = (0, 0)
    if border_scale > 1:
        border_scale += 2
    hum_area.anchored_position = (BORDER, BORDER * border_scale + y_offset)
    y_offset += hum_area.bounding_box[3]
    text_group.append(hum_area)

    tbl_area = label.Label(font, text=TBL_PREFIX, color=TEXT_COLOR_BASE)
    tbl_area.anchor_point = (0, 0)
    if border_scale > 1:
        border_scale += 2
    tbl_area.anchored_position = (BORDER, BORDER * border_scale + y_offset)
    text_group.append(tbl_area)

    start_hr = secrets.get("start_hr")
    end_hr = secrets.get("end_hr")

    distance_threshold = secrets.get("distance_threshold")
    table_state = BinaryState()

    logger.info("Setting up buttons")
    buttons = []
    # The D1/D2 buttons are pulled LOW.
    for pin, pull in [
        (board.D0, digitalio.Pull.UP),
        (board.D1, digitalio.Pull.DOWN),
        (board.D2, digitalio.Pull.DOWN),
    ]:
        button = Button(pin, pull)
        buttons.append(button)
    button_pressed_stamp = 0

    distance_stamp = 0
    logger.debug("entering main loop")
    table_state_val = None
    while True:
        button_values = [b.pressed for b in buttons]
        logger.debug(f"button pressed: {button_values}")
        if True in button_values:
            button_pressed_stamp = time.monotonic_ns() // 1_000_000_000

        #
        # Getting distance from us100 makes the code sleep for up to 2 * 2 * 0.1 seconds,
        # so this is not ideal for tight loop like this which needs to sample
        # button presses fast enough to detect them.
        # Therefore, get the distance only every 10 seconds,
        # to increase the probability of getting the button presses.
        #
        if distance_stamp < time.monotonic_ns() - 10 * 1_000_000_000:
            logger.debug("getting distance value")
            distance = us100.distance
            logger.debug(f"got distance value: {distance}")
            table_state_val = handle_distance(distance, distance_threshold, mqtt_client)
            distance_stamp = time.monotonic_ns()

        #
        # Leave the display on during certain hours unless a button is pressed.
        # Then leave it on for a minute.
        #
        cur_hr, _ = get_time(ntp)
        if (
            start_hr <= cur_hr < end_hr
            or button_pressed_stamp >= time.monotonic_ns() // 1_000_000_000 - 60
        ):
            display.brightness = 1
            refresh_text(
                co2_value_area,
                temp_area,
                hum_area,
                tbl_area,
                user_data,
                secrets.get(LAST_UPDATE_THRESH),
                secrets.get(CO2_THRESH),
                blinker,
            )
            logger.debug(f"user data = {user_data}")

            handle_power(
                blinker,
                display,
                image_tile_grid,
                table_state,
                table_state_val,
                user_data,
                mqtt_client,
                secrets.get(MQTT_TOPIC),
            )
        else:
            logger.debug("outside of working hours, setting the display off")
            display.brightness = 0

            # Deals with start of work in the morning.
            table_state.reset()
            user_data[TABLE_STATE_DURATION] = None

            blinker.set_blinking(False)

        try:
            mqtt_client.loop(mqtt_loop_timeout)
        except MQTT.MMQTTException as mqtt_exception:
            logger.error(f"MQTT error: {mqtt_exception}")
            mqtt_client.reconnect()
            mqtt_client.loop(mqtt_loop_timeout)


# pylint: disable=too-many-arguments
def handle_power(
    blinker,
    display,
    image_tile_grid,
    table_state,
    table_state_val,
    user_data,
    mqtt_client,
    topic,
):
    """
    If power is on, handle the table state.
    """

    logger = logging.getLogger(__name__)

    power = user_data.get(POWER)
    if power is None:
        logger.debug("power N/A")
        return

    if power > secrets.get(POWER_THRESH):
        logger.debug("power on")

        # pylint: disable=too-many-function-args
        handle_table_state(
            blinker,
            display,
            image_tile_grid,
            table_state,
            table_state_val,
            user_data,
            mqtt_client,
            topic,
        )
    else:
        logger.debug("power off")
        # Reset the table position tracking. If the display went off,
        # there was likely a work pause.
        # Do not set the user_data element to keep showing the last value.
        table_state.reset()
        blinker.set_blinking(False, BLUE)


# pylint: disable=too-many-arguments
def handle_table_state(
    blinker,
    display,
    image_tile_grid,
    table_state,
    table_state_val,
    user_data,
    mqtt_client,
    topic,
):
    """
    change the image based on table state duration
    """
    if table_state_val is None:
        return

    table_state_duration = table_state.update(table_state_val)
    #
    # Implementation note:
    #   The table state is smuggled into the user_data
    #   (used to stored metrics received from MQTT)
    #   so that refresh_text() has more uniform argument types.
    #
    user_data.update({TABLE_STATE_DURATION: table_state_duration})

    if user_data.get("annotation_sent") is None:
        user_data["annotation_sent"] = 0

    #
    # Change the icon and set the neopixel to blinking
    # if table state duration exceeded the threshold.
    #
    icon_path = secrets.get(ICON_PATHS)[0]
    if table_state_duration > secrets.get(TABLE_STATE_DUR_THRESH):
        icon_path = secrets.get(ICON_PATHS)[1]

        if can_blink(blinker, BLUE):
            blinker.set_blinking(True, color=BLUE)

        if (
            user_data.get("annotation_sent") // 1_000_000_000
            < time.monotonic_ns() // 1_000_000_000 - table_state_duration
        ):
            mqtt_client.publish(
                topic, json.dumps({"annotation": True, "tags": ["table_duration"]})
            )
            user_data["annotation_sent"] = time.monotonic_ns()
    else:
        blinker.set_blinking(False, color=BLUE)
        user_data["annotation_sent"] = 0
    display_icon(display, image_tile_grid, icon_path)


def handle_distance(distance, distance_threshold, mqtt_client):
    """
    publish distance to MQTT, determine the state based on threshold
    :return: new table state value
    """

    logger = logging.getLogger(__name__)

    if distance > distance_threshold:
        table_state_val = "up"
    else:
        table_state_val = "down"
    logger.debug(f"distance: {distance} cm (table {table_state_val})")

    try:
        # If the publish() fails with one of the exceptions below,
        # reconnect will be attempted. The reconnect() will try number of times,
        # so there is no point retrying here. The message to be published
        # is not important anyway.
        mqtt_client.publish(
            secrets.get(MQTT_TOPIC),
            json.dumps({"distance": distance}),
        )
    except OSError as os_error:
        logger.error(f"failed to publish MQTT message: {os_error}")
        mqtt_client.reconnect()
    except MQTT.MMQTTException as mqtt_exception:
        logger.error(f"failed to publish MQTT message: {mqtt_exception}")
        mqtt_client.reconnect()

    return table_state_val


def display_icon(display, tile_grid, icon_path):
    """
    Display icon in the bottom right corner.
    :return: TileGrid object (either new if the tile_grid argument was None or updated)
    """

    logger = logging.getLogger(__name__)

    try:
        with open(icon_path, "rb"):
            #
            # Technically the OnDiskBitmap should allow file object
            # for file opened in binary mode (for backward compatibility),
            # however this does not seem to be the case.
            #
            icon_bitmap = displayio.OnDiskBitmap(icon_path)
            if not tile_grid:
                tile_grid = displayio.TileGrid(
                    icon_bitmap,
                    pixel_shader=icon_bitmap.pixel_shader,
                    x=display.width - icon_bitmap.width + 10,
                    y=display.height - icon_bitmap.height,
                )
                return tile_grid

            # This assumes that the icon size is the same as the original,
            # otherwise the TileGrid will not allow the update.
            tile_grid.bitmap = icon_bitmap
            tile_grid.pixel_shader = icon_bitmap.pixel_shader
            tile_grid.x = display.width - icon_bitmap.width + 10
            tile_grid.y = display.height - icon_bitmap.height
            return tile_grid
    # pylint: disable=broad-exception-caught
    except Exception as broad_exception:
        logger.error(f"cannot display {icon_path}: {broad_exception}")
        return None


try:
    main()
except ConnectionError as conn_error:
    # When this happens, it usually means that the microcontroller's wifi/networking is botched.
    # The only way to recover is to perform hard reset.
    hard_reset(conn_error)
except MemoryError as memory_error:
    # This is usually the case of delayed exception from the 'import wifi' statement,
    # possibly caused by a bug (resource leak) in CircuitPython that manifests
    # after a sequence of ConnectionError exceptions thrown from withing the wifi module.
    # Should not happen given the above 'except ConnectionError',
    # however adding that here just in case.
    hard_reset(memory_error)
except Exception as generic_exception:  # pylint: disable=broad-except
    # This assumes that such exceptions are quite rare.
    # Otherwise, this would drain the battery quickly by restarting
    # over and over in a quick succession.
    print("Code stopped by unhandled exception:")
    print(
        traceback.format_exception(
            None, generic_exception, generic_exception.__traceback__
        )
    )
    RELOAD_TIME = 10
    print(f"Performing a supervisor reload in {RELOAD_TIME} seconds")
    time.sleep(RELOAD_TIME)
    supervisor.reload()
