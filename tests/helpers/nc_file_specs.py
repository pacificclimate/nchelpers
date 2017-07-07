"""
Helper module for testing `get_climatology_bounds_var_name` and `get_is_multi_year_mean`.
Provides specs for fixture `fake_nc_dataset` (q.v.), which manufactures a NetCDF file with metadata content
defined by dicts like these.
"""

# These could all be DRYed up into one mondo function, but it would be hard to code and to read.

# Without time variable
without_time_var = {}


# Lacking all clues: no time:climatology attr, no likely named climatology bounds variables,
# no time:bounds attr, no likely named time bounds variables with likely values
without_all = {
    'dimensions': {
        'time': None,
    },
    'variables': {
        'time': {
            'dimensions': ('time',),
            'datatype': 'd',
            'attrs': {
                'units': 'days since 1850-01-01 00:00:00',
                'calendar': '365_day',
            }
        }
    }
}


# With time:climatology attr, but variable does not exist
def with_time_bounds_attr_without_bounds_var(attr_name, var_name):
    return {
        'dimensions': {
            'time': None,
        },
        'variables': {
            'time': {
                'dimensions': ('time',),
                'datatype': 'd',
                'attrs': {
                    'units': 'days since 1850-01-01 00:00:00',
                    'calendar': '365_day',
                    attr_name: var_name,
                },
            },
        },
    }


# Without time:climatology or time:bounds attr, and with named climo/time bounds variable
def without_time_bounds_attr_with_bounds_var(var_name, values=[]):
    return {
        'dimensions': {
            'time': None,
            'bnds': 2,
        },
        'variables': {
            'time': {
                'dimensions': ('time',),
                'datatype': 'd',
                'attrs': {
                    'units': 'days since 1850-01-01 00:00:00',
                    'calendar': '365_day',
                },
            },
            var_name: {
                'dimensions': ('time', 'bnds'),
                'datatype': 'd',
                'attrs': {
                    'units': 'days since 1850-01-01 00:00:00',
                    'calendar': '365_day',
                },
                'values': values
            }
        },
    }

# With time:bounds attr, variable exists
def with_time_bounds_attr_with_bounds_var(attr_name, var_name, values=[]):
    return {
        'dimensions': {
            'time': None,
            'bnds': 2,
        },
        'variables': {
            'time': {
                'dimensions': ('time',),
                'datatype': 'd',
                'attrs': {
                    'units': 'days since 1850-01-01 00:00:00',
                    'calendar': '365_day',
                    attr_name: var_name
                },
            },
            var_name: {
                'dimensions': ('time', 'bnds'),
                'datatype': 'd',
                'attrs': {
                    'units': 'days since 1850-01-01 00:00:00',
                    'calendar': '365_day',
                },
                'values': values
            },
        },
    }
