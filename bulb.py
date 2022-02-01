"""
Wrapper class for controlling Adafruit USB light bulb.
"""

import os

import serial


class Bulb(object):
    """
    Supports on/off/blink for red, green, yellow.
    """

    RED_ON = 0x11
    RED_OFF = 0x21
    RED_BLINK = 0x41

    YELLOW_ON = 0x12
    YELLOW_OFF = 0x22
    YELLOW_BLINK = 0x42

    GREEN_ON = 0x14
    GREEN_OFF = 0x24
    GREEN_BLINK = 0x44

    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"

    on_cmds = {RED: RED_ON, GREEN: GREEN_ON, YELLOW: YELLOW_ON}
    off_cmds = {RED: RED_OFF, GREEN: GREEN_OFF, YELLOW: YELLOW_OFF}
    blink_cmds = {RED: RED_BLINK, GREEN: GREEN_BLINK, YELLOW: YELLOW_BLINK}

    def __init__(self, serial_device_path, baud_rate=9600):
        if not os.path.exists(serial_device_path):
            raise OSError(f"not a valid path: {serial_device_path}")

        self.serial_device_path = serial_device_path
        self.baud_rate = baud_rate

        self.bulb_serial = None

    def cleanup(self):
        """
        Turn all the diodes off.
        """
        self._send_command(self.RED_OFF)
        self._send_command(self.YELLOW_OFF)
        self._send_command(self.GREEN_OFF)

    def __enter__(self):
        self.bulb_serial = serial.Serial(self.serial_device_path, self.baud_rate)

        self.cleanup()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def _send_command(self, cmd):
        if self.bulb_serial:
            self.bulb_serial.write(bytes([cmd]))

    def close(self):
        """
        Turn all the diodes off and close the serial line.
        """
        self.cleanup()
        self.bulb_serial.close()

    # TODO: add variant with timeout
    def blink(self, color):
        """
        blink with given color
        """
        self._send_command(self.blink_cmds.get(color.lower()))

    # TODO: add variant with timeout
    # pylint: disable=invalid-name
    def on(self, color):
        """
        turn on given color
        """
        self._send_command(self.on_cmds.get(color.lower()))

    def off(self, color):
        """
        turn off given color
        """
        self._send_command(self.off_cmds.get(color.lower()))
