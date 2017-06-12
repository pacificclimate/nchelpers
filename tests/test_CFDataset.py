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
from pytest import mark, raises, approx
from netCDF4 import num2date
from nchelpers.date_utils import time_to_seconds

# TODO: Get a real GCM-driven hydromodel output file and adjust tiny_hydromodel_gcm.nc and its tests as necessary

# TODO: Create an observation-driven hydromodel output file and use it to create tiny_hydromodel_obs.nc and tests
# Arelia is preparing such a file as of Apr 4.

# TODO: Get an RCM output file and test against it. (Driven by property 'model_type'.)

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
    #   time_resolution
    ('climo_gcm', 'first_MiB_md5sum', 'b9ce45acbefae185fbbc4028e57e6758'),
    ('climo_gcm', 'md5', 'b9ce45acbefae185fbbc4028e57e6758'),
    ('climo_gcm', 'climatology_bounds_var_name', 'climatology_bnds'),
    ('climo_gcm', 'is_multi_year_mean', True),
    ('climo_gcm', 'time_resolution', 'monthly'), # not that this is very meaningful for a climo file
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

    ('climo_gcm', 'project', 'CMIP5'),
    ('climo_gcm', 'institution', 'BNU'),
    ('climo_gcm', 'model', 'BNU-ESM'),
    ('climo_gcm', 'emissions', 'historical'),
    ('climo_gcm', 'run', 'r1i1p1'),
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


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'tasmax'}),
    ('downscaled', {'tasmax'}),
    ('hydromodel_gcm', {'RUNOFF', 'BASEFLOW', 'EVAP', 'GLAC_MBAL_BAND', 'GLAC_AREA_BAND', 'SWE_BAND'}),
    ('climo_gcm', {'tasmax'}),
], indirect=['tiny_dataset'])
def test_dependent_varnames(tiny_dataset, expected):
    assert set(tiny_dataset.dependent_varnames) == expected


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
