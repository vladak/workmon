"""
MQTT publisher
"""

import logging
import threading

import paho.mqtt.client as mqtt


class MqttFatal(Exception):
    """
    fatal error when setting up MQTT
    """


class Mqtt:
    """
    MQTT wrapper
    """
    def __init__(self, hostname, port, topic):
        self.topic = topic

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        try:
            keep_alive = 60
            self.client.connect(hostname, port, keep_alive)
        except OSError as exc:
            raise MqttFatal from exc

        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    def run(self):
        """
        thread function
        """
        self.client.loop_forever()

    # pylint: disable=unused-argument
    @staticmethod
    def on_connect(client, userdata, flags, ret_code):
        """
        called on MQTT connect
        :param client:
        :param userdata:
        :param flags:
        :param ret_code:
        :return:
        """
        logger = logging.getLogger(__name__)

        if ret_code == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Connect to MQTT broker failed with code {ret_code}")
            raise MqttFatal("cannot connect to MQTT broker")

    def publish(self, msg):
        """
        publish MQTT message
        """
        self.client.publish(self.topic, payload=msg, qos=0, retain=False)
