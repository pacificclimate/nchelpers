from datetime import datetime


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


def d2s(date):
    '''Equivalent of datetime.strftime(d, '%Y-%m-%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}-{m}-{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))


def d2ss(date):
    '''Equivalent of datetime.strftime(d, '%Y%m%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}{m}{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))

