from pytest import mark
from netCDF4 import num2date
from nchelpers.util import time_to_seconds


def test_first_MiB_md5sum(tiny_gcm):
    assert tiny_gcm.first_MiB_md5sum == b'>\xb8\x12\xcc\xa96is\xb4\x10x\xb0\xbf\x19\xfe;'


def test_dependent_varnames(tiny_gcm):
    assert set(tiny_gcm.dependent_varnames) == {'tasmax'}


def test_dim_names(tiny_gcm):
    assert set(tiny_gcm.dim_names()) == {'time', 'lon', 'lat', 'nb2'}


@mark.parametrize('dim_name, expected', (
        (['time'], {'T': 'time'}),
        (['time', 'lon'], {'T': 'time', 'X': 'lon'}),
        (None, {'T': 'time', 'X': 'lon', 'Y': 'lat'})
))
def test_dim_axes_from_names(tiny_gcm, dim_name, expected):
    assert tiny_gcm.dim_axes_from_names(dim_name) == expected


@mark.parametrize('dim_name, expected', (
        (['time'], {'time': 'T'}),
        (['time', 'lon'], {'time': 'T', 'lon': 'X'}),
        (None, {'time': 'T', 'lon': 'X', 'lat': 'Y'})
))
def test_dim_axes(tiny_gcm, dim_name, expected):
    assert tiny_gcm.dim_axes(dim_name) == expected


def test_climatology_bounds_var_name(tiny_gcm):
    # TODO: Create a positive test for this method/property
    assert tiny_gcm.climatology_bounds_var_name == None


def test_is_multi_year_mean(tiny_gcm):
    # TODO: Create a positive test for this method/property
    assert tiny_gcm.is_multi_year_mean == False


def test_time_steps(tiny_gcm):
    time = tiny_gcm.variables['time']
    time_steps = tiny_gcm.time_steps
    assert time_steps['units'] == time.units
    assert time_steps['calendar'] == time.calendar
    assert len(time_steps['numeric']) == len(time[:])
    assert time_steps['numeric'][0] == 5475.5
    assert time_steps['numeric'][-1] == 9125.5
    assert len(time_steps['datetime']) == len(time[:])
    for i in [0, -1]:
        assert time_steps['datetime'][i] == num2date(time[i], time.units, time.calendar)


def test_time_range(tiny_gcm):
    assert tiny_gcm.time_range == (5475.5, 9125.5)


def test_time_range_formatted(tiny_gcm):
    assert tiny_gcm.time_range_formatted == '19650101-19750101'


def test_time_step_size(tiny_gcm):
    assert tiny_gcm.time_step_size == time_to_seconds(1, 'days')


def test_time_resolution(tiny_gcm):
    assert tiny_gcm.time_resolution == 'daily'


def test_metadata(tiny_gcm):
    assert tiny_gcm.metadata.institution == 'BNU'
    assert tiny_gcm.metadata.model == 'BNU-ESM'
    assert tiny_gcm.metadata.emissions == 'historical'
    assert tiny_gcm.metadata.run == 'r1i1p1'
    assert tiny_gcm.metadata.project == 'CMIP5'


def test_unique_id(tiny_gcm):
    assert tiny_gcm.unique_id == 'tasmax_daily_BNU-ESM_historical_r1i1p1_19650101-19750101'


def test_is_unprocessed_model_output(tiny_gcm):
    assert tiny_gcm.is_unprocessed_model_output == True


def test_climo_periods(tiny_gcm):
    # TODO: Create a more interesting test for this property
    assert set(tiny_gcm.climo_periods.keys()) == set()