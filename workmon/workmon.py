#!/usr/bin/env python3
"""
Monitor table position and display on/off state.
"""

import logging
import os
import sys
import time
from datetime import datetime

from prometheus_client import Gauge, start_http_server

from .bulb import Bulb
from .display import Display, DisplayException
from .parserutil import parse_args
from .table import Table


def time_delta_fmt(seconds):
    """
    :return number of seconds formatted for logging
    """
    if seconds < 60:
        return f"{seconds}s"

    if seconds < 3600:
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes}:{seconds:02}"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"


def get_tty_usb(id_to_match):
    """
    Find device tree entry for given ID/substring. Normally this should return /dev/ttyUSB*
    """

    logger = logging.getLogger(__name__)

    by_id_dir_path = "/dev/serial/by-id/"
    if not os.path.isdir(by_id_dir_path):
        raise OSError(f"need {by_id_dir_path} directory to work")

    for item in os.listdir(by_id_dir_path):
        if id_to_match in item:
            logger.debug(f"found a match for {id_to_match}: {item}")
            link_destination = os.readlink(os.path.join(by_id_dir_path, item))
            return os.path.realpath(
                os.path.join("/dev/serial/by-id/", link_destination)
            )

    return None


# pylint: disable=too-few-public-methods
class Maximums:
    """
    for passing tunables around
    """

    def __init__(
        self, display_contig_max, display_daily_max, break_duration, table_state_max
    ):
        """
        :param display_contig_max
        :param display_daily_max
        :param break_duration
        :param table_state_max
        """
        self.display_contig_max = display_contig_max
        self.display_daily_max = display_daily_max
        self.break_duration = break_duration
        self.table_state_max = table_state_max


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def sensor_loop(timeout, display, table, bulb, maximums):
    """
    Acquire data from the sensors.
    """

    logger = logging.getLogger(__name__)

    table_gauge = "table"
    display_gauge = "display"
    gauges = {
        table_gauge: Gauge("table_position", "Table position"),
        display_gauge: Gauge("display_status", "Display status"),
    }

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

    #
    # Infinite loop to sample data from the sensors.
    #
    while True:
        table_state = (
            table.is_up()
        )  # Unlike display, not interested in actual position.
        gauges[table_gauge].set(int(table_state))
        display_on = display.is_on()
        if display_on is None:
            continue
        gauges[display_gauge].set(int(display_on))

        # How much time in seconds has elapsed since the last loop iteration.
        # TODO: for now run with this estimate
        delta = timeout

        date_now = datetime.now()
        # TODO: assumes normal life, make this tunable
        if (
            date_now.hour == 6
        ):  # TODO: this assumes the sleep timeout is less than one hour
            logger.debug("New work day is starting")
            display_daily_duration = 0
            table_time = 0
            break_time = 0
            blinked_end_of_day = False

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
                    f"(more then {time_delta_fmt(display_contig_max)}) with display on"
                )
                bulb.blink("red")

            display_daily_duration = display_daily_duration + delta
            logger.debug(
                f"daily display duration now {time_delta_fmt(display_daily_duration)}"
            )
            if display_daily_duration > display_daily_max and not blinked_end_of_day:
                logger.info(
                    f"daily display duration {time_delta_fmt(display_daily_duration)} "
                    f"over {time_delta_fmt(display_daily_max)}"
                )
                bulb.blink("green")
                blinked_end_of_day = True
        else:
            logger.debug(
                f"display off (after {time_delta_fmt(display_contig_duration)})"
            )
            # Display changed state on -> off, start counting the break.
            if last_display_state != display_on:
                break_time = 0
            else:
                break_time = break_time + delta
                logger.debug(f"break time now {time_delta_fmt(break_time)}")
                if break_time > break_duration:
                    logger.info(
                        f"Had a break for more than {time_delta_fmt(break_time)}, "
                        f"resetting display/table duration time"
                    )
                    display_contig_duration = 0
                    table_time = 0

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
                        f"in current position"
                    )
                    bulb.blink("yellow")
        else:
            logger.debug(
                f"table changed the position from {last_table_state} to {table_state}"
            )
            table_time = 0

        last_table_state = table_state
        last_display_state = display_on

        time.sleep(timeout)


def main():
    """
    Main program
    """
    args = parse_args()

    logging.basicConfig()
    logger = logging.getLogger(__package__)
    logger.setLevel(args.loglevel)
    logger.info("Running")

    username = os.environ.get("USERNAME")
    if not username:
        logger.error("The USERNAME environment variable is required")
        sys.exit(1)
    password = os.environ.get("PASSWORD")
    if not password:
        logger.error("The PASSWORD environment variable is required")
        sys.exit(1)

    logger.info(f"Starting HTTP server on port {args.port}")
    start_http_server(args.port)

    maximums = Maximums(
        args.display_contig_max,
        args.display_daily_max,
        args.break_duration,
        args.table_state_max,
    )

    try:
        display = Display(args.hostname, username, password, args.wattage)
        with Table(
            get_tty_usb("Silicon_Labs_CP2102"), height_threshold=args.height
        ) as table:
            with Bulb(get_tty_usb("1a86")) as bulb:
                sensor_loop(args.sleep, display, table, bulb, maximums)
    except DisplayException as exc:
        logger.error(f"failed to open the display: {exc}")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"OS error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
