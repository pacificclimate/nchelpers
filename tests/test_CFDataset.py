"""Test class CFDataset against two 'tiny' data files, one a GCM output and one a downscaled GCM output.
The data in these files is very limited spatially and temporally (though valid) in order to reduce their size,
and their global metadata is standard.

All tests are parameterized over these two files, usually via the indirected fixture object `tiny_dataset`.
"""
from datetime import datetime
from pytest import mark
from netCDF4 import num2date
from nchelpers.date_utils import time_to_seconds


# Test CFDataset properties that can be tested with a simple equality test. Most are of this kind.
@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'first_MiB_md5sum', b'>\xb8\x12\xcc\xa96is\xb4\x10x\xb0\xbf\x19\xfe;'),
    ('gcm', 'climatology_bounds_var_name', None),
    ('gcm', 'is_multi_year_mean', False),
    ('gcm', 'time_range', (5475.5, 9125.5)),
    ('gcm', 'time_range_formatted', '19650101-19750101'),
    ('gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('gcm', 'time_resolution', 'daily'),
    ('gcm', 'is_unprocessed_model_output', True),
    ('gcm', 'ensemble_member', 'r1i1p1'),
    ('gcm', 'cmor_filename', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101.nc'),
    ('gcm', 'unique_id', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101'),
    ('downscaled', 'first_MiB_md5sum', b"['\xecD~;\n\xe6\xf3\x05\x7f\x0c9\x99]\xac"),
    ('downscaled', 'climatology_bounds_var_name', None),
    ('downscaled', 'is_multi_year_mean', False),
    ('downscaled', 'time_range', (711857.5, 767008.5)),
    ('downscaled', 'time_range_formatted', '19500101-21001231'),
    ('downscaled', 'time_step_size', time_to_seconds(1, 'days')),
    ('downscaled', 'time_resolution', 'daily'),
    ('downscaled', 'is_unprocessed_model_output', False),
    ('downscaled', 'ensemble_member', 'r1i1p1'),
    ('downscaled', 'cmor_filename', 'tasmax_day_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_19500101-21001231.nc'),
    ('downscaled', 'unique_id', 'tasmax_day_BCCAQ2_ACCESS1-0_historical-rcp45_r1i1p1_19500101-21001231'),
], indirect=['tiny_dataset'])
def test_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset, prop) == expected


@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'project', 'CMIP5'),
    ('gcm', 'institution', 'BNU'),
    ('gcm', 'model', 'BNU-ESM'),
    ('gcm', 'emissions', 'historical'),
    ('gcm', 'run', 'r1i1p1'),
    ('downscaled', 'project', 'CMIP5'),
    ('downscaled', 'institution', 'PCIC'),
], indirect=['tiny_dataset'])
def test_metadata_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset.metadata, prop) == expected


# The dimensions in both datasets (gcm, downscaled) are the same. This simplifies parameterization.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
@mark.parametrize('dim_name, expected', [
    (['time'], {'T': 'time'}),
    (['time', 'lon'], {'T': 'time', 'X': 'lon'}),
    (None, {'T': 'time', 'X': 'lon', 'Y': 'lat'})
])
def test_dim_axes_from_names(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes_from_names(dim_name) == expected


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time', 'lon', 'lat', 'nb2'}),
    ('downscaled', {'time', 'lon', 'lat'})
], indirect=['tiny_dataset'])
def test_dim_names(tiny_dataset, expected):
    assert set(tiny_dataset.dim_names()) == expected


# The dimensions in both datasets (gcm, downscaled) are the same. This simplifies parameterization.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
@mark.parametrize('dim_name, expected', (
        (['time'], {'time': 'T'}),
        (['time', 'lon'], {'time': 'T', 'lon': 'X'}),
        (None, {'time': 'T', 'lon': 'X', 'lat': 'Y'})
))
def test_dim_axes(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes(dim_name) == expected


# The variables in both datasets (gcm, downscaled) are the same. This simplifies parameterization.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
def test_dependent_varnames(tiny_dataset):
    assert set(tiny_dataset.dependent_varnames) == {'tasmax'}


# The time variable in both dataset (gcm, downscaled) is the same. This simplifies parameterization.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
def test_time_var(tiny_dataset):
    assert tiny_dataset.time_var.name == 'time'
    assert tiny_dataset.time_var.standard_name == 'time'


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 711857.5, 767008.5),
], indirect=['tiny_dataset'])
def test_time_var_values(tiny_dataset, start_time, end_time):
    assert tiny_dataset.time_var_values[0] == start_time
    assert tiny_dataset.time_var_values[-1] == end_time


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 711857.5, 767008.5),
], indirect=['tiny_dataset'])
def test_time_steps(tiny_dataset, start_time, end_time):
    time = tiny_dataset.variables['time']
    time_steps = tiny_dataset.time_steps
    assert time_steps['units'] == time.units
    assert time_steps['calendar'] == time.calendar
    assert len(time_steps['numeric']) == len(time[:])
    assert time_steps['numeric'][0] == start_time
    assert time_steps['numeric'][-1] == end_time
    assert len(time_steps['datetime']) == len(time[:])
    for i in [0, -1]:
        assert time_steps['datetime'][i] == num2date(time[i], time.units, time.calendar)


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', set()),
    ('downscaled', {'6190', '7100', '8110', '2020', '2050', '2080'}),
], indirect=['tiny_dataset'])
def test_climo_periods(tiny_dataset, expected):
    assert set(tiny_dataset.climo_periods.keys()) == expected


@mark.parametrize('tiny_dataset, pattern, all_vars', [
    ('gcm', '{}_Amon_BNU-ESM_historical_r1i1p1_20000101-20101231.nc', 'tasmax'),
    ('downscaled', '{}_Amon_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_20000101-20101231.nc', 'tasmax'),
], indirect=['tiny_dataset'])
@mark.parametrize('variable', [None, 'var'])
def test_climo_output_filename(tiny_dataset, pattern, all_vars, variable):
    assert tiny_dataset.climo_output_filename(datetime(2000, 1, 1), datetime(2010, 12, 31), variable) == \
           pattern.format(variable or all_vars)