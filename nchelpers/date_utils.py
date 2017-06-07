from datetime import datetime, date
import collections


def resolution_standard_name(seconds):
    '''Return a standard descriptive string given a time resolution in seconds'''
    return {
        60: '1-minute',
        120: '2-minute',
        300: '5-minute',
        900: '15-minute',
        1800: '30-minute',
        3600: '1-hourly',
        10800: '3-hourly',
        21600: '6-hourly',
        43200: '12-hourly',
        86400: 'daily',
        2678400: 'monthly',
        2635200: 'monthly',
        2592000: 'monthly',
        31536000: 'yearly',
        31104000: 'yearly',
    }.get(seconds, 'other')


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

