from datetime import datetime, date
import collections
import re

from nchelpers.exceptions import CFAttributeError, CFValueError


def time_scale(time_var):
    try:
        units = time_var.units
    except AttributeError:
        raise CFAttributeError("Time variable '{}' lacks 'units' attribute"
                               .format(time_var.name))
    match = re.match('(days|hours|minutes|seconds) since.*', units)
    if match:
        return match.groups()[0]
    else:
        raise CFValueError("cf_units param must be a string of the form "
                           "'<time units> since <reference time>'")


def resolution_standard_name(seconds):
    """Return a standard descriptive string given a time resolution in seconds.
    """
    for m in [1, 2, 5, 15, 30]:
        if seconds == time_to_seconds(m, 'minutes'):
            return '{}-minute'.format(m)
    for h in [1, 3, 6, 12]:
        if seconds == time_to_seconds(h, 'hours'):
            return '{}-hourly'.format(h)
    if seconds == time_to_seconds(1, 'days'):
        return 'daily'
    # A month can have between 28 and 31 days in it, depending on calendar 
    # and leap-yearness. To simplify processing of median values, allow any 
    # value between these limits even though the actual possible set is 
    # relatively small (but hard to precompute).
    if time_to_seconds(28, 'days') <= seconds <= time_to_seconds(31, 'days'):
        return 'monthly'
    # A season can have between 88 and 92 days in it, depending on calendar 
    # and leap-yearness. To simplify processing of median values, allow any 
    # value between these limits even though the actual possible set is 
    # relatively small (but hard to precompute).
    if time_to_seconds(88, 'days') <= seconds <= time_to_seconds(92, 'days'):
        return 'seasonal'
    for d in [360, 365, 366]:
        if seconds == time_to_seconds(d, 'days'):
            return 'yearly'
    return 'other'


seconds_per_unit = {
    'seconds': 1,
    'minutes': 60,
    'hours': 3600,
    'days': 86400,
}


def time_to_seconds(x, units='seconds'):
    """Return the number of seconds equal to ``x`` ``units`` of time,
    e.g., 10 minutes -> 600"""
    if units in seconds_per_unit:
        return x * seconds_per_unit[units]
    else:
        raise CFValueError(
            "No conversions available for unit '{}'".format(units))


def seconds_to_time(s, units='seconds'):
    """Return the number of ``units`` equal to ``s`` seconds of time, e.g.,
    600 -> 10 minutes"""
    if units in seconds_per_unit:
        return s / seconds_per_unit[units]
    else:
        raise CFValueError(
            "No conversions available for unit '{}'".format(units))


remapping_month_lengths = (31, 28, 31, 30, 30, 30, 30, 30, 30, 30, 30, 30)

def cumsum(items):
    total = 0
    yield total
    for item in items:
        total += item
        yield total


remapping_month_ends = list(reversed(list(cumsum(remapping_month_lengths))))

def jday_360_to_remapped_month_day(jday_360):
    """Map a Julian day (day of year) in a 360-day calendar to a standard
    calendar (month, day) pair -- no leap year (Feb always has 28 days).
    This mapping is a bit peculiar in Jan, Feb, and Mar; outside of those dates
    it's straightforward.
    """
    for index, end in enumerate(remapping_month_ends):
        if jday_360 > end:
            return 13 - index, jday_360 - end


def to_datetime(value):
    """Convert (iterables of) datetime-like values to real datetime values.

    WARNING: Does not recode for non-standard calendars.

    Motivation: NetCDF.num2date returns a 'phony' datetime-like object when 
    the calendar is not one of 'proleptic_gregorian', 'standard' or 'gregorian'.
    See http://unidata.github.io/netcdf4-python/#netCDF4.num2date 
    for more details.

    In some cases, a phony datetime object is not acceptable. For example,
    SQLite DateTime type only accepts Python datetime and date objects as input.

    This function creates a true python datetime object from a phony one by 
    mapping the date and time attributes from the latter to the former.
    """
    # TODO: Convert time values in case of 360_day calendar?
    # See https://github.com/pacificclimate/modelmeta/blob/master/db/index_netcdf.r#L468-L479
    if isinstance(value, collections.Iterable):
        return (to_datetime(v) for v in value)

    if isinstance(value, (datetime, date)):
        return value

    year, month, day = \
        (getattr(value, attr) for attr in 'year month day'.split())
    if getattr(value, 'calendar', None) == '360_day':
        month, day = jday_360_to_remapped_month_day(value.dayofyr)
    return datetime(
        year, month, day,
        **{attr: getattr(value, attr) 
           for attr in 'hour minute second microsecond'.split()}
    )


def d2s(date):
    """Equivalent of datetime.strftime(d, '%Y-%m-%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900"""
    return '{y}-{m}-{d}'.format(
        y=str(date.year),
        m=str(date.month).zfill(2), 
        d=str(date.day).zfill(2)
    )


def d2ss(date):
    """Equivalent of datetime.strftime(d, '%Y%m%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900"""
    return '{y}{m}{d}'.format(
        y=str(date.year), 
        m=str(date.month).zfill(2), 
        d=str(date.day).zfill(2)
    )

def truncate_to_resolution(date, resolution):
    """Given a datetime and a resolution, returns the earliest
    datetime in the same resolution-sized chunk as the input date.
    Useful for checking whether two timestamps are the same month,
    season, etc.
    Seasonal truncation behaves unintuitively: January and February
    dates will be truncated to December 1 of the *previous* year,
    reflecting that winter crosses the year boundary."""
    if 'minute' in resolution:
        n = re.match('^(\d+)-minute$',resolution)
        if n and int(n.group(1)) in [1, 2, 5, 15, 30]:
            return datetime(date.year, date.month, date.day, date.hour,
                            date.minute - (date.minute % int(n.group(1))))
    elif 'hourly' in resolution:
        n = re.match('^(\d+)-hourly$',resolution)
        if n and int(n.group(1)) in [1, 3, 6, 12]:
            return datetime(date.year, date.month, date.day,
                            date.hour - (date.hour % int(n.group(1))))
    elif resolution == 'daily':
        return datetime(date.year, date.month, date.day)
    elif resolution == 'monthly':
        return datetime(date.year, date.month, 1)
    elif resolution == 'seasonal':
        if date.month <= 2:  # winter began in the previous year.
            return datetime(date.year - 1, 12, 1)
        else:
            return datetime(date.year, date.month - (date.month % 3), 1)
    elif resolution == 'yearly':
        return datetime(date.year, 1, 1)
    #unrecognized resolution.
    raise ValueError("Unsupported time resolution: {}".format(resolution))

