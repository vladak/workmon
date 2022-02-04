"""
argument parsing
"""

import argparse
import logging

from .logutil import LogLevelAction


def parse_args():
    """
    parse command line arguments
    :return args
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
        default=70,  # Samsung 24" display takes ~74W when on.
        type=int,
        help="wattage threshold for detecting whether display is on/off",
    )
    parser.add_argument(
        "--hostname",
        required=True,
        help="hostname (IP address) for the TP-link smart plug",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        action=LogLevelAction,
        help='Set log level (e.g. "ERROR")',
        default=logging.INFO,
    )
    parser.add_argument(
        "--display_contig_max",
        type=int,
        default=3600,
        help="Maximum time without a break (in seconds)",
    )
    parser.add_argument(
        "--display_daily_max",
        type=int,
        default=3600 * 7,
        help="recommended work duration (in seconds)",
    )
    parser.add_argument(
        "--break_duration",
        type=int,
        default=5 * 60,
        help="the minimal duration of not working that is considered a break time (in seconds)",
    )
    parser.add_argument(
        "--table_state_max",
        type=int,
        default=20 * 60,
        help="maximum time the table should be in single position while working (in seconds)",
    )
    parser.add_argument(
        "-t",
        "--topic",
        help="MQTT topic to send blink events to",
    )
    parser.add_argument(
        "--mqtt_hostname",
        help="hostname of the MQTT broker",
    )
    parser.add_argument(
        "--mqtt_port",
        type=int,
        help="port of the MQTT broker",
    )

    return parser.parse_args()
