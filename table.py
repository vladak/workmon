"""
wrapper class for US-100 Adafruit sensor to detect table position
"""

import serial

import adafruit_us100


class Table:
    """
    provides 1 bit of information w.r.t. given threshold: whether the table is up or down
    """

    def __init__(self, serial_device_path, baud_rate=9600, height_threshold=100):
        self.serial_device_path = serial_device_path
        self.baud_rate = baud_rate
        self.height_threshold = height_threshold

    def __enter__(self):
        self.uart = serial.Serial(self.serial_device_path, baudrate=self.baud_rate, timeout=1)
        self.us100 = adafruit_us100.US100(self.uart)

    def __exit__(self):
        self.close()

    def is_up(self):
        return self.us100.distance > self.height_threshold

    def is_down(self):
        return not self.is_up()

    def close(self):
        self.uart.close()