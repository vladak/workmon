"""
DST utilities
"""

import adafruit_logging as logging


def dst_offset_eu(time_struct) -> int:
    """
    Checks if the supplied time struct matches DST in EU.
    Assumes the input time is non-UTC time.
    Using formula from https://www.webexhibits.org/daylightsaving/i.html
    Since 1996, valid through 2099.
    Code adapted from
    https://forum.arduino.cc/t/daylight-saving-time-adjust-with-ethernet-ntp/192602
    :return: time offset in hours
    """
    hour = time_struct.tm_hour
    day = time_struct.tm_mday
    month = time_struct.tm_mon
    year = time_struct.tm_year

    begin_dst_month = 3  # March
    begin_dst_day = 31 - (5 * year // 4 + 4) % 7
    end_dst_month = 10  # October
    end_dst_day = 31 - (5 * year // 4 + 1) % 7

    # pylint: disable=too-many-boolean-expressions,chained-comparison
    if (
        ((month > begin_dst_month) and (month < end_dst_month))
        or ((month == begin_dst_month) and (day > begin_dst_day))
        or ((month == begin_dst_month) and (day == begin_dst_day) and (hour >= 2))
        or ((month == end_dst_month) and (day < end_dst_day))
        or ((month == end_dst_month) and (day == end_dst_day) and (hour < 1))
    ):
        return 1

    return 0


def get_time(ntp):
    """
    return current time from NTP as tuple hour, minute
    """
    logger = logging.getLogger(__name__)

    current_time = None  # to silence a warning in IDEA
    attempts = 3
    for i in range(attempts):
        try:
            current_time = ntp.datetime
            break
        except OSError as os_error:
            logger.warning(f"got OSError when getting NTP time: {os_error}")
            if i == attempts - 1:
                raise os_error
            continue

    current_hour = current_time.tm_hour + dst_offset_eu(current_time)
    current_minute = current_time.tm_min
    logger.debug(f"time: {current_hour:2}:{current_minute:02}")

    return current_hour, current_minute
