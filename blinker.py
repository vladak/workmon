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

    Not thread safe.
    """

    def __init__(self, pixel, brightness=0.5, duration=0.5):
        """
        initialize the Blinker object
        """
        self.pixel = pixel
        self.brightness = brightness
        self.duration = duration

        self._binary_state = BinaryState()
        self._is_on = False

        self.is_blinking = False
        self.color = None

    def set_blinking(self, is_blinking: bool, color=None):
        """
        Let the Neo pixel be on in color and the duration specified in the init function.
        """
        logger = logging.getLogger(__name__)

        logger.debug(f"blinking -> {is_blinking}")
        self.is_blinking = is_blinking

        if self.is_blinking:
            self.color = color
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
            # If the color argument is specified, it has to match the current color.
            if color is None or self.color == color:
                self.pixel.brightness = 0
                self._is_on = False
                self.color = None
                self._binary_state.reset()
