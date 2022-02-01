"""
wrapper class for TP-link smart plug wattage
"""
import logging

from PyP100 import PyP110


class DisplayException(Exception):
    """
    wrapper for Display specific exceptions
    """


class Display:
    """
    provides 1 bit of information: whether the display is on or off

    Assumes Wattage sensor measurements w.r.t. given threshold.
    """

    def __init__(self, hostname, username, password, threshold):
        """
        :param hostname hostname or IP address
        :param username username
        :param password password
        :param threshold value in Watts to set apart the display to be on/off
        """
        self.threshold = threshold

        self.p110 = PyP110.P110(hostname, username, password)
        self.p110.handshake()
        self.p110.login()

        self.logger = logging.getLogger(__name__)

    def is_on(self):
        """
        is the display on ?
        """

        energy_usage_dict = self.p110.getEnergyUsage()
        self.logger.debug(f"Got energy usage dictionary: {energy_usage_dict}")
        value = energy_usage_dict.get("result").get("current_power")

        return int(value) / 1000 > self.threshold

    def is_off(self):
        """
        is the display off ?
        """
        return not self.is_on()
