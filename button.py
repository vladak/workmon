"""
button class to provide button pressed information
"""

import digitalio


# pylint: disable=too-few-public-methods
class Button:
    """
    wraps button handling
    """

    def __init__(self, pin, pull):
        """
        :param pin: board pin
        :param pull: pull direction (UP or DOWN)
        """
        button_io = digitalio.DigitalInOut(pin)
        button_io.switch_to_input(pull=pull)

        self._button = button_io
        self._pull = pull

    @property
    def pressed(self):
        """
        return whether the button is pressed
        """
        if self._pull == digitalio.Pull.UP:
            return not self._button.value

        return self._button.value
