"""Test class CFDataset against 'tiny' data files:

    tiny_gcm: unprocessed GCM output
    tiny_downscaled: downscaled GCM output
    tiny_hydromodel_obs: Interpolated observation-forced hydrological model output
    tiny_hydromodel_gcm: GCM-forced hydrological model output

The data in these files is very limited spatially and temporally (though valid) in order to reduce their size,
and their global metadata is standard.

All tests are parameterized over these files, which requires a little trickiness with fixtures.
pytest doesn't directly support parametrizing over fixtures (which here delivers the test input file)
To get around that, we use indirect fixtures, which are passed a parameter
that they use to determine their behaviour, i.e. what input file to return.
"""
from datetime import datetime
import os

from pytest import mark, raises, approx

from netCDF4 import num2date

from nchelpers import CFDataset
from nchelpers.date_utils import time_to_seconds

from .helpers.nc_file_specs import spec
from .helpers.time_values import suspicious_time_values, non_suspicious_time_values

# TODO: Get a real GCM-driven hydromodel output file and adjust tiny_hydromodel_gcm.nc and its tests as necessary

# TODO: Create an observation-driven hydromodel output file and use it to create tiny_hydromodel_obs.nc and tests
# Arelia is preparing such a file as of Apr 4.

# TODO: Get an RCM output file and test against it. (Driven by property 'model_type'.)


@mark.parametrize('raw_dataset, converter, expected', [
    # absolute path
    ('{cwd}/nchelpers/data/tiny_gcm.nc', None, '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'abspath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'normpath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'realpath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
    # relative path
    ('./nchelpers/data/tiny_gcm.nc', None, './nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'abspath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'normpath', 'nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'realpath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
    # relative path with symlink
    ('./nchelpers/data/ln_tiny_gcm.nc', None, './nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'abspath', '{cwd}/nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'normpath', 'nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'realpath', '{cwd}/nchelpers/data/tiny_gcm.nc'),
], indirect=['raw_dataset'])
def test_filepath(cwd, raw_dataset, converter, expected):
    assert raw_dataset.filepath(converter) == expected.format(cwd=cwd)


# Test CFDataset properties that can be tested with a simple equality test. Most are of this kind.
@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'first_MiB_md5sum', '3eb812cca9366973b41078b0bf19fe3b'),
    ('gcm', 'md5', '3eb812cca9366973b41078b0bf19fe3b'),
    ('gcm', 'climatology_bounds_var_name', None),
    ('gcm', 'is_multi_year_mean', False),
    ('gcm', 'time_range', (5475.5, 9125.5)),
    ('gcm', 'time_range_formatted', '19650101-19750101'),
    ('gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('gcm', 'time_resolution', 'daily'),
    ('gcm', 'is_unprocessed_gcm_output', True),
    ('gcm', 'is_downscaled_output', False),
    ('gcm', 'is_hydromodel_output', False),
    ('gcm', 'is_hydromodel_dgcm_output', False),
    # ('gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('gcm', 'model_type', 'GCM'),
    ('gcm', 'ensemble_member', 'r1i1p1'),
    ('gcm', 'cmor_filename', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101.nc'),
    ('gcm', 'unique_id', 'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101'),

    ('downscaled', 'first_MiB_md5sum', '57eb791548dd7f8dbda5fc12c96ff8af'),
    ('downscaled', 'md5', '57eb791548dd7f8dbda5fc12c96ff8af'),
    ('downscaled', 'climatology_bounds_var_name', None),
    ('downscaled', 'is_multi_year_mean', False),
    ('downscaled', 'time_range', (715509.5, 727196.5)),
    ('downscaled', 'time_range_formatted', '19600101-19911231'),
    ('downscaled', 'time_step_size', time_to_seconds(1, 'days')),
    ('downscaled', 'time_resolution', 'daily'),
    ('downscaled', 'is_unprocessed_gcm_output', False),
    ('downscaled', 'is_downscaled_output', True),
    ('downscaled', 'is_hydromodel_output', False),
    ('downscaled', 'is_hydromodel_dgcm_output', False),
    # ('downscaled', 'is_hydromodel_iobs_output', False), # TODO
    ('downscaled', 'model_type', 'GCM'),
    ('downscaled', 'ensemble_member', 'r1i1p1'),
    ('downscaled', 'cmor_filename', 'tasmax_day_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_19600101-19911231.nc'),
    ('downscaled', 'unique_id', 'tasmax_day_BCCAQ2_ACCESS1-0_historical-rcp45_r1i1p1_19600101-19911231'),

    ('hydromodel_gcm', 'first_MiB_md5sum', 'b2b33021719da5cd63befe07185dbfe2'),
    ('hydromodel_gcm', 'md5', 'd4273596b44a70cecc7b5636e74d86b5'),
    ('hydromodel_gcm', 'climatology_bounds_var_name', None),
    ('hydromodel_gcm', 'is_multi_year_mean', False),
    ('hydromodel_gcm', 'time_range', (0.0, 4382.0)),
    ('hydromodel_gcm', 'time_range_formatted', '19840101-19951231'),
    ('hydromodel_gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('hydromodel_gcm', 'time_resolution', 'daily'),
    ('hydromodel_gcm', 'is_unprocessed_gcm_output', False),
    ('hydromodel_gcm', 'is_downscaled_output', False),
    ('hydromodel_gcm', 'is_hydromodel_output', True),
    ('hydromodel_gcm', 'is_hydromodel_dgcm_output', True),
    # ('hydromodel_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('hydromodel_gcm', 'model_type', 'GCM'),
    ('hydromodel_gcm', 'ensemble_member', 'r1i1p1'),
    ('hydromodel_gcm', 'cmor_filename',
     'BASEFLOW+EVAP+GLAC_AREA_BAND+GLAC_MBAL_BAND+RUNOFF+SWE_BAND_day_VICGL+RGM+HydroCon_ACCESS1-0_historical+rcp45_r1i1p1_19840101-19951231.nc'),
    ('hydromodel_gcm', 'unique_id', 
     'BASEFLOW-EVAP-GLAC_AREA_BAND-GLAC_MBAL_BAND-RUNOFF-SWE_BAND_day_VICGL-RGM-HydroCon_ACCESS1-0_historical-rcp45_r1i1p1_19840101-19951231'),

    # Note: The following properties are not meaningful for a climatological output file and so are not tested:
    #   time_range
    #   time_range_formatted
    #   time_step_size
    ('climo_gcm', 'first_MiB_md5sum', 'b9ce45acbefae185fbbc4028e57e6758'),
    ('climo_gcm', 'md5', 'b9ce45acbefae185fbbc4028e57e6758'),
    ('climo_gcm', 'climatology_bounds_var_name', 'climatology_bnds'),
    ('climo_gcm', 'is_multi_year_mean', True),
    ('climo_gcm', 'time_resolution', 'monthly,seasonal,yearly'),
    ('climo_gcm', 'is_unprocessed_gcm_output', True), # actually so, though the term 'unprocessed' here is misleading
    ('climo_gcm', 'is_downscaled_output', False),
    ('climo_gcm', 'is_hydromodel_output', False),
    ('climo_gcm', 'is_hydromodel_dgcm_output', False),
    # ('climo_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('climo_gcm', 'model_type', 'GCM'),
    ('climo_gcm', 'cmor_filename', 'tasmax_msaClim_BNU-ESM_historical_r1i1p1_19650101-19701230.nc'),
    ('climo_gcm', 'unique_id', 'tasmax_msaClim_BNU-ESM_historical_r1i1p1_19650101-19701230'),
], indirect=['tiny_dataset'])
def test_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset, prop) == expected


# Setup for testing `get_climatology_bounds_var_name`
# and `get_is_multi_year_mean`, which depends on `get_climatology_bounds_var_name`.
#
# These cases are shared between the two methods, so each case includes expected output for both.
# Each test function ignores the other's expected output parameter.
# Each tuple correspnods to the following arguments: 
#   `(file_spec, strict, expected_climatology_bounds_var_name, expected_is_multi_year_mean)`
#
# The alert reader will note that in all current test cases,
#   `expected_is_multi_year_mean == bool(expected_climatology_bounds_var_name)`
# However, this is not necessarily so, and at least one potential refinement to `is_multi_year_mean` will
# change this relationship. Hence the explicit distinction between the two values.

likely_climo_bounds_var_names = ['climatology_bounds', 'climatology_bnds', 'climo_bounds', 'climo_bnds']
likely_time_bounds_var_names = ['time_bounds', 'time_bnds']

# Use a non-"suspcicious" number of time values to prevent false positives from that heuristic.
narrow_time_bounds = [[0, 10], [10, 20]]
narrow_time_values = [5, 15]

wide_time_bounds = [[0, 3650], [30, 3680]]
wide_time_values = [1825, 1855]

# Starred components in lists would make this list construction much tidier, but Py <3.5 doesn't support that.
climo_bounds_var_test_cases = (
    # Without time variable
    [
        ({}, strict, None, False)
        for strict in [False, True]
    ] +

    # All subsequent tests with time variable ...

    # Without time:climatology or time:bounds attr; without bounds variable
    [
        (spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=None), strict, None, False)
        for strict in [False, True]
    ] +

    # With time:climatology attr; without climo bounds variable
    # Note: does not check existence of variable. Is this right?
    [
        (spec(tb_attr={'climatology': 'foo'}, tb_var_name=None, tb_values=None, t_values=None), strict, 'foo', True)
        for strict in [False, True]
    ] +

    # With time:climatology attr; with climo bounds variable
    # Use non-canonical bounds var name, to prevent false success with likely-name heuristic
    [
        (spec(tb_attr={'climatology': 'foo'}, tb_var_name='foo', tb_values=None, t_values=None), False, 'foo', True)
        for strict in [False, True]
    ] +

    # Without time:climatology or time:bounds attr; with likely named climo bounds variable
    # Note: no checking of bounds variable contents. Is this right?
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=None, t_values=None), False, name, True)
        for name in likely_climo_bounds_var_names
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=None, t_values=None), True, None, False)
        for name in likely_climo_bounds_var_names
    ] +

    # Without time:climatology or time:bounds attr; without likely named climo bounds variable
    [
        (spec(tb_attr=None, tb_var_name='foo', tb_values=None, t_values=None), strict, None, False)
        for strict in [False, True]
    ] +

    # With time:bounds attr; with time bounds too narrow (< 2 yr)
    [
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo', tb_values=narrow_time_bounds, t_values=narrow_time_values), strict, None, False)
        for strict in [False, True]
    ] +

    # With time:bounds attr; with time bounds broad enough (> 2 yr)
    [
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo', tb_values=wide_time_bounds, t_values=wide_time_values), False, 'foo', True),
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo', tb_values=wide_time_bounds, t_values=wide_time_values), True, None, False),
    ] +

    # Without time:climatology or time:bounds attr; with likely named time bounds var;
    # with time bounds too narrow (10 d < 2 yr)
    [
        (spec(tb_attr=None, tb_var_name=name, tb_values=narrow_time_bounds, t_values=narrow_time_values), strict, None, False)
        for name in likely_time_bounds_var_names
        for strict in [False, True]
    ] +

    # Without time:climatology or time:bounds attr; with likely named time bounds var;
    # with time bounds broad enough (3650 d > 2 yr)
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=wide_time_bounds, t_values=wide_time_values), False, name, True)
        for name in likely_time_bounds_var_names
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=wide_time_bounds, t_values=wide_time_values), True, None, False)
        for name in likely_time_bounds_var_names
    ]
)


@mark.parametrize(
    'fake_nc_dataset, strict, var_name, _',
    climo_bounds_var_test_cases,
    indirect=['fake_nc_dataset']
)
def test_climatology_bounds_var_name(fake_nc_dataset, strict, var_name, _):
    cf = CFDataset(fake_nc_dataset, strict_metadata=strict)
    assert cf.climatology_bounds_var_name == var_name


@mark.parametrize(
    'fake_nc_dataset, strict, _, is_mym',
    # All the cases depending on climo bounds
    climo_bounds_var_test_cases +

    # Without time:climatology or time:bounds attrs; without variable with likely name for climo bounds;
    # without variable with likely name for time bounds and likely contents;
    # with time variable with suspicious length and contents
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=t_values), False, None, True)
        for t_values in suspicious_time_values
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=t_values), True, None, False)
        for t_values in suspicious_time_values
    ] +
    [
        (spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=t_values), strict, None, False)
        for t_values in non_suspicious_time_values
        for strict in [False, True]
    ]
    ,
    indirect=['fake_nc_dataset']
)
def test_is_multi_year_mean(fake_nc_dataset, strict, _, is_mym):
    cf = CFDataset(fake_nc_dataset, strict_metadata=strict)
    assert cf.is_multi_year_mean == is_mym


# Test against some actual files (from climate-explorer-backend tests).
# This is a supplement to the much more thorough but contrived tests with the
# faked nc datasets above.
@mark.parametrize('dataset, is_mym', [
    ('CanESM2-rcp85-tasmax-r1i1p1-2010-2039', True),
    ('prism_pr_small', True),
], indirect=['dataset'])
def test_is_multi_year_mean_against_nonstandard_datasets(dataset, is_mym):
    assert dataset.is_multi_year_mean == is_mym


@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'institute_id', 'BNU'),
    ('gcm', 'model_id', 'BNU-ESM'),
    ('gcm', 'experiment_id', 'historical'),
    ('gcm', 'initialization_method', 1),
    ('gcm', 'physics_version', 1),
    ('gcm', 'realization', 1),

    ('downscaled', 'institute_id', 'CSIRO-BOM'),
    ('downscaled', 'model_id', 'ACCESS1-0'),
    ('downscaled', 'experiment_id', 'historical, rcp45'),
    ('downscaled', 'initialization_method', 1),
    ('downscaled', 'physics_version', 1),
    ('downscaled', 'realization', 1),

    ('hydromodel_gcm', 'institute_id', 'CSIRO-BOM'),
    ('hydromodel_gcm', 'model_id', 'ACCESS1-0'),
    ('hydromodel_gcm', 'experiment_id', 'historical, rcp45'),
    ('hydromodel_gcm', 'initialization_method', 1),
    ('hydromodel_gcm', 'physics_version', 1),
    ('hydromodel_gcm', 'realization', 1),

    ('climo_gcm', 'institute_id', 'BNU'),
    ('climo_gcm', 'model_id', 'BNU-ESM'),
    ('climo_gcm', 'experiment_id', 'historical'),
    ('climo_gcm', 'initialization_method', 1),
    ('climo_gcm', 'physics_version', 1),
    ('climo_gcm', 'realization', 1),
], indirect=['tiny_dataset'])
def test_gcm_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset.gcm, prop) == expected


@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'project', 'CMIP5'),
    ('gcm', 'institution', 'BNU'),
    ('gcm', 'model', 'BNU-ESM'),
    ('gcm', 'emissions', 'historical'),
    ('gcm', 'experiment', 'historical'),
    ('gcm', 'run', 'r1i1p1'),
    ('gcm', 'ensemble_member', 'r1i1p1'),
    
    ('downscaled', 'project', 'CMIP5'),
    ('downscaled', 'institution', 'PCIC'),
    ('downscaled', 'model', 'ACCESS1-0'),
    ('downscaled', 'emissions', 'historical, rcp45'),
    ('downscaled', 'experiment', 'historical, rcp45'),
    ('downscaled', 'run', 'r1i1p1'),
    ('downscaled', 'ensemble_member', 'r1i1p1'),

    ('hydromodel_gcm', 'project', 'CMIP5'),
    ('hydromodel_gcm', 'institution', 'PCIC'),
    ('hydromodel_gcm', 'model', 'ACCESS1-0'),
    ('hydromodel_gcm', 'emissions', 'historical, rcp45'),
    ('hydromodel_gcm', 'experiment', 'historical, rcp45'),
    ('hydromodel_gcm', 'run', 'r1i1p1'),
    ('hydromodel_gcm', 'ensemble_member', 'r1i1p1'),

    ('climo_gcm', 'project', 'CMIP5'),
    ('climo_gcm', 'institution', 'BNU'),
    ('climo_gcm', 'model', 'BNU-ESM'),
    ('climo_gcm', 'emissions', 'historical'),
    ('climo_gcm', 'experiment', 'historical'),
    ('climo_gcm', 'run', 'r1i1p1'),
    ('climo_gcm', 'ensemble_member', 'r1i1p1'),
], indirect=['tiny_dataset'])
def test_metadata_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset.metadata, prop) == expected


@mark.parametrize('tiny_dataset, var_name', [
    ('gcm', 'lat'),
    ('gcm', 'lon'),
], indirect=['tiny_dataset'])
def test_get_var_bounds_and_values(tiny_dataset, var_name):
    bvs = tiny_dataset.var_bounds_and_values(var_name)
    var = tiny_dataset.variables[var_name]
    for i, (lower, value, upper) in enumerate(bvs):
        assert lower < value < upper
        assert value == var[i]


@mark.parametrize('tiny_dataset, var_name, expected', [
    ('gcm', 'time', (5475.5, 9125.5)),
    ('gcm', 'lon', (264.375, 272.8125)),
    ('gcm', 'lat', (65.5776, 73.9475)),
    ('gcm', 'tasmax', (220.68445, 304.13501)),
], indirect=['tiny_dataset'])
def test_variable_range(tiny_dataset, var_name, expected):
    assert tiny_dataset.var_range(var_name) == approx(expected)


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time', 'lon', 'lat', 'nb2'}),
    ('downscaled', {'time', 'lon', 'lat'}),
    ('hydromodel_gcm', {'time', 'lon', 'lat', 'depth'}),
    ('climo_gcm', {'time', 'lon', 'lat', 'bnds'}),
], indirect=['tiny_dataset'])
def test_dim_names(tiny_dataset, expected):
    assert set(tiny_dataset.dim_names()) == expected


# Tests for some dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'climo_gcm',
], indirect=True)
@mark.parametrize('dim_name, expected', [
    (['time'], {'time': 'T'}),
    (['time', 'lon'], {'time': 'T', 'lon': 'X'}),
])
def test_dim_axes_from_names(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes_from_names(dim_name) == expected


# Tests for all dimensions - may differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('downscaled', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('hydromodel_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y', 'depth': 'Z'}),
    ('climo_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
], indirect=['tiny_dataset'])
def test_dim_axes_from_names2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes_from_names() == expected


# Tests for some dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'climo_gcm',
], indirect=True)
@mark.parametrize('dim_name, expected', (
        (['time'], {'time': 'T'}),
        (['time', 'lon'], {'time': 'T', 'lon': 'X'}),
))
def test_dim_axes(tiny_dataset, dim_name, expected):
    assert tiny_dataset.dim_axes(dim_name) == expected


# Tests for all dimensions - may differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('downscaled', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('hydromodel_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y', 'depth': 'Z'}),
    ('climo_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
], indirect=['tiny_dataset'])
def test_dim_axes2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes() == expected


# Tests for all dimensions - may differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('downscaled', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('hydromodel_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat', 'Z': 'depth'}),
    ('climo_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
], indirect=['tiny_dataset'])
def test_axes_dim(tiny_dataset, expected):
    assert tiny_dataset.axes_dim() == expected


# TODO: Obtain a test file with reduced dimensions and test reduced_dims with it.
# Request sent to Stephen Sobie and Trevor Murdock 2017-06-02 for such a file.


@mark.parametrize('tiny_dataset, dim_names, expected', [
    ('gcm', set(), {'tasmax'}),
    ('gcm', {'time'}, {'tasmax'}),
    ('gcm', {'lat', 'lon'}, {'tasmax'}),
    ('gcm', {'foo'}, set()),
    ('downscaled', set(), {'tasmax'}),
    ('hydromodel_gcm', set(), {'RUNOFF', 'BASEFLOW', 'EVAP', 'GLAC_MBAL_BAND', 'GLAC_AREA_BAND', 'SWE_BAND'}),
    ('climo_gcm', set(), {'tasmax'}),
], indirect=['tiny_dataset'])
def test_dependent_varnames(tiny_dataset, dim_names, expected):
    assert set(tiny_dataset.dependent_varnames(dim_names=dim_names)) == expected


@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'climo_gcm',
], indirect=True)
@mark.parametrize('property, standard_name', [
    ('time_var', 'time'),
    ('lon_var', 'longitude'),
    ('lat_var', 'latitude'),
])
def test_common_vars(tiny_dataset, property, standard_name):
    assert getattr(tiny_dataset, property).standard_name == standard_name


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 715509.5, 727196.5),
    ('hydromodel_gcm', 0.0, 4382.0),
    ('climo_gcm', 6585.0, 6752.0), # not exactly start and end for a climo file, but a worthwhile test
], indirect=['tiny_dataset'])
def test_time_var_values(tiny_dataset, start_time, end_time):
    assert tiny_dataset.time_var_values[0] == start_time
    assert tiny_dataset.time_var_values[-1] == end_time


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 715509.5, 727196.5),
    ('hydromodel_gcm', 0.0, 4382.0),
    ('climo_gcm', 6585.0, 6752.0), # not exactly start and end for a climo file, but a worthwhile test
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
    ('downscaled', {'6190'}),
    ('hydromodel_gcm', set()),
    # Not relevant for climo data sets
], indirect=['tiny_dataset'])
def test_climo_periods(tiny_dataset, expected):
    assert set(tiny_dataset.climo_periods.keys()) == expected


@mark.parametrize('tiny_dataset, pattern, all_vars', [
    ('gcm', '{}_msaClim_BNU-ESM_historical_r1i1p1_20000101-20101231.nc', 'tasmax'),
    ('downscaled', '{}_msaClim_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_20000101-20101231.nc', 'tasmax'),
    ('hydromodel_gcm',
     '{}_msaClim_VICGL+RGM+HydroCon_ACCESS1-0_historical+rcp45_r1i1p1_20000101-20101231.nc',
     'BASEFLOW+EVAP+GLAC_AREA_BAND+GLAC_MBAL_BAND+RUNOFF+SWE_BAND'),
    # Not relevant for climo data sets
], indirect=['tiny_dataset'])
@mark.parametrize('variable', [None, 'var'])
def test_climo_output_filename(tiny_dataset, pattern, all_vars, variable):
    assert tiny_dataset.climo_output_filename(datetime(2000, 1, 1), datetime(2010, 12, 31), variable) == \
           pattern.format(variable or all_vars)


class TestIndirectValues:
    """Test the indirect value feature of CFDataset.
    See CFDataset class docstring for explanation of indirect values.
    To test, we use an otherwise empty CFDataset file populated with properties (attributes) for testing.
    For its contents, see conftest.py.
    """

    def test_is_indirected(self, indir_dataset):
        assert not indir_dataset.is_indirected('one')
        assert indir_dataset.is_indirected('uno')
        assert indir_dataset.is_indirected('un')
        assert indir_dataset.is_indirected('foo')  # even if the indirection is circular
        assert indir_dataset.is_indirected('baz')  # even if the indirected property does not exist

    def test_get_direct_value(self, indir_dataset):
        assert indir_dataset.get_direct_value('one') == 1
        assert indir_dataset.get_direct_value('uno') == '@one'

    def test_valid_indirect(self, indir_dataset):
        assert indir_dataset.one == 1
        assert indir_dataset.uno == 1
        assert indir_dataset.un == 1

    def test_indirect_nonexistent(self, indir_dataset):
        assert indir_dataset.baz == '@qux'

    def test_circular_indirection(self, indir_dataset):
        with raises(RuntimeError):
            value = indir_dataset.foo
            print(value)
