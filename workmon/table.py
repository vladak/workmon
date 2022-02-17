"""
wrapper class for US-100 Adafruit sensor to detect table position
"""

import logging
import os

import adafruit_us100
import serial


class TableException(Exception):
    """
    wrapper for table exceptions
    """


class Table:
    """
    provides 1 bit of information w.r.t. given threshold: whether the table is up or down
    """

    def __init__(
        self,
        serial_device_path,
        baud_rate=9600,
        height_up_threshold=90,
        height_down_threshold=60,
    ):
        """
        :param serial_device_path
        :param baud_rate
        :param height_up_threshold if the distance is above this threshold (in centimeters),
            the table is considered up
        :param height_down_threshold if the distance is below this threshold (in centimeters),
            the table is considered down
        """
        if not os.path.exists(serial_device_path):
            raise OSError(f"not a valid path: {serial_device_path}")

        self.serial_device_path = serial_device_path
        self.baud_rate = baud_rate
        self.height_up_threshold = height_up_threshold
        self.height_down_threshold = height_down_threshold

        self.uart = None
        self.us100 = None

        self.logger = logging.getLogger(__name__)

        self.logger.debug(f"using table threshold {self.height_threshold}")

    def __enter__(self):
        self.uart = serial.Serial(
            self.serial_device_path, baudrate=self.baud_rate, timeout=1
        )
        self.us100 = adafruit_us100.US100(self.uart)

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def get_distance(self):
        """
        get current distance
        """
        distance = self.us100.distance
        if distance is None:
            raise TableException("cannot determine table state")

        return distance

    def log_position(self, distance, is_up):
        """
        log current distance and position
        """
        position_str = "up" if is_up else "down"
        self.logger.debug(f"table distance = {distance} -> position {position_str}")

    def is_up(self):
        """
        is the table up ?
        """
        distance = self.get_distance()
        is_up = distance > self.height_up_threshold
        self.log_position(distance, is_up)
        return is_up

    def is_down(self):
        """
        is the table down ?
        """
        distance = self.get_distance()
        is_down = distance < self.height_down_threshold
        self.log_position(distance, not is_down)
        return is_down

    def close(self):
        """
        Close the serial line.
        """
        if self.uart:
            self.uart.close()
