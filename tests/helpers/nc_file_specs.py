"""
Helper module for testing `get_climatology_bounds_var_name` and `get_is_multi_year_mean`.
Provides facilities for creating NetCDF files programmatically.
"""
from netCDF4 import Dataset


def create_fake_nc_dataset(filepath, spec):
    """
    Create a NetCDF dataset with contents defined by a static specification object.

    :param filepath (str): filepath of NetCDF file to be created
    :param spec (dict): specification object
    :return: None

    Creating from a static specification object (a nested dict) simplifies the definition and creation of
    a variety of NetCDF files for testing. Declarative coding FTW!

    The specification object has the general form::

        {
            'dimensions': {
                <dim name>: <size>,
                ...
            },
            'variables': {
                <var name>: {
                    'dimensions': (<dim name>, ...),
                    'datatype': <datatype>,
                    'attrs': {
                        <attr name>: <attr value>,
                        ...
                    },
                    'values': <var values>
                },
                ...
            }
        }
    """
    nc = Dataset(filepath, mode='w')

    if 'dimensions' in spec:
        for name, size in spec['dimensions'].items():
            nc.createDimension(name, size)

    if 'variables' in spec:
        for name, var_spec in spec['variables'].items():
            variable = nc.createVariable(name, var_spec['datatype'], dimensions=var_spec['dimensions'])
            if 'attrs' in var_spec and var_spec['attrs']:
                for name, value in var_spec['attrs'].items():
                    variable.setncattr(name, value)
            if 'values' in var_spec and var_spec['values']:
                for i, value in enumerate(var_spec['values']):
                    variable[i] = value

    nc.close()


# The following functions, culminating with `spec`, build specification objects for various
# cases of interest to test code.

def dimensions(bounds):
    result = {'time': None}
    if bounds:
        result.update({'bnds': 2})
    return result


def base_time_var_attrs(units='days since 1850-01-01 00:00:00', calendar='365_day'):
    return {
        'units': units,
        'calendar': calendar,
    }


def time_var_attrs(time_bounds_attr):
    result = base_time_var_attrs()
    if time_bounds_attr:
        result.update(time_bounds_attr)
    return result


def time_var(time_bounds_attr, time_values):
    result = {
        'dimensions': ('time',),
        'datatype': 'd',
        'attrs': time_var_attrs(time_bounds_attr),
        'values': time_values
    }
    return result


def time_bounds_var(time_bounds_values):
    result = {
        'dimensions': ('time', 'bnds'),
        'datatype': 'd',
        'attrs': base_time_var_attrs(),
        'values': time_bounds_values
    }
    return result


def variables(time_bounds_attr, time_bounds_var_name, time_bounds_values, time_values):
    result = {
        'time': time_var(time_bounds_attr, time_values)
    }
    if time_bounds_var_name:
        result.update({
            time_bounds_var_name: time_bounds_var(time_bounds_values)
        })
    return result


def spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=None):
    return {
        'dimensions': dimensions(bool(tb_var_name)),
        'variables': variables(tb_attr, tb_var_name, tb_values, t_values)
    }