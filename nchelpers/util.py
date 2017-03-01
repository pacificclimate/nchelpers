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


def standard_climo_periods(calendar='standard'):
    standard_climo_years = {
        '6190': ['1961', '1990'],
        '7100': ['1971', '2000'],
        '8110': ['1981', '2010'],
        '2020': ['2010', '2039'],
        '2050': ['2040', '2069'],
        '2080': ['2070', '2099']
    }
    day = '30' if calendar == '360_day' else '31'
    return dict([(k, (s2d(year[0]+'-01-01'), s2d(year[1]+'-12-'+day))) for k, year in standard_climo_years.items()])


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


# Date conversion functions

def s2d(s):
    return datetime.strptime(s, '%Y-%m-%d')


def ss2d(s):
    return datetime.strptime(s, '%Y%m%d')


def d2s(date):
    '''Equivalent of datetime.strftime(d, '%Y-%m-%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}-{m}-{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))


def d2ss(date):
    '''Equivalent of datetime.strftime(d, '%Y%m%d'), but
    gets around the idiotic Python 2.7 strftime limitation of year >= 1900'''
    return '{y}{m}{d}'.format(y=str(date.year), m=str(date.month).zfill(2), d=str(date.day).zfill(2))

