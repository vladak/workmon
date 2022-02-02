"""
various utility functions
"""
import logging
import os


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

