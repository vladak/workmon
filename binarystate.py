"""
generic binary state tracking class
"""
import time

import adafruit_logging as logging


class BinaryState:
    """
    provides state tracking based on updating value periodically
    """

    def __init__(
        self,
    ):
        """
        set the initial state
        """
        self.prev_state = None
        self.state_duration = 0
        self.stamp = time.monotonic_ns()  # use _ns() to avoid losing precision

    def update(self, cur_state):
        """
        :param cur_state: current state
        :return: duration of the state in seconds
        """
        logger = logging.getLogger(__name__)

        # Record the duration of table position.
        if self.prev_state:
            if self.prev_state == cur_state:
                self.state_duration += (
                    time.monotonic_ns() - self.stamp
                ) // 1_000_000_000
                logger.debug(
                    f"state '{cur_state}' preserved (for {self.state_duration} sec)"
                )
            else:
                logger.debug(f"state changed {self.prev_state} -> {cur_state}")
                self.state_duration = 0

        self.prev_state = cur_state
        self.stamp = time.monotonic_ns()

        return self.state_duration

    def reset(self):
        """
        reset the state
        """
        # TODO: reset self.stamp as well ?
        self.prev_state = None
        self.state_duration = 0
