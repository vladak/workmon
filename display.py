"""
wrapper class for TP-link smart plug wattage
"""


class DisplayException(Exception):
    """
    wrapper for Display specific exceptions
    """


class Display:
    """
    provides 1 bit of information: whether the display is on or off

    Assumes Wattage sensor measurements w.r.t. given threshold.
    """

    def __init__(self, url, username, password, threshold):
        self.url = url
        self.username = username
        self.password = password
        self.threshold = threshold

    def __enter__(self):
        pass

    def __exit__(self):
        self.close()

    def is_on(self):
        """
        is the display on ?
        """
        value = 1234

        return int(value) > self.threshold

    def is_off(self):
        """
        is the display off ?
        """
        return not self.is_on()

    def close(self):
        pass
