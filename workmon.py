#!/usr/bin/env python3
"""
Monitor table position and display on/off state.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from prometheus_client import Gauge, start_http_server

from bulb import Bulb
from display import Display, DisplayException
from logutil import LogLevelAction
from table import Table


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


def sensor_loop(timeout, display, table, bulb):
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

    # Maximum time without a break (in seconds)
    # TODO: make this tunable
    display_contig_max = 3600

    # recommended work duration (in seconds)
    # TODO: make this configurable
    display_daily_max = 3600 * 7

    # the minimal duration of not working that is considered a break time (in seconds)
    # TODO: make this configurable
    break_duration = 5 * 60

    # maximum time the table should be in single position while working (in seconds)
    # TODO: make this configurable
    table_state_max = 20 * 60

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

    #
    # Infinite loop to sample data from the sensors.
    #
    while True:
        table_state = (
            table.is_up()
        )  # Unlike display, not interested in actual position.
        gauges[table_gauge].set(int(table_state))
        display_on = display.is_on()
        gauges[display_gauge].set(int(display_on))

        # How much time in seconds has elapsed since the last loop iteration.
        # TODO: for now run with this estimate
        delta = timeout

        date_now = datetime.now()
        # TODO: assumes normal life, make this tunable
        if date_now.hour > 6:
            logger.debug("New work day is starting")
            display_daily_duration = 0
            table_time = 0
            break_time = 0

        # Check work duration and breaks.
        if display_on:
            break_time = 0

            display_contig_duration = display_contig_duration + delta
            logger.debug(
                f"display contiguously on for {display_contig_duration} seconds"
            )
            if display_contig_duration > display_contig_max:
                logger.info(
                    f"spent {display_contig_duration} seconds "
                    f"(more then {display_contig_max}) with display on"
                )
                # TODO: make this configurable
                bulb.blink("red")

            display_daily_duration = display_daily_duration + delta
            logger.debug(
                f"daily display duration now {display_daily_duration} seconds"
            )  # TODO: format the time hh:ss
            if display_daily_duration > display_daily_max:
                logger.info(
                    f"daily display duration {display_daily_duration} "
                    f"over {display_daily_max} seconds"
                )
                # TODO: make this configurable
                # TODO: this should perhaps occur only couple of times
                bulb.blink("green")
        else:
            logger.debug(f"display off (after {display_contig_duration} seconds)")
            # Display changed state on -> off, start counting the break.
            if last_display_state != display_on:
                break_time = 0
            else:
                break_time = break_time + delta
                logger.debug(f"break time now {break_time} seconds")
                if break_time > break_duration:
                    logger.info(
                        f"Had a break for more than {break_time} seconds, "
                        f"resetting display/table duration time"
                    )
                    display_contig_duration = 0
                    table_time = 0

        # Now check the table.
        if last_table_state == table_state:
            if display_on:
                table_time = table_time + delta
                logger.debug(
                    f"table maintained the position for {table_time} "
                    f"while working for {display_contig_duration}"
                )
                if table_time > table_state_max:
                    logger.info(
                        f"table spent more than {table_state_max} in current position"
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
    parser = argparse.ArgumentParser(
        description="work habits monitoring",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--port",
        default=8111,
        type=int,
        help="port to listen on for HTTP requests",
    )
    parser.add_argument(
        "-s",
        "--sleep",
        default=5,
        type=int,
        help="sleep duration between iterations in seconds",
    )
    parser.add_argument(
        "--height", default=120, type=int, help="table height threshold"
    )
    parser.add_argument(
        "-W",
        "--wattage",
        default=70000,  # Samsung 24" display
        type=int,
        help="wattage threshold for detecting whether display is on/off",
    )
    parser.add_argument(
        "--hostname", required=True,
        help="hostname (IP address) for the TP-link smart plug"
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        action=LogLevelAction,
        help='Set log level (e.g. "ERROR")',
        default=logging.INFO,
    )
    args = parser.parse_args()

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(args.loglevel)
    logger.info("Running")

    logger.info(f"Starting HTTP server on port {args.port}")
    start_http_server(args.port)

    username = os.environ.get("USERNAME")
    if not username:
        logger.error("The USERNAME environment variable is required")
        sys.exit(1)
    password = os.environ.get("PASSWORD")
    if not password:
        logger.error("The PASSWORD environment variable is required")
        sys.exit(1)

    try:
        display = Display(args.hostname, username, password, args.wattage)
        with Table(
            get_tty_usb("Silicon_Labs_CP2102"), height_threshold=args.height
        ) as table:
            with Bulb(get_tty_usb("1a86")) as bulb:
                sensor_loop(args.sleep, display, table, bulb)
    except DisplayException as exc:
        logger.error(f"failed to open the display: {exc}")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
