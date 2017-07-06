from datetime import datetime, date
import collections
import re


def time_scale(time_var):
    match = re.match('(days|hours|minutes|seconds) since.*', time_var.units)
    if match:
        return match.groups()[0]
    else:
        raise ValueError("cf_units param must be a string of the form '<time units> since <reference time>'")


def resolution_standard_name(seconds):
    '''Return a standard descriptive string given a time resolution in seconds'''
    for m in [1, 2, 5, 15, 30]:
        if seconds == time_to_seconds(m, 'minutes'):
            return '{}-minute'.format(m)
    for h in [1, 3, 6, 12]:
        if seconds == time_to_seconds(h, 'hours'):
            return '{}-hourly'.format(h)
    if seconds == time_to_seconds(1, 'days'):
        return 'daily'
    # A month can have between 28 and 31 days in it, depending on calendar and leap-yearness.
    # To simplify processing of median values, allow any value between these limits even though the actual
    # possible set is relatively small (but hard to precompute).
    if time_to_seconds(28, 'days') <= seconds <= time_to_seconds(31, 'days'):
        return 'monthly'
    # A season can have between 88 and 92 days in it, depending on calendar and leap-yearness.
    # To simplify processing of median values, allow any value between these limits even though the actual
    # possible set is relatively small (but hard to precompute).
    if time_to_seconds(88, 'days') <= seconds <= time_to_seconds(92, 'days'):
        return 'seasonal'
    for d in [360, 365, 366]:
        if seconds == time_to_seconds(d, 'days'):
            return 'yearly'
    return 'other'


def time_to_seconds(x, units='seconds'):
    '''Return the number of seconds equal to `x` `units` of time, e.g., 10 minutes'''
    seconds_per_unit = {
        'seconds': 1,
        'minutes': 60,
        'hours': 3600,
        'days': 86400,
    }
    if units in seconds_per_unit:
        return x * seconds_per_unit[units]
    else:
        raise ValueError("No conversions available for unit '{}'".format(units))


def to_datetime(value):
    """Convert (iterables of) datetime-like values to real datetime values.

    WARNING: Does not recode for non-standard calendars.

    Motivation: NetCDF.num2date returns a 'phony' datetime-like object when the calendar is not one of
    'proleptic_gregorian', 'standard' or 'gregorian'.
    See http://unidata.github.io/netcdf4-python/#netCDF4.num2date for more details.

    In some cases, a phony datetime object is not acceptable. For example,
    SQLite DateTime type only accepts Python datetime and date objects as input.

    This function creates a true python datetime object from a phony one by mapping the
    date and time attributes from the latter to the former.
    """
    # TODO: Convert time values in case of 360_day calendar?
    # See https://github.com/pacificclimate/modelmeta/blob/master/db/index_netcdf.r#L468-L479
    if isinstance(value, collections.Iterable):
        return (to_datetime(v) for v in value)
    if isinstance(value, (datetime, date)):
        return value
    return datetime(
        *(getattr(value, attr) for attr in 'year month day'.split()),
        **{attr: getattr(value, attr) for attr in 'hour minute second microsecond'.split()}
    )


def d2s(date):
    '''Equivalent of datetime.strftime(d, '%Y-%m-%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}-{m}-{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))


def d2ss(date):
    '''Equivalent of datetime.strftime(d, '%Y%m%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}{m}{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))

