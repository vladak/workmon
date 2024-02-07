"""
module that contains the Blinker class
"""

import adafruit_logging as logging

from binarystate import BinaryState


# pylint: disable=too-few-public-methods
class Blinker:
    """
    Encapsulates a method to blink a neopixel from within a tight loop.

    The class is not ready to be used in multiple instances for the same neopixel.
    Assumes that update() will be called more frequently than the value of the duration parameter.
    """

    def __init__(self, pixel, brightness=0.5, duration=0.5, color=(0, 0, 255)):
        """
        initialize the Blinker object
        """
        self.pixel = pixel
        self.brightness = brightness
        self.duration = duration
        self.color = color

        self._binary_state = BinaryState()
        self._is_on = False

    def set_blinking(self, is_blinking: bool):
        """
        Let the Neo pixel be on in color and the duration specified in the init function.
        """
        logger = logging.getLogger(__name__)

        logger.debug(f"blinking -> {is_blinking}")

        if is_blinking:
            duration = self._binary_state.update(self._is_on)
            logger.debug(f"state {self._is_on} duration {duration}")
            if duration > self.duration:
                logger.debug(
                    f"duration {duration} exceeded {self.duration}, switching state"
                )
                self._is_on = not self._is_on
                if self._is_on:
                    self.pixel.brightness = self.brightness
                    self.pixel.fill(self.color)
                else:
                    self.pixel.brightness = 0
        else:
            self.pixel.brightness = 0
            self._is_on = False
            self._binary_state.reset()
