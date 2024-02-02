"""
MQTT utility functions
"""
import ssl

import adafruit_logging as logging
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Avoid infinite recursion by using non-default logger in the MQTT callbacks.
MQTT_LOGGER_NAME = "mqtt"


# pylint: disable=unused-argument, redefined-outer-name, invalid-name
def connect(mqtt_client, userdata, flags, rc):
    """
    This function will be called when the mqtt_client is connected
    successfully to the broker.
    """
    logger = logging.getLogger(MQTT_LOGGER_NAME)

    logger.info("Connected to MQTT Broker!")
    logger.debug(f"Flags: {flags}\n RC: {rc}")


# pylint: disable=unused-argument, invalid-name
def disconnect(mqtt_client, userdata, rc):
    """
    This method is called when the mqtt_client disconnects from the broker.
    """
    logger = logging.getLogger(MQTT_LOGGER_NAME)

    logger.info("Disconnected from MQTT Broker!")


def publish(mqtt_client, userdata, topic, pid):
    """
    This method is called when the mqtt_client publishes data to a feed.
    """
    logger = logging.getLogger(MQTT_LOGGER_NAME)

    logger.info(f"Published to {topic} with PID {pid}")


def mqtt_client_setup(pool, broker, port, log_level, user_data=None, socket_timeout=1):
    """
    Set up a MiniMQTT Client
    """

    logger = logging.getLogger(MQTT_LOGGER_NAME)
    logger.setLevel(log_level)

    mqtt_client = MQTT.MQTT(
        broker=broker,
        port=port,
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
        user_data=user_data,
        socket_timeout=socket_timeout,
    )
    # Connect callback handlers to mqtt_client
    mqtt_client.on_connect = connect
    mqtt_client.on_disconnect = disconnect
    mqtt_client.on_publish = publish

    return mqtt_client
