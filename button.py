"""
button class to provide button pressed information
"""

import digitalio
from adafruit_debouncer import Debouncer


# pylint: disable=too-few-public-methods
class Button:
    """
    wraps button handling
    """

    def __init__(self, pin, pull):
        """
        :param pin: board pin
        :param pull: pull direction (digitalio.Pull.UP or digitalio.Pull.DOWN)
        """
        button_io = digitalio.DigitalInOut(pin)
        button_io.switch_to_input(pull=pull)

        self._button = Debouncer(button_io)
        self._pull = pull

    def update(self):
        """
        Update the button state. Should be called at the start of the main loop.
        Must be called frequently.
        """
        self._button.update()

    @property
    def pressed(self):
        """
        return whether the button is pressed
        """
        if self._pull == digitalio.Pull.UP:
            return self._button.fell

        return self._button.rose
