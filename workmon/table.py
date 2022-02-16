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

    def __init__(self, serial_device_path, baud_rate=9600, height_threshold=90):
        if not os.path.exists(serial_device_path):
            raise OSError(f"not a valid path: {serial_device_path}")

        self.serial_device_path = serial_device_path
        self.baud_rate = baud_rate
        self.height_threshold = height_threshold

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

    def is_up(self):
        """
        is the table up ?
        """
        distance = self.us100.distance
        if distance is None:
            raise TableException("cannot determine table state")

        position = distance > self.height_threshold
        position_str = "up" if position else "down"
        self.logger.debug(f"table distance = {distance} -> position {position_str}")
        return position

    def is_down(self):
        """
        is the table down ?
        """
        return not self.is_up()

    def close(self):
        """
        Close the serial line.
        """
        if self.uart:
            self.uart.close()
