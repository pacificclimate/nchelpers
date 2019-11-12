from datetime import datetime
import collections

from pytest import mark
from netCDF4 import num2date

from nchelpers.date_utils import \
    resolution_standard_name, \
    jday_360_to_remapped_month_day, \
    to_datetime, \
    truncate_to_resolution


@mark.parametrize('arg, result', [
    (60, '1-minute'),
    (2678400, 'monthly'),
    (999, 'other')
])
def test_resolution_standard_name(arg, result):
    assert resolution_standard_name(arg) == result


jday_360_to_month_day = [
    (1, 1, 1),  # 360: Jan 1
    (30, 1, 30),  # 360: Jan 30
    (31, 1, 31),  # 360: Feb 1
    (58, 2, 27),  # 360: Feb 28
    (59, 2, 28),  # 360: Feb 29
    (60, 3, 1),  # 360: Feb 30
    (61, 3, 2),  # 360: Mar 1
    (90, 3, 31),  # 360: Mar 30
    (91, 4, 1),  # 360: Apr 1
    (120, 4, 30),  # 360: Apr 30
    (121, 5, 1),  # etc.: first and last days of other 360 day months
    (150, 5, 30),
    (151, 6, 1),
    (180, 6, 30),
    (181, 7, 1),
    (210, 7, 30),
    (211, 8, 1),
    (240, 8, 30),
    (360, 12, 30),
]


@mark.parametrize('jday_360, month, day', jday_360_to_month_day)
def test_jday_360_to_remapped_date(jday_360, month, day):
    assert jday_360_to_remapped_month_day(jday_360) == (month, day)


@mark.parametrize('arg, expected', [
    # ((), ()),
    # (datetime(2000, 1, 2, 3, 4, 5, 6),
    #  datetime(2000, 1, 2, 3, 4, 5, 6)),
    # (num2date(0, 'seconds since 2000-01-02 03:04:05'),
    #  datetime(2000, 1, 2, 3, 4, 5)),
    # ((datetime(2000, 1, 2, 3, 4, s) for s in range(5)),
    #  (datetime(2000, 1, 2, 3, 4, s) for s in range(5))),
    # ((num2date(s, 'seconds since 2000-01-02 03:04:00') for s in range(5)),
    #  (datetime(2000, 1, 2, 3, 4, s) for s in range(5))),
    (num2date(1, 'days since 1999-12-30', '360_day'), datetime(2000, 1, 1)),
    (num2date(30, 'days since 1999-12-30', '360_day'), datetime(2000, 1, 30)),
    (num2date(31, 'days since 1999-12-30', '360_day'), datetime(2000, 1, 31)),
    (num2date(32, 'days since 1999-12-30', '360_day'), datetime(2000, 2, 1)),
    (num2date(59, 'days since 1999-12-30', '360_day'), datetime(2000, 2, 28)),
    (num2date(60, 'days since 1999-12-30', '360_day'), datetime(2000, 3, 1)),
])
def test_to_datetime(arg, expected):
    if isinstance(arg, collections.Iterable):
        assert list(to_datetime(arg)) == list(expected)
    else:
        assert to_datetime(arg) == expected


@mark.parametrize('jday_360, month, day' , jday_360_to_month_day)
def test_to_datetime_360(jday_360, month, day):
    assert \
        to_datetime(num2date(jday_360, 'days since 1999-12-30', '360_day')) == \
        datetime(2000, month, day)

@mark.parametrize('date, resolution, expected', [
    (datetime(2000, 2, 1, 13, 35), "yearly", datetime(2000, 1, 1)),
    (datetime(2000, 2, 1, 13, 35), "monthly", datetime(2000, 2, 1)),
    (datetime(2000, 2, 1, 13, 35), "seasonal", datetime(1999, 12, 1)),
    (datetime(2000, 2, 1, 13, 35), "30-minute", datetime(2000, 2, 1, 13, 30)),
    (datetime(2000, 2, 1, 13, 35), "2-minute", datetime(2000, 2, 1, 13, 34)),
    (datetime(2000, 2, 1, 13, 35), "6-hourly", datetime(2000, 2, 1, 12)),
    (datetime(2000, 2, 1, 13, 35), "1-hourly", datetime(2000, 2, 1, 13)),
    (datetime(2012, 5, 1), "seasonal", datetime(2012, 3, 1))
    ])
def test_truncate_to_resolution(date, resolution, expected):
    assert(truncate_to_resolution(date, resolution)) == expected