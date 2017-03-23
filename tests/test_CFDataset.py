"""Test class CFDataset against 'tiny' data files:

    tiny_gcm: unprocessed GCM output
    tiny_downscaled: downscaled GCM output
    tiny_hydromodel_obs: Interpolated observation-forced hydrological model output
    tiny_hydromodel_gcm: GCM-forced hydrological model output

The data in these files is very limited spatially and temporally (though valid) in order to reduce their size,
and their global metadata is standard.

All tests are parameterized over these files, usually via the indirect fixture object `tiny_dataset`.
"""
from datetime import datetime
from pytest import mark
from netCDF4 import num2date
from nchelpers.date_utils import time_to_seconds

# TODO: Get a real GCM-driven hydromodel output file and adjust tiny_hydromodel_gcm.nc and its tests as necessary

# TODO: Create an observation-driven hydromodel output file and use it to create tiny_hydromodel_obs.nc and tests
# This will follow settling of metadata standard for obs-driven hydromodel output with assistance from Arelia week
# of Mar 20

# Test CFDataset properties that can be tested with a simple equality test. Most are of this kind.
@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'first_MiB_md5sum', b'>\xb8\x12\xcc\xa96is\xb4\x10x\xb0\xbf\x19\xfe;'),
    ('gcm', 'climatology_bounds_var_name', None),
    ('gcm', 'is_multi_year_mean', False),
    ('gcm', 'time_range', (5475.5, 9125.5)),
    ('gcm', 'time_range_formatted', '19650101-19750101'),
    ('gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('gcm', 'time_resolution', 'daily'),
    ('gcm', 'is_unprocessed_gcm_output', True),
    ('gcm', 'is_downscaling_output', False),
    ('gcm', 'is_hydromodel_output', False),
    ('gcm', 'ensemble_member', 'r1i1p1'),
    ('gcm', 'cmor_filename', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101.nc'),
    ('gcm', 'unique_id', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101'),

    ('downscaled', 'first_MiB_md5sum', b'X\x87\xde_\xcd\r\x0f\xe1O-\xb7PF\x9f\xb1z'),
    ('downscaled', 'climatology_bounds_var_name', None),
    ('downscaled', 'is_multi_year_mean', False),
    ('downscaled', 'time_range', (711857.5, 767008.5)),
    ('downscaled', 'time_range_formatted', '19500101-21001231'),
    ('downscaled', 'time_step_size', time_to_seconds(1, 'days')),
    ('downscaled', 'time_resolution', 'daily'),
    ('downscaled', 'is_unprocessed_gcm_output', False),
    ('downscaled', 'is_downscaling_output', True),
    ('downscaled', 'is_hydromodel_output', False),
    ('downscaled', 'ensemble_member', 'r1i1p1'),
    ('downscaled', 'cmor_filename', 'tasmax_day_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_19500101-21001231.nc'),
    ('downscaled', 'unique_id', 'tasmax_day_BCCAQ2_ACCESS1-0_historical-rcp45_r1i1p1_19500101-21001231'),

    # ('hydromodel_gcm', 'first_MiB_md5sum', b'?'), # TODO when the file stops changing
    ('hydromodel_gcm', 'climatology_bounds_var_name', None),
    ('hydromodel_gcm', 'is_multi_year_mean', False),
    ('hydromodel_gcm', 'time_range', (0.0, 4382.0)),
    ('hydromodel_gcm', 'time_range_formatted', '19840101-19951231'),
    ('hydromodel_gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('hydromodel_gcm', 'time_resolution', 'daily'),
    ('hydromodel_gcm', 'is_unprocessed_gcm_output', False),
    ('hydromodel_gcm', 'is_downscaling_output', False),
    ('hydromodel_gcm', 'is_hydromodel_output', True),
    ('hydromodel_gcm', 'ensemble_member', 'r1i1p1'),
    ('hydromodel_gcm', 'cmor_filename',
     'BASEFLOW+EVAP+GLAC_AREA_BAND+GLAC_MBAL_BAND+RUNOFF+SWE_BAND_day_VICGL+RGM+HydroCon_ACCESS1-0_historical+rcp45_r1i1p1_19840101-19951231.nc'),
    ('hydromodel_gcm', 'unique_id', 
     'BASEFLOW-EVAP-GLAC_AREA_BAND-GLAC_MBAL_BAND-RUNOFF-SWE_BAND_day_VICGL-RGM-HydroCon_ACCESS1-0_historical-rcp45_r1i1p1_19840101-19951231'),
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
    
    ('hydromodel_gcm', 'project', 'CMIP5'),
    ('hydromodel_gcm', 'institution', 'PCIC'),
], indirect=['tiny_dataset'])
def test_metadata_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset.metadata, prop) == expected


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time', 'lon', 'lat', 'nb2'}),
    ('downscaled', {'time', 'lon', 'lat'}),
    ('hydromodel_gcm', {'time', 'lon', 'lat', 'depth'})
], indirect=['tiny_dataset'])
def test_dim_names(tiny_dataset, expected):
    assert set(tiny_dataset.dim_names()) == expected


# Tests for dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
@mark.parametrize('dim_name, expected', [
    (['time'], {'T': 'time'}),
    (['time', 'lon'], {'T': 'time', 'X': 'lon'}),
])
def test_dim_axes_from_names(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes_from_names(dim_name) == expected


# Tests for dimensions that differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('downscaled', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('hydromodel_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'})
], indirect=['tiny_dataset'])
def test_dim_axes_from_names2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes_from_names() == expected


# Tests for dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', ['gcm', 'downscaled'], indirect=True)
@mark.parametrize('dim_name, expected', (
        (['time'], {'time': 'T'}),
        (['time', 'lon'], {'time': 'T', 'lon': 'X'}),
))
def test_dim_axes(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes(dim_name) == expected


# Tests for dimensions that differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('downscaled', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('hydromodel_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'})
], indirect=['tiny_dataset'])
def test_dim_axes2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes() == expected


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'tasmax'}),
    ('downscaled', {'tasmax'}),
    ('hydromodel_gcm', {'RUNOFF', 'BASEFLOW', 'EVAP', 'GLAC_MBAL_BAND', 'GLAC_AREA_BAND', 'SWE_BAND'})
], indirect=['tiny_dataset'])
def test_dependent_varnames(tiny_dataset, expected):
    assert set(tiny_dataset.dependent_varnames) == expected


@mark.parametrize('tiny_dataset', ['gcm', 'downscaled', 'hydromodel_gcm'], indirect=True)
def test_time_var(tiny_dataset):
    assert tiny_dataset.time_var.standard_name == 'time'


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 711857.5, 767008.5),
    ('hydromodel_gcm', 0.0, 4382.0),
], indirect=['tiny_dataset'])
def test_time_var_values(tiny_dataset, start_time, end_time):
    assert tiny_dataset.time_var_values[0] == start_time
    assert tiny_dataset.time_var_values[-1] == end_time


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 711857.5, 767008.5),
    ('hydromodel_gcm', 0.0, 4382.0),
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
    ('hydromodel_gcm', set()),
], indirect=['tiny_dataset'])
def test_climo_periods(tiny_dataset, expected):
    assert set(tiny_dataset.climo_periods.keys()) == expected


@mark.parametrize('tiny_dataset, pattern, all_vars', [
    ('gcm', '{}_msaClim_BNU-ESM_historical_r1i1p1_20000101-20101231.nc', 'tasmax'),
    ('downscaled', '{}_msaClim_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_20000101-20101231.nc', 'tasmax'),
    ('hydromodel_gcm',
     '{}_msaClim_VICGL+RGM+HydroCon_ACCESS1-0_historical+rcp45_r1i1p1_20000101-20101231.nc',
     'BASEFLOW+EVAP+GLAC_AREA_BAND+GLAC_MBAL_BAND+RUNOFF+SWE_BAND'),
], indirect=['tiny_dataset'])
@mark.parametrize('variable', [None, 'var'])
def test_climo_output_filename(tiny_dataset, pattern, all_vars, variable):
    assert tiny_dataset.climo_output_filename(datetime(2000, 1, 1), datetime(2010, 12, 31), variable) == \
           pattern.format(variable or all_vars)