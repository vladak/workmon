"""
tests for time utility functions
"""

import os
import time
from unittest.mock import Mock

import pytest

from timeutil import dst_offset_eu, get_time

testdata = [
    ((2024, 2, 10, 20, 12, 33, 5, 41, -1), 0),
    ((2024, 3, 31, 8, 1, 0, 6, 91, -1), 1),  # last Sunday in March
    ((2024, 5, 12, 10, 32, 0, 6, 133, -1), 1),
    ((2024, 10, 27, 1, 0, 0, 6, 301, -1), 1),  # last Sunday in October
    ((2024, 12, 24, 9, 0, 0, 6, 359, -1), 0),
]


@pytest.mark.parametrize(
    "tup,is_dst_expected", testdata, ids=["before", "at", "middle", "end", "after"]
)
def test_dst_offset_eu(tup, is_dst_expected):
    """
    Test dst_offset_eu() by using a couple of known inputs.
    """
    os.environ["TZ"] = "Europe/Prague"
    time.tzset()

    t_epoch = time.mktime(tup)
    gm_t = time.gmtime(t_epoch + 3600)  # assumes the above TZ setting
    assert gm_t.tm_gmtoff == 0
    local_t = time.localtime(t_epoch)
    assert local_t.tm_isdst == is_dst_expected
    assert (local_t.tm_isdst == 0) == (dst_offset_eu(gm_t) == 0)


def test_get_time_vs_dst_eu():
    """
    Verify that get_time() correctly handles DST (in the EU at least).
    """
    ntp = Mock()
    t_epoch = time.mktime((2024, 5, 12, 10, 32, 0, 6, 133, -1))
    gm_t = time.gmtime(t_epoch)
    ntp.datetime = gm_t
    ntp_hour, ntp_minute = get_time(ntp)
    assert ntp_hour == gm_t.tm_hour + 1
    assert ntp_minute == gm_t.tm_min
