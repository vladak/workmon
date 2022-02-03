#!/usr/bin/env python3
"""
Monitor table position and display on/off state.
"""

import logging
import time
from datetime import datetime

from prometheus_client import Gauge

from .utils import time_delta_fmt


# pylint: disable=too-few-public-methods
class Maximums:
    """
    for passing tunables around
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self, display_contig_max, display_daily_max, break_duration, table_state_max, timeout
    ):
        """
        :param display_contig_max
        :param display_daily_max
        :param break_duration
        :param table_state_max
        :param timeout
        """
        self.display_contig_max = display_contig_max
        self.display_daily_max = display_daily_max
        self.break_duration = break_duration
        self.table_state_max = table_state_max
        self.timeout = timeout


class Workmon:
    """
    main work monitoring class
    """

    table_gauge = "table"
    display_gauge = "display"

    def __init__(self, display, table, bulb, maximums):
        """
        :param display
        :param table
        :param bulb
        :param maximums
        """
        self.display = display
        self.table = table
        self.bulb = bulb
        self.maximums = maximums

        self.gauges = {
            self.table_gauge: Gauge("table_position", "Table position"),
            self.display_gauge: Gauge("display_status", "Display status"),
        }

    def get_sensor_values(self):
        """
        :return tuple of table position and display state
        """

        table_state = (
            self.table.is_up()
        )  # Unlike display, not interested in actual position.
        self.gauges[self.table_gauge].set(int(table_state))

        display_on = self.display.is_on()
        if display_on is None:
            self.gauges[self.display_gauge].set("NaN")
        else:
            self.gauges[self.display_gauge].set(int(display_on))

        return table_state, display_on

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def sensor_loop(self):
        """
        In endless loop acquire data from the sensors, perform signalling.
        """

        logger = logging.getLogger(__name__)

        maximums = self.maximums
        display_contig_max = maximums.display_contig_max
        display_daily_max = maximums.display_daily_max
        break_duration = maximums.break_duration
        table_state_max = maximums.table_state_max

        last_table_state = None
        last_display_state = None

        # the last duration for which the display was on (in seconds)
        display_contig_duration = 0
        # total in the display was on during the day (in seconds)
        display_daily_duration = 0
        # duration of the last break (in seconds)
        break_time = 0
        # the duration for which the table has been in the last position (in seconds)
        table_time = 0
        blinked_end_of_day = False
        blinked_table = False
        blinked_display = False

        last_time = time.monotonic()
        #
        # Infinite loop to sample data from the sensors.
        #
        while True:
            table_state, display_on = self.get_sensor_values()
            if display_on is None:
                continue

            # How much time in seconds has elapsed since the last loop iteration.
            delta = int(time.monotonic() - last_time)
            last_time = time.monotonic()
            logger.debug(f"time delta = {time_delta_fmt(delta)}")

            date_now = datetime.now()
            if date_now.hour == 6:
                logger.debug("New work day is starting")
                display_daily_duration = 0
                table_time = 0
                break_time = 0
                blinked_end_of_day = False
                blinked_table = False
                blinked_display = False

            # Check work duration and breaks.
            if display_on:
                break_time = 0

                display_contig_duration = display_contig_duration + delta
                logger.debug(
                    f"display contiguously on for {time_delta_fmt(display_contig_duration)}"
                )
                if display_contig_duration > display_contig_max:
                    logger.info(
                        f"spent {time_delta_fmt(display_contig_duration)} "
                        f"with display on (more than {time_delta_fmt(display_contig_max)})"
                    )
                    if not blinked_display:
                        self.bulb.blink("red")
                        blinked_display = True

                display_daily_duration = display_daily_duration + delta
                logger.debug(
                    f"daily display duration now {time_delta_fmt(display_daily_duration)}"
                )
                if display_daily_duration > display_daily_max:
                    logger.info(
                        f"daily display duration {time_delta_fmt(display_daily_duration)} "
                        f"over {time_delta_fmt(display_daily_max)}"
                    )
                    if not blinked_end_of_day:
                        self.bulb.blink("green")
                        blinked_end_of_day = True
            else:
                logger.debug(
                    f"display off (after being on for "
                    f"{time_delta_fmt(display_contig_duration)})"
                )
                # Display changed state on -> off, start counting the break.
                if last_display_state != display_on:
                    break_time = 0
                else:
                    break_time = break_time + delta
                    logger.debug(f"break time now {time_delta_fmt(break_time)}")
                    if break_time > break_duration:
                        logger.info(
                            f"Had a break for {time_delta_fmt(break_time)}, "
                            f"(more than {time_delta_fmt(break_duration)}),"
                            f" resetting display/table duration time"
                        )
                        display_contig_duration = 0
                        table_time = 0
                        blinked_display = False

            # Now check the table.
            if last_table_state == table_state:
                if display_on:
                    table_time = table_time + delta
                    logger.debug(
                        f"table maintained the position for {time_delta_fmt(table_time)} "
                        f"while working for {time_delta_fmt(display_contig_duration)}"
                    )
                    if table_time > table_state_max:
                        logger.info(
                            f"table spent more than {time_delta_fmt(table_state_max)} "
                            f"in current position, blinking is in order"
                        )
                        if not blinked_table:
                            self.bulb.blink("yellow")
                            blinked_table = True
            else:
                logger.debug(
                    f"table changed the position from {last_table_state} to {table_state}"
                )
                table_time = 0
                blinked_table = False

            last_table_state = table_state
            last_display_state = display_on

            time.sleep(self.maximums.timeout)
