from datetime import datetime
import collections

from pytest import mark
from netCDF4 import num2date

from nchelpers.date_utils import resolution_standard_name, to_datetime


@mark.parametrize('arg, result', [
    (60, '1-minute'),
    (2678400, 'monthly'),
    (999, 'other')
])
def test_resolution_standard_name(arg, result):
    assert resolution_standard_name(arg) == result


@mark.parametrize('input, expected', [
    (datetime(2000, 1, 2, 3, 4, 5, 6), datetime(2000, 1, 2, 3, 4, 5, 6)),
    (num2date(0, 'seconds since 2000-01-02 03:04:05'), datetime(2000, 1, 2, 3, 4, 5)),
    ((), ()),
    ((datetime(2000, 1, 2, 3, 4, s) for s in range(5)), (datetime(2000, 1, 2, 3, 4, s) for s in range(5))),
    ((num2date(s, 'seconds since 2000-01-02 03:04:00') for s in range(5)), (datetime(2000, 1, 2, 3, 4, s) for s in range(5))),
])
def test_to_datetime(input, expected):
    if isinstance(input, collections.Iterable):
        assert list(to_datetime(input)) == list(expected)
    else:
        assert to_datetime(input) == expected