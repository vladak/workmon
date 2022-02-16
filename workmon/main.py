"""
main program
"""

import logging
import os
import sys

from prometheus_client import start_http_server

from .bulb import Bulb
from .display import Display, DisplayException
from .mqtt import Mqtt, MqttFatal
from .parserutil import parse_args
from .table import Table
from .utils import get_tty_usb
from .workmon import Maximums, Workmon


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
        args.sleep,
        args.start_of_day,
    )

    mqtt = None
    if args.mqtt_hostname and args.mqtt_port > 0 and args.topic:
        try:
            mqtt = Mqtt(args.mqtt_hostname, args.mqtt_port, args.topic)
        except MqttFatal as mqtt_fatal:
            logger.error(f"cannot get Mqtt instance: {mqtt_fatal}")

    try:
        display = Display(args.hostname, username, password, args.wattage)
        with Table(
            get_tty_usb("Silicon_Labs_CP2102"), height_threshold=args.height
        ) as table:
            with Bulb(get_tty_usb("1a86")) as bulb:
                workmon = Workmon(display, table, bulb, maximums, mqtt)
                workmon.sensor_loop()
    except DisplayException as exc:
        logger.error(f"failed to open the display: {exc}")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"OS error: {exc}")
        sys.exit(1)


def run_main():
    """
    this is the main entry point
    """
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run_main()
