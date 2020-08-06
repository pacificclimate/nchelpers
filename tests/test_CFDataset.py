"""Test class CFDataset against 'tiny' data files:

    tiny_gcm: unprocessed GCM output
    tiny_downscaled: downscaled GCM output
    tiny_hydromodel_obs: Interpolated observation-forced hydrological model
        output
    tiny_hydromodel_gcm: GCM-forced hydrological model output

The data in these files is very limited spatially and temporally (though valid)
in order to reduce their size, and their global metadata is standard.

All tests are parameterized over these files, which requires a little
trickiness with fixtures. ``pytest`` doesn't directly support parametrizing
over fixtures (which here delivers the test input file) To get around that,
we use indirect fixtures, which are passed a parameter that they use to
determine their behaviour, i.e. what input file to return.
"""
from datetime import datetime

from pytest import mark, raises, approx

from netCDF4 import num2date

from nchelpers import CFDataset
from nchelpers.date_utils import time_to_seconds
from nchelpers.exceptions import CFAttributeError, CFValueError

from .helpers.nc_file_specs import spec
from .helpers.time_values import suspicious_time_values, non_suspicious_time_values

# TODO: Get a real GCM-driven hydromodel output file and adjust
# tiny_hydromodel_gcm.nc and its tests as necessary

# TODO: Create an observation-driven hydromodel output file and use it to
# create tiny_hydromodel_obs.nc and tests Arelia is preparing such a file as of
# Apr 4.

# TODO: Get an RCM output file and test against it.
# (Driven by property 'model_type'.)


@mark.parametrize('raw_dataset, converter, expected', [
    # absolute path
    ('{cwd}/nchelpers/data/tiny_gcm.nc', None,
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'abspath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'normpath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('{cwd}/nchelpers/data/tiny_gcm.nc', 'realpath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    # relative path
    ('./nchelpers/data/tiny_gcm.nc', None,
     './nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'abspath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'normpath',
     'nchelpers/data/tiny_gcm.nc'),
    ('./nchelpers/data/tiny_gcm.nc', 'realpath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
    # relative path with symlink
    ('./nchelpers/data/ln_tiny_gcm.nc', None,
     './nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'abspath',
     '{cwd}/nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'normpath',
     'nchelpers/data/ln_tiny_gcm.nc'),
    ('./nchelpers/data/ln_tiny_gcm.nc', 'realpath',
     '{cwd}/nchelpers/data/tiny_gcm.nc'),
], indirect=['raw_dataset'])
def test_filepath(cwd, raw_dataset, converter, expected):
    assert raw_dataset.filepath(converter) == expected.format(cwd=cwd)


# Test CFDataset properties that can be tested with a simple equality test.
# Most are of this kind.
@mark.parametrize('tiny_dataset, prop, expected', [
    ('gcm', 'first_MiB_md5sum', '3eb812cca9366973b41078b0bf19fe3b'),
    ('gcm', 'md5', '3eb812cca9366973b41078b0bf19fe3b'),
    ('gcm', 'climatology_bounds_var_name', None),
    ('gcm', 'sampling_geometry', 'gridded'),
    ('gcm', 'is_multi_year', False),
    ('gcm', 'is_multi_year_mean', False),
    ('gcm', 'time_range', (5475.5, 9125.5)),
    ('gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('gcm', 'time_resolution', 'daily'),
    ('gcm', 'is_unprocessed_gcm_output', True),
    ('gcm', 'is_downscaled_output', False),
    ('gcm', 'is_hydromodel_output', False),
    ('gcm', 'is_hydromodel_dgcm_output', False),
    # ('gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('gcm', 'is_streamflow_model_output', False),
    ('gcm', 'is_streamflow_model_dgcm_output', False),
    ('gcm', 'is_streamflow_model_iobs_output', False),
    ('gcm', 'is_climdex_output', False),
    ('gcm', 'is_climdex_ds_gcm_output', False),
    ('gcm', 'is_gridded_obs', False),
    ('gcm', 'model_type', 'GCM'),
    ('gcm', 'ensemble_member', 'r1i1p1'),
    ('gcm', 'cmor_filename',
     'tasmax_day_BNU-ESM_historical_r1i1p1_19650101-19750101.nc'),

    ('downscaled', 'first_MiB_md5sum', '6ebca934615ad7e6bd328bcc6fa9058b'),
    ('downscaled', 'md5', '6ebca934615ad7e6bd328bcc6fa9058b'),
    ('downscaled', 'climatology_bounds_var_name', None),
    ('downscaled', 'sampling_geometry', 'gridded'),
    ('downscaled', 'is_multi_year', False),
    ('downscaled', 'is_multi_year_mean', False),
    ('downscaled', 'time_range', (715509.5, 727196.5)),
    ('downscaled', 'time_step_size', time_to_seconds(1, 'days')),
    ('downscaled', 'time_resolution', 'daily'),
    ('downscaled', 'is_unprocessed_gcm_output', False),
    ('downscaled', 'is_downscaled_output', True),
    ('downscaled', 'is_hydromodel_output', False),
    ('downscaled', 'is_hydromodel_dgcm_output', False),
    # ('downscaled', 'is_hydromodel_iobs_output', False), # TODO
    ('downscaled', 'is_streamflow_model_output', False),
    ('downscaled', 'is_streamflow_model_dgcm_output', False),
    ('downscaled', 'is_streamflow_model_iobs_output', False),
    ('downscaled', 'is_climdex_output', False),
    ('downscaled', 'is_climdex_ds_gcm_output', False),
    ('downscaled', 'is_gridded_obs', False),
    ('downscaled', 'model_type', 'GCM'),
    ('downscaled', 'ensemble_member', 'r1i1p1'),
    ('downscaled', 'cmor_filename',
     'tasmax_day_BCCAQ2_ACCESS1-0_historical+rcp45_r1i1p1_19600101-19911231.nc'),

    ('hydromodel_gcm', 'first_MiB_md5sum', '6544f8a39ba722e2085677525269c883'),
    ('hydromodel_gcm', 'md5', '36af1a6d4665fecf0d1a727a7cbdc6ef'),
    ('hydromodel_gcm', 'climatology_bounds_var_name', None),
    ('hydromodel_gcm', 'sampling_geometry', 'gridded'),
    ('hydromodel_gcm', 'is_multi_year', False),
    ('hydromodel_gcm', 'is_multi_year_mean', False),
    ('hydromodel_gcm', 'time_range', (0.0, 4382.0)),
    ('hydromodel_gcm', 'time_step_size', time_to_seconds(1, 'days')),
    ('hydromodel_gcm', 'time_resolution', 'daily'),
    ('hydromodel_gcm', 'is_unprocessed_gcm_output', False),
    ('hydromodel_gcm', 'is_downscaled_output', False),
    ('hydromodel_gcm', 'is_hydromodel_output', True),
    ('hydromodel_gcm', 'is_hydromodel_dgcm_output', True),
    # ('hydromodel_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('hydromodel_gcm', 'is_streamflow_model_output', False),
    ('hydromodel_gcm', 'is_streamflow_model_dgcm_output', False),
    ('hydromodel_gcm', 'is_streamflow_model_iobs_output', False),
    ('hydromodel_gcm', 'is_climdex_output', False),
    ('hydromodel_gcm', 'is_climdex_ds_gcm_output', False),
    ('hydromodel_gcm', 'is_gridded_obs', False),
    ('hydromodel_gcm', 'model_type', 'GCM'),
    ('hydromodel_gcm', 'ensemble_member', 'r1i1p1'),
    ('hydromodel_gcm', 'cmor_filename',
     'BASEFLOW+EVAP+GLAC_AREA_BAND+GLAC_MBAL_BAND+RUNOFF+SWE_BAND_day_VICGL+'
     'RGM+HydroCon_ACCESS1-0_historical+rcp45_r1i1p1_19840101-19951231.nc'),

    # Note: The following properties are not meaningful for a climatological
    # output file and so are not tested:
    #   time_range
    #   time_step_size
    ('mClim_gcm', 'first_MiB_md5sum', '411cae3298be3ba38588fceba0992eb7'),
    ('mClim_gcm', 'md5', '411cae3298be3ba38588fceba0992eb7'),
    ('mClim_gcm', 'climatology_bounds_var_name', 'climatology_bnds'),
    ('mClim_gcm', 'sampling_geometry', 'gridded'),
    ('mClim_gcm', 'is_multi_year', True),
    ('mClim_gcm', 'is_multi_year_mean', True),
    ('mClim_gcm', 'time_resolution', 'monthly'),
    # actually so, though the term 'unprocessed' here is misleading
    ('mClim_gcm', 'is_unprocessed_gcm_output', True),
    ('mClim_gcm', 'is_downscaled_output', False),
    ('mClim_gcm', 'is_hydromodel_output', False),
    ('mClim_gcm', 'is_hydromodel_dgcm_output', False),
    # ('mClim_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('mClim_gcm', 'is_streamflow_model_output', False),
    ('mClim_gcm', 'is_streamflow_model_dgcm_output', False),
    ('mClim_gcm', 'is_streamflow_model_iobs_output', False),
    ('mClim_gcm', 'is_climdex_output', False),
    ('mClim_gcm', 'is_climdex_ds_gcm_output', False),
    ('mClim_gcm', 'is_gridded_obs', False),
    ('mClim_gcm', 'model_type', 'GCM'),
    ('mClim_gcm', 'cmor_filename',
     'tasmax_mClim_BNU-ESM_historical_r1i1p1_19650101-19701231.nc'),

    ('sClim_gcm', 'first_MiB_md5sum', 'ecd2a0a28ffc12cc795d4e6b623543b6'),
    ('sClim_gcm', 'md5', 'ecd2a0a28ffc12cc795d4e6b623543b6'),
    ('sClim_gcm', 'climatology_bounds_var_name', 'climatology_bnds'),
    ('sClim_gcm', 'sampling_geometry', 'gridded'),
    ('sClim_gcm', 'is_multi_year', True),
    ('sClim_gcm', 'is_multi_year_mean', True),
    ('sClim_gcm', 'time_resolution', 'seasonal'),
    # actually so, though the term 'unprocessed' here is misleading
    ('sClim_gcm', 'is_unprocessed_gcm_output', True),
    ('sClim_gcm', 'is_downscaled_output', False),
    ('sClim_gcm', 'is_hydromodel_output', False),
    ('sClim_gcm', 'is_hydromodel_dgcm_output', False),
    # ('sClim_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('sClim_gcm', 'is_streamflow_model_output', False),
    ('sClim_gcm', 'is_streamflow_model_dgcm_output', False),
    ('sClim_gcm', 'is_streamflow_model_iobs_output', False),
    ('sClim_gcm', 'is_climdex_output', False),
    ('sClim_gcm', 'is_climdex_ds_gcm_output', False),
    ('sClim_gcm', 'is_gridded_obs', False),
    ('sClim_gcm', 'model_type', 'GCM'),
    ('sClim_gcm', 'cmor_filename',
     'tasmax_sClim_BNU-ESM_historical_r1i1p1_19650101-19701231.nc'),

    ('aClim_gcm', 'first_MiB_md5sum', 'b002ec3839db4daffdad335ad0d31563'),
    ('aClim_gcm', 'md5', 'b002ec3839db4daffdad335ad0d31563'),
    ('aClim_gcm', 'climatology_bounds_var_name', 'climatology_bnds'),
    ('aClim_gcm', 'sampling_geometry', 'gridded'),
    ('aClim_gcm', 'is_multi_year', True),
    ('aClim_gcm', 'is_multi_year_mean', True),
    ('aClim_gcm', 'time_resolution', 'yearly'),
    # actually so, though the term 'unprocessed' here is misleading
    ('aClim_gcm', 'is_unprocessed_gcm_output', True),
    ('aClim_gcm', 'is_downscaled_output', False),
    ('aClim_gcm', 'is_hydromodel_output', False),
    ('aClim_gcm', 'is_hydromodel_dgcm_output', False),
    # ('aClim_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('aClim_gcm', 'is_streamflow_model_output', False),
    ('aClim_gcm', 'is_streamflow_model_dgcm_output', False),
    ('aClim_gcm', 'is_streamflow_model_iobs_output', False),
    ('aClim_gcm', 'is_climdex_output', False),
    ('aClim_gcm', 'is_climdex_ds_gcm_output', False),
    ('aClim_gcm', 'is_gridded_obs', False),
    ('aClim_gcm', 'model_type', 'GCM'),
    ('aClim_gcm', 'cmor_filename',
     'tasmax_aClim_BNU-ESM_historical_r1i1p1_19650101-19701231.nc'),

    ('climdex_ds_gcm', 'first_MiB_md5sum', '5cbe8412f19599f893ba28062e0d7a9b'),
    ('climdex_ds_gcm', 'md5', '5cbe8412f19599f893ba28062e0d7a9b'),
    ('climdex_ds_gcm', 'climatology_bounds_var_name', None),
    ('climdex_ds_gcm', 'sampling_geometry', 'gridded'),
    ('climdex_ds_gcm', 'is_multi_year', False),
    ('climdex_ds_gcm', 'is_multi_year_mean', False),
    ('climdex_ds_gcm', 'time_range', (182.0, 54969.0)),
    ('climdex_ds_gcm', 'time_step_size', time_to_seconds(365, 'days')),
    ('climdex_ds_gcm', 'time_resolution', 'yearly'),
    ('climdex_ds_gcm', 'is_unprocessed_gcm_output', False),
    ('climdex_ds_gcm', 'is_downscaled_output', False),
    ('climdex_ds_gcm', 'is_hydromodel_output', False),
    ('climdex_ds_gcm', 'is_hydromodel_dgcm_output', False),
    # ('climdex_ds_gcm', 'is_hydromodel_iobs_output', False), # TODO
    ('climdex_ds_gcm', 'is_streamflow_model_output', False),
    ('climdex_ds_gcm', 'is_streamflow_model_dgcm_output', False),
    ('climdex_ds_gcm', 'is_streamflow_model_iobs_output', False),
    ('climdex_ds_gcm', 'is_climdex_output', True),
    ('climdex_ds_gcm', 'is_climdex_ds_gcm_output', True),
    ('climdex_ds_gcm', 'is_gridded_obs', False),
    ('climdex_ds_gcm', 'model_type', 'GCM'),
    ('climdex_ds_gcm', 'ensemble_member', 'r1i1p1'),
    ('climdex_ds_gcm', 'cmor_filename',
     'altcddETCCDI_yr_BCCAQ_ACCESS1-0_historical+rcp85_'
     'r1i1p1_19500702-21000702.nc'),

    ('gridded_obs', 'first_MiB_md5sum', '6e4b0f8968a18ffa917e34b68a3e5636'),
    ('gridded_obs', 'md5', '6e4b0f8968a18ffa917e34b68a3e5636'),
    ('gridded_obs', 'climatology_bounds_var_name', None),
    ('gridded_obs', 'sampling_geometry', 'gridded'),
    ('gridded_obs', 'is_multi_year', False),
    ('gridded_obs', 'is_multi_year_mean', False),
    ('gridded_obs', 'time_range', (0.0, 3.0)),
    ('gridded_obs', 'time_step_size', time_to_seconds(1, 'days')),
    ('gridded_obs', 'time_resolution', 'daily'),
    ('gridded_obs', 'is_unprocessed_gcm_output', False),
    ('gridded_obs', 'is_downscaled_output', False),
    ('gridded_obs', 'is_hydromodel_output', False),
    ('gridded_obs', 'is_hydromodel_dgcm_output', False),
    # ('gridded_obs', 'is_hydromodel_iobs_output', False), # TODO
    ('gridded_obs', 'is_streamflow_model_output', False),
    ('gridded_obs', 'is_streamflow_model_dgcm_output', False),
    ('gridded_obs', 'is_streamflow_model_iobs_output', False),
    ('gridded_obs', 'is_climdex_output', False),
    ('gridded_obs', 'is_climdex_ds_gcm_output', False),
    ('gridded_obs', 'is_gridded_obs', True),
    ('gridded_obs', 'cmor_filename',
     'pr_day_SYMAP_BC_v1_historical_19500101-19500104.nc'),

     ('gridded_mClimSD_obs', 'first_MiB_md5sum', '7eb975dfd17845621123400dbb6d0e5b'),
     ('gridded_mClimSD_obs', 'md5', '7eb975dfd17845621123400dbb6d0e5b'),
     ('gridded_mClimSD_obs', 'climatology_bounds_var_name', 'climatology_bnds'),
     ('gridded_mClimSD_obs', 'sampling_geometry', 'gridded'),
     ('gridded_mClimSD_obs', 'is_multi_year', True),
     ('gridded_mClimSD_obs', 'is_multi_year_mean', True),
     ('gridded_mClimSD_obs', 'time_range', (13163.0, 13253.0)),
     ('gridded_mClimSD_obs', 'time_step_size', time_to_seconds(31, 'days')),
     ('gridded_mClimSD_obs', 'time_resolution', 'seasonal'),
     ('gridded_mClimSD_obs', 'is_unprocessed_gcm_output', False),
     ('gridded_mClimSD_obs', 'is_downscaled_output', False),
     ('gridded_mClimSD_obs', 'is_hydromodel_output', False),
     ('gridded_mClimSD_obs', 'is_hydromodel_dgcm_output', False),
     # ('gridded_mClimSD_obs', 'is_hydromodel_iobs_output', False), # TODO
     ('gridded_mClimSD_obs', 'is_streamflow_model_output', False),
     ('gridded_mClimSD_obs', 'is_streamflow_model_dgcm_output', False),
     ('gridded_mClimSD_obs', 'is_streamflow_model_iobs_output', False),
     ('gridded_mClimSD_obs', 'is_climdex_output', False),
     ('gridded_mClimSD_obs', 'is_climdex_ds_gcm_output', False),
     ('gridded_mClimSD_obs', 'is_gridded_obs', True),
     ('gridded_mClimSD_obs', 'cmor_filename',
      'pr_mClimSD_anusplin_historical_19710201-20000531.nc'),

    ('streamflow', 'first_MiB_md5sum', 'e399c143415d13b7eab6809daa9cfc2f'),
    ('streamflow', 'md5', 'e399c143415d13b7eab6809daa9cfc2f'),
    ('streamflow', 'climatology_bounds_var_name', None),
    ('streamflow', 'sampling_geometry', 'dsg.timeSeries'),
    ('streamflow', 'is_multi_year', False),
    ('streamflow', 'is_multi_year_mean', False),
    ('streamflow', 'time_range', (710034.5, 710049.5)),
    ('streamflow', 'time_step_size', time_to_seconds(1, 'days')),
    ('streamflow', 'time_resolution', 'daily'),
    ('streamflow', 'is_unprocessed_gcm_output', False),
    ('streamflow', 'is_downscaled_output', False),
    ('streamflow', 'is_hydromodel_output', False),
    ('streamflow', 'is_hydromodel_dgcm_output', False),
    # ('streamflow', 'is_hydromodel_iobs_output', False), # TODO
    ('streamflow', 'is_streamflow_model_output', True),
    ('streamflow', 'is_streamflow_model_dgcm_output', True),
    ('streamflow', 'is_streamflow_model_iobs_output', False),
    ('streamflow', 'is_climdex_output', False),
    ('streamflow', 'is_climdex_ds_gcm_output', False),
    ('streamflow', 'is_gridded_obs', False),
    ('streamflow', 'model_type', 'GCM'),
    ('streamflow', 'ensemble_member', 'r1i2p3'),
    ('streamflow', 'cmor_filename',
     'streamflow_day_model_exp_r1i2p3_19450102-19450117.nc'),

], indirect=['tiny_dataset'])
def test_simple_property(tiny_dataset, prop, expected):
    assert getattr(tiny_dataset, prop) == expected


# Setup for testing ``get_climatology_bounds_var_name`` and
# ``get_is_multi_year_mean``, which depends on
# ``get_climatology_bounds_var_name``.
#
# These cases are shared between the two methods, so each case includes
# expected output for both.
# Each test function ignores the other's expected output parameter.
# Each tuple correspnods to the following arguments:
#   ``(file_spec, strict,
#      expected_climatology_bounds_var_name, expected_is_multi_year_mean)``
#
# The alert reader will note that in all current test cases,
#   ``expected_is_multi_year_mean == bool(expected_climatology_bounds_var_name)``
# However, this is not necessarily so, and at least one potential refinement
# to ``is_multi_year_mean`` will change this relationship. Hence the explicit
# distinction between the two values.

likely_climo_bounds_var_names = ['climatology_bounds', 'climatology_bnds',
                                 'climo_bounds', 'climo_bnds']
likely_time_bounds_var_names = ['time_bounds', 'time_bnds']

# Use a non-"suspcicious" number of time values to prevent false positives
# from that heuristic.
narrow_time_bounds = [[0, 10], [10, 20]]
narrow_time_values = [5, 15]

wide_time_bounds = [[0, 3650], [30, 3680]]
wide_time_values = [1825, 1855]

# Starred components in lists would make this list construction much tidier,
# but Py <3.5 doesn't support that. Ppptththhtpptth.
climo_bounds_var_test_cases = (
    # Without time variable
    [
        ({}, strict, None, False)
        for strict in [False, True]
    ] +

    # All subsequent tests with time variable ...

    # Without time:climatology or time:bounds attr; without bounds variable
    [
        (spec(tb_attr=None, tb_var_name=None, tb_values=None, t_values=None),
         strict, None, False)
        for strict in [False, True]
    ] +

    # With time:climatology attr; without climo bounds variable
    # Note: does not check existence of variable. Is this right?
    [
        (spec(tb_attr={'climatology': 'foo'}, tb_var_name=None,
              tb_values=None, t_values=None),
         strict, 'foo', True)
        for strict in [False, True]
    ] +

    # With time:climatology attr; with climo bounds variable
    # Use non-canonical bounds var name, to prevent false success with likely-name heuristic
    [
        (spec(tb_attr={'climatology': 'foo'}, tb_var_name='foo',
              tb_values=None, t_values=None),
         False, 'foo', True)
        for strict in [False, True]
    ] +

    # Without time:climatology or time:bounds attr; with likely named climo bounds variable
    # Note: no checking of bounds variable contents. Is this right?
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=None, t_values=None),
         False, name, True)
        for name in likely_climo_bounds_var_names
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=name, tb_values=None, t_values=None),
         True, None, False)
        for name in likely_climo_bounds_var_names
    ] +

    # Without time:climatology or time:bounds attr; without likely named climo bounds variable
    [
        (spec(tb_attr=None, tb_var_name='foo', tb_values=None, t_values=None),
         strict, None, False)
        for strict in [False, True]
    ] +

    # With time:bounds attr; without corresponding variable
    [
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name=None,
              tb_values=None, t_values=None),
         strict, None, False)
        for strict in [False, True]
    ] +

    # With time:bounds attr; with time bounds too narrow (< 2 yr)
    [
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo',
              tb_values=narrow_time_bounds, t_values=narrow_time_values),
         strict, None, False)
        for strict in [False, True]
    ] +

    # With time:bounds attr; with time bounds broad enough (> 2 yr)
    [
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo',
              tb_values=wide_time_bounds, t_values=wide_time_values),
         False, 'foo', True),
        (spec(tb_attr={'bounds': 'foo'}, tb_var_name='foo',
              tb_values=wide_time_bounds, t_values=wide_time_values),
         True, None, False),
    ] +

    # Without time:climatology or time:bounds attr; with likely named time bounds var;
    # with time bounds too narrow (10 d < 2 yr)
    [
        (spec(tb_attr=None, tb_var_name=name,
              tb_values=narrow_time_bounds, t_values=narrow_time_values),
         strict, None, False)
        for name in likely_time_bounds_var_names
        for strict in [False, True]
    ] +

    # Without time:climatology or time:bounds attr; with likely named time bounds var;
    # with time bounds broad enough (3650 d > 2 yr)
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=name,
              tb_values=wide_time_bounds, t_values=wide_time_values),
         False, name, True)
        for name in likely_time_bounds_var_names
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=name,
              tb_values=wide_time_bounds, t_values=wide_time_values),
         True, None, False)
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
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values),
         False, None, True)
        for t_values in suspicious_time_values
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values), True, None, False)
        for t_values in suspicious_time_values
    ] +
    [
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values), strict,
         None, False)
        for t_values in non_suspicious_time_values
        for strict in [False, True]
    ]
    ,
    indirect=['fake_nc_dataset']
)
def test_is_multi_year(fake_nc_dataset, strict, _, is_mym):
    cf = CFDataset(fake_nc_dataset, strict_metadata=strict)
    assert cf.is_multi_year == is_mym


# Test against some actual files (from climate-explorer-backend tests).
# This is a supplement to the much more thorough but contrived tests with the
# faked nc datasets above.
@mark.parametrize('dataset, is_mym', [
    ('CanESM2-rcp85-tasmax-r1i1p1-2010-2039', True),
    ('prism_pr_small', True),
], indirect=['dataset'])
def test_is_multi_year_against_nonstandard_datasets(dataset, is_mym):
    assert dataset.is_multi_year == is_mym


@mark.parametrize(
    'fake_nc_dataset, strict, _, is_mym',
    # All the cases depending on climo bounds
    climo_bounds_var_test_cases +

    # Without time:climatology or time:bounds attrs; without variable with likely name for climo bounds;
    # without variable with likely name for time bounds and likely contents;
    # with time variable with suspicious length and contents
    [
        # Non-strict
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values),
         False, None, True)
        for t_values in suspicious_time_values
    ] +
    [
        # Strict
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values), True, None, False)
        for t_values in suspicious_time_values
    ] +
    [
        (spec(tb_attr=None, tb_var_name=None,
              tb_values=None, t_values=t_values), strict,
         None, False)
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


# All test datasets are known to have time dimension units of 'days since ...',
# which means we can use constants for time values (no need to convert units).

epsilon = 2e-5  # about 1 second, in days
min_month_length = 28  # days
max_month_length = 31  # days

@mark.parametrize('tiny_dataset, exp_start, exp_end', [
    ('gcm', 5475.0, 9126.0),
    # ('downscaled', 715509.0, 727197.0),  # downscaled files lack time bounds
    # ('hydromodel_gcm', 0.0, 4382.0),     # hydromodel files lack time bounds
    ('mClim_gcm', 5475.0, 7665.0),
    ('sClim_gcm', 5475.0, 7665.0),
    ('aClim_gcm', 5475.0, 7665.0),
    ('climdex_ds_gcm', 0.0, 55151.0),
], indirect=['tiny_dataset'])
@mark.parametrize('nominal', [False, True])
def test_time_bounds_extrema(tiny_dataset, nominal, exp_start, exp_end):
    extrema_open = tiny_dataset.time_bounds_extrema(
        nominal=nominal, closed=False)
    extrema_closed = tiny_dataset.time_bounds_extrema(
        nominal=nominal, closed=True)

    # Check open-closed values, relative to each other
    assert extrema_open[0] == extrema_closed[0]
    assert extrema_open[1] - epsilon <= extrema_closed[1] < extrema_open[1]

    # Check nominal values using absolute values of half-open interval
    if not nominal and tiny_dataset.is_multi_year_mean and \
        tiny_dataset.time_resolution == 'seasonal':
        delta_max = max_month_length
        delta_min = min_month_length
    else:
        delta_max = delta_min = 0
    assert exp_start - delta_max <= extrema_open[0] <= exp_start - delta_min
    assert exp_end - delta_max <= extrema_open[1] <= exp_end - delta_min


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

    ('mClim_gcm', 'institute_id', 'BNU'),
    ('mClim_gcm', 'model_id', 'BNU-ESM'),
    ('mClim_gcm', 'experiment_id', 'historical'),
    ('mClim_gcm', 'initialization_method', 1),
    ('mClim_gcm', 'physics_version', 1),
    ('mClim_gcm', 'realization', 1),

    ('climdex_ds_gcm', 'institute_id', 'CSIRO-BOM'),
    ('climdex_ds_gcm', 'model_id', 'ACCESS1-0'),
    ('climdex_ds_gcm', 'experiment_id', 'historical, rcp85'),
    ('climdex_ds_gcm', 'initialization_method', 1),
    ('climdex_ds_gcm', 'physics_version', 1),
    ('climdex_ds_gcm', 'realization', 1),
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

    ('mClim_gcm', 'project', 'CMIP5'),
    ('mClim_gcm', 'institution', 'BNU'),
    ('mClim_gcm', 'model', 'BNU-ESM'),
    ('mClim_gcm', 'emissions', 'historical'),
    ('mClim_gcm', 'experiment', 'historical'),
    ('mClim_gcm', 'run', 'r1i1p1'),
    ('mClim_gcm', 'ensemble_member', 'r1i1p1'),

    ('climdex_ds_gcm', 'project', 'CMIP5'),
    ('climdex_ds_gcm', 'institution', 'PCIC'),
    ('climdex_ds_gcm', 'model', 'ACCESS1-0'),
    ('climdex_ds_gcm', 'emissions', 'historical, rcp85'),
    ('climdex_ds_gcm', 'experiment', 'historical, rcp85'),
    ('climdex_ds_gcm', 'run', 'r1i1p1'),
    ('climdex_ds_gcm', 'ensemble_member', 'r1i1p1'),

    ('gridded_obs', 'project', 'other'),
    ('gridded_obs', 'institution', 'PCIC'),
    ('gridded_obs', 'model', 'SYMAP_BC_v1'),
    ('gridded_obs', 'emissions', 'historical'),
    ('gridded_obs', 'run', 'nominal'),
    ('gridded_obs', 'institute', 'PCIC'),
    ('gridded_obs', 'experiment', 'historical'),
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


@mark.slow
@mark.parametrize('tiny_dataset, var_name, expected', [
    ('gcm', 'time', (5475.5, 9125.5)),
    ('gcm', 'lon', (264.375, 272.8125)),
    ('gcm', 'lat', (65.5776, 73.9475)),
    ('gcm', 'tasmax', (220.68445, 304.13501)),
], indirect=['tiny_dataset'])
def test_variable_range(tiny_dataset, var_name, expected):
    assert tiny_dataset.var_range(var_name, chunksize=2) == approx(expected)


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'time', 'lon', 'lat', 'nb2'}),
    ('downscaled', {'time', 'lon', 'lat'}),
    ('hydromodel_gcm', {'time', 'lon', 'lat', 'depth'}),
    ('mClim_gcm', {'time', 'lon', 'lat', 'bnds'}),
    ('climdex_ds_gcm', {'time', 'lon', 'lat', 'bnds'}),
], indirect=['tiny_dataset'])
def test_dim_names(tiny_dataset, expected):
    assert set(tiny_dataset.dim_names()) == expected


# Tests for some dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'mClim_gcm',
    'climdex_ds_gcm',
    'gridded_obs',
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
    ('mClim_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('climdex_ds_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('gridded_obs', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
], indirect=['tiny_dataset'])
def test_dim_axes_from_names2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes_from_names() == expected


# Tests for some dimensions that are the same in all datasets.
@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'mClim_gcm',
    'climdex_ds_gcm',
    'gridded_obs',
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
    ('mClim_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('climdex_ds_gcm', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
    ('gridded_obs', {'time': 'T', 'lon': 'X', 'lat': 'Y'}),
], indirect=['tiny_dataset'])
def test_dim_axes2(tiny_dataset, expected):
    assert tiny_dataset.dim_axes() == expected


# Tests for all dimensions - may differ between datasets.
@mark.parametrize('tiny_dataset, expected', [
    ('gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('downscaled', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('hydromodel_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat', 'Z': 'depth'}),
    ('mClim_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('climdex_ds_gcm', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
    ('gridded_obs', {'T': 'time', 'X': 'lon', 'Y': 'lat'}),
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
    ('hydromodel_gcm', set(), {'RUNOFF', 'BASEFLOW', 'EVAP', 'GLAC_MBAL_BAND',
                               'GLAC_AREA_BAND', 'SWE_BAND'}),
    ('mClim_gcm', set(), {'tasmax'}),
    ('climdex_ds_gcm', set(), {'altcddETCCDI'}),
    ('gridded_obs', set(), {'pr'}),
    ('streamflow', set(), {'streamflow'})
], indirect=['tiny_dataset'])
def test_dependent_varnames(tiny_dataset, dim_names, expected):
    assert set(tiny_dataset.dependent_varnames(dim_names=dim_names)) == expected


@mark.parametrize('tiny_dataset, var_name', [
    ('streamflow', 'streamflow'),
], indirect=['tiny_dataset'])
@mark.parametrize('method, extra_args, instance_var_name', [
    ('instance_dim', tuple(), 'outlets'),
    ('id_instance_var', tuple(), 'outlet_name'),
    ('spatial_instance_var', ('X',), 'lon'),
    ('spatial_instance_var', ('Y',), 'lat'),
])
def test_dsg_dataset_vars(
        tiny_dataset, var_name, method, extra_args, instance_var_name):
    assert getattr(tiny_dataset, method)(var_name, *extra_args).name == \
           instance_var_name


@mark.parametrize('tiny_dataset', [
    'gcm',
    'downscaled',
    'hydromodel_gcm',
    'mClim_gcm',
    'climdex_ds_gcm',
    'gridded_obs',
], indirect=True)
@mark.parametrize('property, standard_name', [
    ('time_var', 'time'),
    ('lon_var', 'longitude'),
    ('lat_var', 'latitude'),
])
def test_gridded_dataset_vars(tiny_dataset, property, standard_name):
    assert getattr(tiny_dataset, property).standard_name == standard_name


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 715509.5, 727196.5),
    ('hydromodel_gcm', 0.0, 4382.0),
    ('mClim_gcm', 6585.0, 6919.0),
    ('sClim_gcm', 6584.0, 6859.0),
    ('aClim_gcm', 6752.0, 6752.0),
    ('climdex_ds_gcm', 182.0, 54969.0),
    ('gridded_obs', 0.0, 3.0),
], indirect=['tiny_dataset'])
def test_time_var_values(tiny_dataset, start_time, end_time):
    assert tiny_dataset.time_var_values[0] == start_time
    assert tiny_dataset.time_var_values[-1] == end_time


@mark.parametrize('tiny_dataset, start_time, end_time', [
    ('gcm', 5475.5, 9125.5),
    ('downscaled', 715509.5, 727196.5),
    ('hydromodel_gcm', 0.0, 4382.0),
    ('mClim_gcm', 6585.0, 6919.0),
    ('sClim_gcm', 6584.0, 6859.0),
    ('aClim_gcm', 6752.0, 6752.0),
    ('climdex_ds_gcm', 182.0, 54969.0),
    ('gridded_obs', 0.0, 3.0),
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


# TODO: Make this a fixture (indirect)?
def proj4_string_nc_spec(crs_attrs):
    return {
        'dimensions': {
            'time': 2,
        },
        'variables': {
            'var': {
                 'dimensions': ('time',),
                 'datatype': 'f4',
                 'attrs': {
                     'grid_mapping': 'crs',
                 },
            },
            'crs': {
                'dimensions': (),
                'datatype': 'c',
                'attrs': crs_attrs,
            }
        }
    }


proj4_string_no_CRS_nc_spec = {
    'dimensions': {'time': 2, },
    'variables': {
        'var': {
            'dimensions': ('time',),
            'datatype': 'f4',
        },
    }
}


@mark.parametrize('fake_nc_dataset, options, expected_proj4_string', [
    # Test each of the supported projections
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'polar_stereographic',
            'standard_parallel': 11,
            'latitude_of_projection_origin': 12,
            'straight_vertical_longitude_from_pole': 13,
            'false_easting': 14,
            'false_northing': 15,
        }),
        {},
        '+proj=stere +ellps=WGS84 +lat_ts=11 +lat_0=12 '
        '+lon_0=13 +x_0=14 +y_0=15 +k_0=1'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'rotated_latitude_longitude',
            'north_pole_latitude': 40,
            'north_pole_longitude': 50,
        }),
        {},
        '+proj=ob_tran +o_proj=longlat +lon_0=-130.0 +o_lat_p=40 '
        '+a=1 +to_meter=0.0174532925199 +no_defs'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'rotated_latitude_longitude',
            'grid_north_pole_latitude': 40,
            'grid_north_pole_longitude': 50,
        }),
        {},
        '+proj=ob_tran +o_proj=longlat +lon_0=-130.0 +o_lat_p=40 '
        '+a=1 +to_meter=0.0174532925199 +no_defs'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'lambert_conformal_conic',
            'standard_parallel': 11,
            'latitude_of_projection_origin': 12,
            'longitude_of_central_meridian': 13,
            'false_easting': 14,
            'false_northing': 15,
        }),
        {},
        # TODO: Is this a legitimate definition string ('+lat2=')?
        '+proj=lcc +ellps=WGS84 +lat_0=12 +lat_1=11 +lat_2= '
        '+lon_0=13 +x_0=14 +y_0=15'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'lambert_conformal_conic',
            'standard_parallel': (11.1, 11.2),
            'latitude_of_projection_origin': 12,
            'longitude_of_central_meridian': 13,
            'false_easting': 14,
            'false_northing': 15,
        }),
        {},
        '+proj=lcc +ellps=WGS84 +lat_0=12 +lat_1=11.1 +lat_2=11.2 '
        '+lon_0=13 +x_0=14 +y_0=15'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'transverse_mercator',
            'latitude_of_projection_origin': 12,
            'longitude_of_central_meridian': 13,
            'false_easting': 14,
            'false_northing': 15,
            'scale_factor_at_central_meridian': 16,
        }),
        {},
        '+proj=tmerc +ellps=WGS84 +lat_0=12 +lon_0=13 +x_0=14 +y_0=15 +k_0=16'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'latitude_longitude',
            'semi_major_axis': 10,
            'semi_minor_axis': 11,
            'inverse_flattening': 12,
            'longitude_of_prime_meridian': 13,
        }),
        {},
        '+proj=longlat +a=10 +rf=12 +b=11 +lon_0=13'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'latitude_longitude',
            'semi_major_axis': 10,
            'longitude_of_prime_meridian': 13,
        }),
        {},
        '+proj=longlat +a=10 +lon_0=13'
    ),
    (
        proj4_string_no_CRS_nc_spec,
        {'default': 'foo'},
        'foo'
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'polar_stereographic',
            'standard_parallel': 11,
            'latitude_of_projection_origin': 12,
            'straight_vertical_longitude_from_pole': 13,
            'false_easting': 14,
            'false_northing': 15,
        }),
        {'ellps': 'foo'},
        '+proj=stere +ellps=foo +lat_ts=11 +lat_0=12 '
        '+lon_0=13 +x_0=14 +y_0=15 +k_0=1'
    ),
], indirect=['fake_nc_dataset'])
def test_proj4_string(fake_nc_dataset, options, expected_proj4_string):
    cf = CFDataset(fake_nc_dataset)
    proj4_string = cf.proj4_string('var', **options)
    assert set(proj4_string.split()) == set(expected_proj4_string.split())


# @mark.parametrize('fake_nc_dataset, options, expected', [
#     (proj4_string_no_CRS_nc_spec, {'default': 'foo'}),
# ], indirect=['fake_nc_dataset'])
# def test_proj4_string_options(fake_nc_dataset, options, expected):
#     cf = CFDataset(fake_nc_dataset)
#     proj4_string = cf.proj4_string('var', **options)
#     assert proj4_string == expected


@mark.parametrize('fake_nc_dataset, exception, exception_check', [
    # No CRS info (missing ``grid_mapping`` attribute on var)
    (
        proj4_string_no_CRS_nc_spec,
        CFAttributeError,
        lambda excinfo:
            'No coordinate reference system metadata found' in str(excinfo.value)
    ),
    # Missing ``grid_mapping_name`` attribute on CRS variable
    (
        proj4_string_nc_spec({}),
        CFAttributeError,
        lambda excinfo: (
            'grid_mapping_name' in str(excinfo.value) and
            'no such attribute' in str(excinfo.value)
        )
    ),
    # Bad projection name (``grid_mapping_name``)
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'foo',
        }),
        CFValueError,
        lambda excinfo: (
            'grid_mapping_name' in str(excinfo.value) and
            'not a recognized value' in str(excinfo.value)
        )
    ),
    # Missing projection parameter attributes
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'polar_stereographic',
            'standard_parallel': 11,
        }),
        CFAttributeError,
        lambda excinfo: 'no such attribute' in str(excinfo.value)
    ),
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'rotated_latitude_longitude',
            'north_pole_latitude': 11,
        }),
        CFAttributeError,
        lambda excinfo: 'no such attribute' in str(excinfo.value)
    ),
    # Invalid number of lats for Lambert conformal conic
    (
        proj4_string_nc_spec({
            'grid_mapping_name': 'lambert_conformal_conic',
            'standard_parallel': (11.1, 11.2, 11.3),
            'latitude_of_projection_origin': 12,
            'longitude_of_central_meridian': 13,
            'false_easting': 14,
            'false_northing': 15,
        }),
        CFValueError,
        lambda excinfo: (
            'standard_parallel' in str(excinfo.value) and
            'length exactly 2' in str(excinfo.value)
        )
    ),
], indirect=['fake_nc_dataset'])
def test_proj4_string_raises(fake_nc_dataset, exception, exception_check):
    cf = CFDataset(fake_nc_dataset)
    with raises(exception) as excinfo:
        proj4_string = cf.proj4_string('var')
    assert exception_check(excinfo)


@mark.parametrize('tiny_dataset, expected', [
    ('gcm', set()),
    ('downscaled', {'6190'}),
    ('hydromodel_gcm', set()),
    ('seasonal', {'2080'})
    # Not relevant for climo data sets
], indirect=['tiny_dataset'])
def test_climo_periods(tiny_dataset, expected):
    assert set(tiny_dataset.climo_periods.keys()) == expected


class TestIndirectValues:
    """Test the indirect value feature of CFDataset.
    See CFDataset class docstring for explanation of indirect values.
    To test, we use an otherwise empty CFDataset file populated with
    properties (attributes) for testing.
    For its contents, see conftest.py.
    """

    def test_is_indirected(self, indir_dataset):
        assert not indir_dataset.is_indirected('one')
        assert indir_dataset.is_indirected('uno')
        assert indir_dataset.is_indirected('un')
        # even if the indirection is circular
        assert indir_dataset.is_indirected('foo')
        # even if the indirected property does not exist
        assert indir_dataset.is_indirected('baz')

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
