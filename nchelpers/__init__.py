"""Module containing helper functions and, centrally, a class that extends
``netcdf4.Dataset`` with properties and methods useful for PCIC applications
(and more generally).

NOTE TO DEVELOPERS:

``netcdf4`` somehow catches and rethrows **all** ``AttributeError``s,
stripped of their message. This is (a) confusing, and (b) makes it necessary
to substitute an exception not derived from AttributeError if you want to
get a message out to the user. This package defines custom exceptions
for this purpose.
"""

import os.path
from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib
import re
import collections

from cached_property import cached_property
import numpy as np
import six

from netCDF4 import Dataset, Variable, num2date, date2num
from nchelpers.date_utils import \
    time_scale, resolution_standard_name, \
    time_to_seconds, seconds_to_time, \
    d2ss, to_datetime, truncate_to_resolution
from nchelpers.decorators import prevent_infinite_recursion
from nchelpers.exceptions import CFAttributeError, CFValueError
from nchelpers.iteration import opt_chunk_shape, chunks

def getattr_cf_error(object, attr_name):
    """
    Get an attribute from a (nominally ``NetCDF4.Dataset`` or ``.Variable``)
    object, and raise an informative CFAttributeError if no such
    attribute exists.
    """
    try:
        return getattr(object, attr_name)
    except AttributeError:
        if isinstance(object, Dataset):
            object_name = 'file'
        elif isinstance(object, Variable):
            object_name = 'variable {}'.format(object.name)
        else:
            object_name = 'object of type {}'.format(type(object))
        raise CFAttributeError(
            "Expected {} to have attribute '{}', but no such attribute exists"
                .format(object_name, attr_name)
        )

# Map of nchelpers time resolution strings to MIP table names, standard where
# possible. For an explanation of the content of this map, see the discussion
# in section titled "MIP table / table_id" in
# https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data
standard_tres_to_mip_table = {
    '1-minute': 'subhr',  # frequency std
    '2-minute': 'subhr',  # frequency std
    '5-minute': 'subhr',  # frequency std
    '15-minute': 'subhr',  # frequency std
    '30-minute': 'subhr',  # frequency std
    '1-hourly': '1hr',  # custom: neither a MIP table nor a freq standard term
    '3-hourly': '3hr',  # frequency std
    '6-hourly': '6hr',  # frequency std
    '12-hourly': '12hr',  # custom: neither a MIP table nor a freq standard term
    'daily': 'day',  # MIP table and frequency standard
    'monthly': 'mon',  # frequency std
    'yearly': 'yr',  # frequency std
    'fx': 'fx', # time-independent data
    'fixed': 'fx'
}


def _normalize180(x):
    """Normalize a longitude value to the range [-180, 180)."""
    return (x + 180.0) % 360.0 - 180.0


def _cmor_formatted_time_range(t_min, t_max, time_resolution='daily'):
    """Format a time range as string in YYYY[mm[dd]] format, min and max
    separated by a dash."""
    try:
        fmt = {
            'yearly': '%Y',
            'monthly': '%Y%m',
            'daily': '%Y%m%d'
        }[time_resolution]
    except KeyError:
        raise CFValueError(
            "Cannot format a time range with resolution '{}' "
            "(only yearly, monthly or daily)".format(time_resolution))
    return '{}-{}'.format(t_min.strftime(fmt), t_max.strftime(fmt))


def cmor_type_filename(extension='', **component_values):
    """Return a filename built from supplied component values, following the a
    CMOR-based filename standards in
    https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data

    Produces a CMOR standard filename if all and only required CMOR filename
    components are defined. Omits any components not in list of component names.
    Omits any component with a None value.

    Warning: This thing is no smarter than it has to be. Does not enforce
    required components or any rules other than order.
    """
    # Include these filename components in this order ...
    component_names = '''
        variable
        mip_table
        frequency
        downscaling_method
        hydromodel_method
        model
        experiment
        ensemble_member
        obs_dataset_id
        time_range
        geo_info
    '''.split()
    # ... if they are defined in component_values
    return '_'.join(component_values[cname] for cname in component_names
                    if component_values.get(cname, None) is not None) \
           + extension


def _replace_commas(s, sep='+'):
    """Return a string constructed by joining with `sep` the substrings of `s`
    delimited by commas and arbitrary spaces.

    :param s: (str) string to split on commas and join with sep
    :param sep: (str) separator string for join
    :return: see above
    """
    return re.sub(r'\s*,\s*', sep, s)


def _indirection_info(value):
    """Return (True, <property name>) iff ``value`` is a string that indirects
    to another property value.
    Otherwise return (False, None).
    See CFDataset docstring for explanation of indirect values.

    :param value: (str) literal value (uninterpreted under indirection rule)
        of a property
    :return: (tuple) (is_indirected, property_name) see above
    """
    if isinstance(value, six.string_types) and value[0] == '@':
        return True, value[1:]
    return False, None


def standard_climo_periods(calendar='standard'):
    """Returns a dict containing the start and end dates, under the specified
    calendar, of standard climatological periods, keyed by abbreviations for
    those periods, e.g., '6190' for 1961-1990.

    These periods begin Jan 1 and end Dec 31, which is a mismatch to
    hydrological years, which begin/end Oct 1 / Sep 30. Discussions with
    Markus Schnorbus confirm that for 30-year means, the difference in annual
    and season averages is negligible and therefore we do not have to allow
    for alternate begin and end dates. """
    standard_climo_years = {
        '6190': (1961, 1990),
        '7100': (1971, 2000),
        '8110': (1981, 2010),
        '2020': (2010, 2039),
        '2050': (2040, 2069),
        '2080': (2070, 2099)
    }
    end_day = 30 if calendar == '360_day' else 31
    return {k: (datetime(start_year, 1, 1), datetime(end_year, 12, end_day))
            for k, (start_year, end_year) in standard_climo_years.items()}


class CFDataset(Dataset):
    """Represents a CF (climate and forecast) dataset stored in a NetCDF file.

    Properties and methods on this class expose metadata that is expected to
    be found in such files, and values computed from that metadata.

    Indirect values
    ---------------

    Any property of a CFDataset object can be given an "indirect value,"
    which is a string of the form

        ``@<property name>``

    ``@`` signfies indirection
    ``<property name>`` is the name of any property of the object

    The value of a property with an indirect value is the value of the property
    named in the indirect value. If the property named in the indirect value
    does not exist, then the value of the property is just the unprocessed
    value of the original property.

    Example: Let cf be a CFDataset object. Then the following test passes::

        cf.alpha = 'hello'              # ordinary string value
        cf.beta = '@alpha'              # indirect value
        assert cf.beta == 'hello'       # indirection works
        cf.gamma = '@not_here'          # indirect to a non-existent property
        assert cf.gamma == '@not_here'  # and get back the unprocessed string


    Because indirection hides the uninterpreted value (e.g., '@alpha') of a
    property with an indirect value, this class also has the methods::

        is_indirected(name)
        get_direct_value(name)

    where ``name`` is the name of any property.

    Helper functions in modelmeta
    -----------------------------

    Some of this class replaces the functionality of helper functions defined
    in pacificclimate/modelmeta. The following list maps those functions to
    \properties/methods of this class.

    get_file_metadata -> metadata.<global attribute>
        - <global attribute> is the unified name for actual CF standard global
          attributes in the NetCDF file
        - doesn't include time metadata; use properties below instead
    ``create_unique_id`` -> ``unique_id``
    ``nc_get_dim_axes_from_names`` -> ``dim_axes_from_names``
    ``nc_get_dim_names`` -> ``dim_names``
    ``nc_get_dim_axes`` -> ``dim_axes``
    ``get_climatology_bounds_var_name`` -> ``climatology_bounds_var_name``
    ``is_multi_year_mean`` -> ``is_multi_year_mean``
    ``get_time_step_size`` -> ``time_step_size``
    ``get_time_resolution`` -> ``time_resolution``
    ``get_timeseries`` -> ``time_steps``
    ``get_time_range`` -> ``time_range``
    ``get_first_MiB_md5sum`` -> ``first_MiB_md5sum``
    ``get_important_varnames`` -> ``dependent_varnames``
    """

    def __init__(self, *args, **kwargs):
        """Class constructor.

        :param strict_metadata (bool): If True, metadata is interpreted
            strictly, i.e., it is expected to adhere to PCIC metadata standards
            and CF metadata standards.
            Otherwise, heuristics are applied when an attempt to read or
            interpret metadata according to standards fails.

        Regarding ``strict_metadata``, the precise meaning of 'heuristics are
        applied' depends on the property/method in question. The following
        properties/methods have both strict and non-strict behaviours:

        - ``climatology_bounds_var_name``
        - ``is_multi_year_mean``

        See docstrings for each prop/method for details of non-strict behaviour.

        NOTE: Any code that depends on these methods, including other
        properties and methods in this class, therefore also implicitly have
        both strict and non-strict behaviours.
        """
        super(CFDataset, self).__init__(*args, **kwargs)
        # Store options directly via dict to prevent them being treated as
        # Dataset attributes.
        # It's possible that it would be better to define ``__setattribute__``
        # with a special case for this attr name, complementary to
        # ``__getattribute__``.
        self.__dict__['_cf_dataset_options'] = {
            'strict_metadata': kwargs.get('strict_metadata', False)
        }

    ###########################################################################
    # Whole file descriptors

    def filepath(self, converter=None):
        """Return the filepath, optionally processed by a converter,
        either none (no conversion) or one of the ``os.path`` path
        transformation functions, ``abspath``, ``normpath``, or ``realpath``.
        """
        fp = super(CFDataset, self).filepath()
        converters = {
            None: lambda fp: fp,
            'abspath': os.path.abspath,
            'normpath': os.path.normpath,
            'realpath': os.path.realpath,
        }
        try:
            return converters[converter](fp)
        except:
            raise ValueError(
                "Expected convert to have value in {}, but got '{}'"
                    .format(converters.keys(), converter)
            )

    # noinspection PyPep8Naming
    @property
    def first_MiB_md5sum(self):
        """MD5 digest of first MiB of this file"""
        m = hashlib.md5()
        with open(self.filepath(), 'rb') as f:
            m.update(f.read(2**20))
        return m.hexdigest()

    @property
    def md5(self):
        """MD5 hex digest of entirety of this file.
        Parsimonious with memory. Adopted from
        https://stackoverflow.com/a/3431838
        """
        hash_md5 = hashlib.md5()
        with open(self.filepath(), 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    ###########################################################################
    # Attribute retrieval

    def is_indirected(self, name):
        """Return True iff the property named has an indirect value.
        See class docstring for explanation of indirect values.
        Does not handle `_cf_dataset_options`, but that doesn't matter.
        """
        return _indirection_info(self.get_direct_value(name))[0]

    def get_direct_value(self, name):
        """Return the value of the named property without indirection
        processing.
        See class docstring for explanation of indirect values.
        Does not handle `_cf_dataset_options`, but that doesn't matter.
        """
        return super(CFDataset, self).__getattribute__(name)

    @prevent_infinite_recursion
    def __getattribute__(self, name):
        """Handle special cases of attribute retrieval:

        - Special attribute named ``_cf_dataset_options``: A local attribute.
          Do not delegate to super.
        - Indirect values for properties. See class docstring for explanation
          of indirect values.
        - Otherwise: Delegate to super.

        :param name: (str) name of attribute
        """
        # Special attribute named ``_cf_dataset_options``.
        if name == '_cf_dataset_options':
            return self.__dict__[name]

        # Indirect value
        # Cannot use ``getattr``, otherwise infinite recursion
        value = super(CFDataset, self).__getattribute__(name)
        is_indirected, indirected_property = _indirection_info(value)
        if is_indirected:
            # The condition for retrieving the value of an indirected property
            # is ``is_indirected`` and <the property named by
            # ``indirected_property`` exists> We must test attribute existence
            # using ``super(CFDataset, self).__getattribute__`` instead of
            # ``hasattr`` in order to process circular indirection correctly.
            # Cannot use ``hasattr`` because it captures the ``getattr``
            # infinite recursion exception and prevents this method from
            # raising it correctly.
            try:
                super(CFDataset, self).__getattribute__(indirected_property)
                # process indirect attribute normally, including indirection
                return getattr(self, indirected_property)
            except AttributeError:
                return value

        # Regular old value
        return value

    ###########################################################################
    # Unified metadata interface

    class UnifiedMetadata(object):
        """Presents a unified interface to certain global metadata attributes
        in a CFDataset object.

        Why?
        - A ``CFDataset`` can have metadata attributes named according to CMIP3
          or CMIP5 standards, or non-CMIP standards, presently grouped under the
          label 'other', depending on the file's origin (which is indicated
          by ``project_id``).
        - We want a common interface, i.e., common names, for a selected set
          of those differently named attributes.
        - We must avoid shadowing existing properties and methods on a
          ``CFDataset`` (or really, a ``netCDF4.Dataset``) object
          unified names we'd like to use for these metadata properties.
        - We'd like to present them as properties instead of as a dict,
          which has uglier syntax.

        How?
        - Create a property called ``metadata`` on ``CFDataset`` that is an
          instance of this class.
        """

        def __init__(self, dataset):
            self.dataset = dataset

        _aliases_by_project_id = {
            'CMIP3': {
                # Original aliases - some mangle the terminology somewhat,
                'project': 'project_id',
                'institution': 'institute',
                'model': 'source',
                'emissions': 'experiment_id',
                'run': 'realization',
                # Better aliases - adhere to CMIP5 terminology
                'institute': 'institute',
                'experiment': 'experiment_id',
                'ensemble_member': 'realization',
            },

            'CMIP5': {
                # Original aliases - some mangle the terminology somewhat,
                'project': 'project_id',
                'institution': 'institute_id',
                'model': 'gcm.model_id',
                'emissions': 'gcm.experiment_id',
                'run': 'ensemble_member',  # uses prefixed values
                # Better aliases - adhere to CMIP5 terminology
                'institute': 'institute_id',
                'experiment': 'gcm.experiment_id',
                'ensemble_member': 'ensemble_member',  # uses prefixed values
            },

            # CAUTION: This is a minimal temporary solution for a priority
            # project. This mapping uses attribute names (for both metadata.*
            # and mapped attributes) that apply to CMIP*/climate model derived
            # datasets. 'other' type datasets are not necessarily so.
            # For a full solution, see
            # https://github.com/pacificclimate/modelmeta/issues/52
            # Note also that this mapping does not use any prefixed values,
            # which (at present) are specific to CMIP/climate model derived
            # datasets.
            'other': {
                # Original aliases - some mangle the terminology somewhat,
                'project': 'project_id',
                'institution': 'institute_id',
                'model': 'model_id',
                'emissions': 'experiment_id',
                'run': 'run',  # bogus attribute to replace ensemble_member
                # Better aliases - adhere to CMIP5 terminology
                'institute': 'institute_id',
                'experiment': 'experiment_id',
            },
        }

        def __getattr__(self, alias):
            def missing_attribute(name):
                return CFAttributeError(
                    "Expected file to contain attribute '{}', "
                    "but no such attribute exists".format(name)
                )

            try:
                project_id = self.dataset.project_id
            except AttributeError:
                raise missing_attribute('project_id')

            if project_id not in self._aliases_by_project_id.keys():
                raise CFValueError(
                    "Expected file to have project id in {}, found '{}'"
                    .format(self._aliases_by_project_id.keys(), project_id)
                )

            aliases = self._aliases_by_project_id[project_id]

            if alias not in aliases.keys():
                raise CFAttributeError(
                    "No such unified attribute: '{}' for a project_id of '{}"
                    .format(alias, project_id)
                )

            def getdottedattr(obj, dotted_attr):
                attrs = dotted_attr.split('.')
                value = obj
                for attr in attrs:
                    value = getattr(value, attr)
                return value

            attr = aliases[alias]
            try:
                return getdottedattr(self.dataset, attr)
            except:
                raise missing_attribute(attr)

    @property
    def metadata(self):
        """Prefix for all aliased (common-name) global metadata attributes"""
        return self.UnifiedMetadata(self)

    ###########################################################################
    # Auto-prefixed GCM metadata interface

    class AutoGcmPrefixedAttribute(object):
        """Access attributes describing the original GCM input data used by
        the program that generated this file.

        In downstream processing of GCM files (e.g., downscaling), attributes
        describing the input GCM (e.g., 'model_id') are recorded in the output
        file with prefixes (e.g., 'driving_'). This class adds an automatically
        computed prefix to a base property name before accessing it. Type of
        file, and therefore prefix, is determined from the content of the file.

        NOTE: This class will prefix any base attribute name, no matter
        whether the prefixed name exists in the file.
        """

        def __init__(self, dataset):
            self.__dict__['dataset'] = dataset

        def _prefixed(self, attr):
            if self.dataset.is_unprocessed_gcm_output:
                prefix = ''
            elif self.dataset.is_downscaled_output:
                prefix = 'GCM__'
            elif self.dataset.is_hydromodel_dgcm_output:
                prefix = 'downscaling__GCM__'
            elif self.dataset.is_hydromodel_iobs_output:
                raise CFAttributeError(
                    'GCM attributes have no meaning for a hydrological model '
                    'forced by observational data')
            elif self.dataset.is_streamflow_model_dgcm_output:
                prefix = 'hydromodel__downscaling__GCM__'
            elif self.dataset.is_streamflow_model_iobs_output:
                raise CFAttributeError(
                    'GCM attributes have no meaning for a streamflow model '
                    'forced by observational data')
            elif (self.dataset.is_climdex_ds_gcm_output):
                prefix = 'downscaling__GCM__'
            else:
                raise CFAttributeError(
                    'Cannot generate automatic GCM attribute prefixes for a '
                    'file without a recognized type')

            return prefix + attr

        def __getattr__(self, attr):
            prefixed_attr = self._prefixed(attr)
            try:
                return getattr(self.dataset, prefixed_attr)
            except AttributeError:
                raise CFAttributeError(
                    "Expected file to contain attribute '{}' but no such "
                    "attribute exists".format(self._prefixed(attr)))

        def __setattr__(self, attr, value):
            prefixed_attr = self._prefixed(attr)
            return setattr(self.dataset, prefixed_attr, value)

    @property
    def gcm(self):
        return self.AutoGcmPrefixedAttribute(self)

    ###########################################################################
    # Other special metadata methods

    @property
    def ensemble_member(self):
        """CMIP5 standard ensemble member code for this file"""
        components = {}
        for component, attr in [
            ('r', 'realization'),
            ('i', 'initialization_method'),
            ('p', 'physics_version')
        ]:
            components[component] = getattr(self.gcm, attr)
        return 'r{r}i{i}p{p}'.format(**components)

    @property
    def model_type(self):
        """String indicating what type of model the file contains.
        Supports modelmeta/mm_cataloguer/index_netcdf.py.
        Really rudimentary decision making about model type.
        """
        if self.metadata.project == 'NARCCAP' or \
                        self.metadata.project not in ('IPCC Fourth Assessment', 'CMIP5'):
            return 'RCM'
        else:
            return 'GCM'

    ###########################################################################
    # File content type

    @property
    def sampling_geometry(self):
        """Return a string indicating the sampling geometry of the file.
        Sampling geometry indicates how the spatial coordinates for dependent
        variables in the file are defined.

        Currently we recognize the following types:

        - Gridded: the familiar XY (typically lat/long) grids.
            - output value: 'gridded'

        - Discrete Sampling Geometry (DSG). Subtypes:
            - timeSeries: Spatial locations are defined by a set of stations at
                arbitrary XY locations. They are not on a grid. For more info,
                see
                https://pcic.uvic.ca/confluence/display/CSG/Modeling+Discrete+Geometry+Datasets
                http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/build/ch09.html
                    - output value: 'dsg.timeSeries'


        """
        try:
            return 'dsg.{}'.format(self.featureType)
        except AttributeError:
            # TODO: Check more carefully for gridded datasets?
            return 'gridded'

    @property
    def is_time_invariant(self):
        """Return True if the metadata indicates that this datafile consists
        of time-independent data, such as elevation or soil data. In order to
        qualify, a dataset must lack a time dimension AND have the metadata
        frequency value of "fx" ("fixed").
        Reasoning: mere lack of a time dimension could plausibly be an error,
        but the frequency attribute indicates positive intent to create a
        time-independent dataset."""
        try:
            self.time_var
            return False # this dataset has a time dimensions
        except CFValueError:
            return self.frequency == "fx"

    @property
    def is_multi_year(self):
        return self.is_multi_year_mean

    @property
    def is_multi_year_mean(self):
        """Return True if the metadata indicates that the data consists of a
        multi-year mean, determined by testing if  the file contains a
        climatological time bounds variable.

        See http://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/
        cf-conventions.html#climatological-statistics,
        section 7.4

        In non-strict mode, failing metadata that conforms to the above
        standard, we use heuristics. These heuristics are emobodied here and in
        `climatology_bounds_var_name` in non-strict mode.

        If `self._cf_dataset_options['strict_metadata']` is True, use strict
        rules only for determining if this file contains multi-year means.
        Otherwise, use heuristics as well.
        """
        # If there is no time axis, this can't be a file of temporal means.
        try:
            time_var = self.time_var
        except CFValueError:
            return False

        # Strict and non-strict rules, according to flag
        if self.climatology_bounds_var_name:
            # TODO: Output of `climatology_bounds_var_name` does not
            # necessarily exist in the file. Should we check for existence?
            return True

        # Strict rules begin here
        if self._cf_dataset_options['strict_metadata']:
            return False

        # Additional non-strict heuristics begin here

        # Heuristic: Time variable has "suspicious" length:
        # 1, 4, 12, 5, 13, 16, 17 (yearly, seasonal, monthly, and
        # various concatenations thereof)
        # AND time variable has likely values (mid-month, mid-season, mid-year)

        def check_monthly(time_steps):
            def check(t, month):
                return t.month == month and t.day in {14, 15, 16}
            return all(check(next(time_steps), month)
                       for month in range(1, 13))

        def check_seasonal(time_steps):
            def check(t, month):
                return t.month == month and t.day in {15, 16, 17}
            return all(check(next(time_steps), month)
                       for month in (1, 4, 7, 10))

        def check_yearly(time_steps):
            t = next(time_steps)
            return ((t.month == 6 and t.day == 30) or
                    (t.month == 7 and t.day in {1, 2}))

        try:
            check_intervals = {
                1: (check_yearly,),
                4: (check_seasonal,),
                12: (check_monthly,),
                5: (check_seasonal, check_yearly),
                13: (check_monthly, check_yearly),
                16: (check_monthly, check_seasonal),
                17: (check_monthly, check_seasonal, check_yearly),
            }[time_var.size]
        except KeyError:
            pass  # No suspcious lengths: Try next heuristic
        else:
            time_steps = (t for t in self.time_steps['datetime'])
            if all(check(time_steps) for check in check_intervals):
                return True

        # Alas
        return False

    @property
    def is_gcm_derivative(self):
        """True iff the content of the file is GCM output or a derivative
        thereof"""
        return self.metadata.project in ('CMIP3', 'CMIP5')

    @property
    def is_other(self):
        """True iff the content of the file is an 'other' type."""
        return self.metadata.project == 'other'

    @property
    def is_unprocessed_gcm_output(self):
        """True iff the content of the file is unprocessed GCM output."""
        return self.is_gcm_derivative and self.product == 'output'

    @property
    def is_downscaled_output(self):
        """True iff the content of the file is downscaling output."""
        return self.is_gcm_derivative and self.product == 'downscaled output'

    @property
    def is_hydromodel_output(self):
        """True iff the content of the file is hydrological model output of
        any kind."""
        return self.product == 'hydrological model output'

    @property
    def is_hydromodel_dgcm_output(self):
        """True iff the content of the file is output of a hydrological model
        forced by downscaled GCM data."""
        return (self.is_gcm_derivative
                and self.is_hydromodel_output
                and self.forcing_type == 'downscaled gcm')

    @property
    def is_hydromodel_iobs_output(self):
        """True iff the content of the file is output of a hydrological
        model forced by interpolated observational data."""
        return (self.is_hydromodel_output
                and self.forcing_type == 'gridded observations')

    @property
    def is_streamflow_model_output(self):
        """True iff the content of the file is streamflow model output of
        any kind."""
        return self.product == 'streamflow model output'

    @property
    def is_streamflow_model_dgcm_output(self):
        """True iff the content of the file is output of a hydrological model
        forced by downscaled GCM data."""
        return (self.is_gcm_derivative
                and self.is_streamflow_model_output
                and self.hydromodel__forcing_type == 'downscaled gcm')

    @property
    def is_streamflow_model_iobs_output(self):
        """True iff the content of the file is output of a hydrological
        model forced by interpolated observational data."""
        return (self.is_streamflow_model_output
                and self.hydromodel__forcing_type == 'gridded observations')

    @property
    def is_climdex_output(self):
        """True iff the content of the file is output of climdex processing."""
        return self.product == 'CLIMDEX output'

    @property
    def is_climdex_gcm_output(self):
        """True iff the content of the file is output of climdex processing
        on an unprocessed GCM output file."""
        return (self.is_gcm_derivative
                and self.is_climdex_output
                and self.input_product == 'output')

    @property
    def is_climdex_ds_gcm_output(self):
        """True iff the content of the file is output of climdex processing
        on a downscaled GCM output file."""
        return (self.is_gcm_derivative
                and self.is_climdex_output
                and self.input_product == 'downscaled output')

    @property
    def is_gridded_obs(self):
        """True iff the content of the file is gridded observations"""
        return self.is_other and self.product == 'gridded observations'


    ###########################################################################
    # Dimensions and axes (gridded datasets)

    def axes_dim(self, dim_names=None):
        """Return a dictionary mapping canonical axis names to specified
        dimension names (or all dimensions in file).

        ASSUMPTION: There is at most one dimension (name) per canonical axis
        name. If not, the mapping inversion loses information.

        Canonical axis names are 'X' (longitude), 'Y' (latitude), 'Z' (level),
        'S' (reduced XY grid), 'T' (time).

        For information on reduced grids, see
        http://www.unidata.ucar.edu/blogs/developer/entry/cf_reduced_grids.

        :param dim_names: (str) List of names of dimensions of interest,
        None for all dimensions in file
        :return: (dict) Dictionary mapping canonical axis name to dimension
        name, for specified dimension names
        """
        # Invert {dim_name: axis} to {axis: dim_name}
        return {axis: dim_name
                for dim_name, axis in self.dim_axes(dim_names).items()}

    def dim_axes(self, dim_names=None):
        """Return a dictionary mapping specified dimension names (or all
        dimensions in file) to the canonical axis name for each dimension.

        Canonical axis names are 'X' (longitude), 'Y' (latitude), 'Z' (level),
        'S' (reduced XY grid), 'T' (time).

        For information on reduced grids, see
        http://www.unidata.ucar.edu/blogs/developer/entry/cf_reduced_grids.

        :param dim_names: (str) List of names of dimensions of interest,
            None for all dimensions in file
        :return: (dict) Dictionary mapping dimension name to canonical axis
            name, for specified dimension names
        """
        if not dim_names:
            dim_names = self.dim_names()

        if len(dim_names) == 0:
            return {}

        # Start with our best guess
        dim_name_to_axis = self.dim_axes_from_names(dim_names)

        # Then fill in the rest from the 'axis' attributes
        for dim_name in dim_name_to_axis.keys():
            if dim_name in self.dimensions and dim_name in self.variables \
                    and hasattr(self.variables[dim_name], 'axis'):
                dim_name_to_axis[dim_name] = self.variables[dim_name].axis

                # A reduced grid dimension has the 'compress' attribute.
                # This kind of dimension is labelled as a 'space' (S) dimension.
                if hasattr(self.variables[dim_name], 'compress'):
                    dim_name_to_axis[dim_name] = 'S'

        return dim_name_to_axis

    def dim_axes_from_names(self, dim_names=None):
        """Map names of dimensions in file to canonical axis names, based on
        well-known dimension names for axes.

        Canonical axis names are 'X' (longitude), 'Y' (latitude), 'Z' (level),
        'S' (reduced XY grid), 'T' (time).

        For information on reduced grids, see
        http://www.unidata.ucar.edu/blogs/developer/entry/cf_reduced_grids.

        Dimensions must be named with well-known names (e.g., 'latitude') to
        be mapped. See dict ``dim_to_axis`` for dimension names recognized.

        :param dim_names: (list of str) List of names of dimensions of interest,
            None for all dimensions in file
        :return: (dict) Dictionary mapping canonical axis name back to
            dimension name, for specified dimension names
        """
        if not dim_names:
            dim_names = self.dim_names()
        dim_to_axis = {
            'lat': 'Y',
            'latitude': 'Y',
            'lon': 'X',
            'longitude': 'X',
            'xc': 'X',
            'yc': 'Y',
            'x': 'X',
            'y': 'Y',
            'time': 'T',
            'timeofyear': 'T',
            'plev': 'Z',
            'lev': 'Z',
            'level': 'Z',
            'depth': 'Z',
        }
        return {dim: dim_to_axis[dim]
                for dim in dim_names if dim in dim_to_axis}

    def dim_names(self, var_name=None):
        """Return names of dimensions of a specified variable (or all
        dimensions) in this file.

        :param var_name: (str) Name of variable of interest
            (or None for all dimensions)
        :return (tuple): A tuple containing the names of the dimensions of
            the specified variable or of all dimensions in the file
        """
        if var_name:
            return self.variables[var_name].dimensions
        else:
            return tuple(k for k in self.dimensions.keys())

    def reduced_dims(self, var_name=None):
        """Return a dict containing the names of the X and Y dimensions of
        the named reduced spatial variable.
         If the named variable is not attributed as a reduced variable,
         return an empty dict.
         If the number of reduced dimensions is not 2, raise an error.

         Documentation on "compression by gathering", which this method deals
         with:
         http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#compression-by-gathering

        :param var_name: (str) name of reduced spatial variable
        :return:
        """
        axes_dim = self.axes_dim()
        if 'S' not in axes_dim:
            return {}
        compressed_axis_names = self.variables[var_name].compress.split()
        if len(compressed_axis_names) != 2:
            raise CFValueError(
                "Expected '{}:compress' to contain 2 variable names, found {}"
                    .format(var_name, compressed_axis_names))
        # TODO: Verify that compressed axis names are always in the order Y, X
        return {'X': compressed_axis_names[1], 'Y': compressed_axis_names[0]}


    ###########################################################################
    # Variables - general

    def dependent_varnames(self, dim_names=set()):
        """A list of the names of the dependent variables (see definition below)
        in this file, optionally limited by dependence on a specified set of
        dimensions.

        :param dim_names: (str or iterable(str)) name(s) of dimensions
            the returned variables must be dependent on.

        A *dependent variable* is a variable that is

        a. not a dimension, and
        b. dependent on (i.e., whose shape is defined by) one or more
           dimensions.

        Many variables in a NetCDF file are not dependent. These include:

        - dimensions
        - bounds variables
        - variables not dependent on any dimensions; in particular,
          variables used to carry coordinate reference system attributes

        The parameter ``dim_names`` specifies dimensions that the dependent
        variable(s) must be dependent on.
        A returned variable can be dependent on other dimensions in addition to
        those specified by ``dim_names``.

        When ``dim_names`` is the empty set, all dependent variables are
        returned regardless of dimensions. (Since the set of dimensions of any
        variable is a superset of the empty set.)
        """
        if isinstance(dim_names, six.string_types):
            dim_names = {dim_names}
        elif isinstance(dim_names, collections.Iterable):
            dim_names = {d for d in dim_names
                         if isinstance(d, six.string_types)}
        else:
            raise ValueError(
                'Invalid dimensions argument: must be None, str,'
                ' or iterable(str)')

        var_names = {
            variable.name for variable in self.variables.values()
            if len(variable.dimensions) > 0 and
               dim_names <= set(variable.dimensions)
        }
        non_dependent_var_names = set(self.dimensions.keys())
        for variable in self.variables.values():
            if hasattr(variable, 'bounds'):
                non_dependent_var_names.add(variable.bounds)
            if hasattr(variable, 'climatology'):
                non_dependent_var_names.add(variable.climatology)
            if hasattr(variable, 'grid_mapping'):
                non_dependent_var_names.add(variable.grid_mapping)
            if hasattr(variable, 'coordinates'):
                non_dependent_var_names.update(variable.coordinates.split())
        return [name for name in var_names - non_dependent_var_names]

    def var_bounds_and_values(self, var_name, bounds_var_name=None):
        """Return a list of tuples describing the bounds and values of a
        NetCDF variable, one tuple per variable value, defining
        (lower_bound, value, upper_bound)

        :param var_name: (str) name of NetCDF variable
        :param bounds_var_name: name of bounds variable; if not specified,
            use variable.bounds
        :return: list of tuples of the form (lower_bound, value, upper_bound)
        """
        variable = self.variables[var_name]
        values = variable[:]
        bounds_var_name = bounds_var_name or getattr(variable, 'bounds', None)

        if bounds_var_name:
            # Explicitly defined bounds: use them
            bounds_var = self.variables[bounds_var_name]
            return zip(bounds_var[:, 0], values, bounds_var[:, 1])
        else:
            # No explicit bounds: manufacture them
            midpoints = (
                # fake lower "midpoint", half of previous step below first value
                [(3*values[0] - values[1]) / 2] +
                # midpoints of values
                [(values[i] + values[i+1]) / 2 for i in range(len(values)-1)] +
                # fake upper "midpoint", half of previous step above last value
                [(3*values[-1] - values[-2]) / 2]
            )
            return zip(midpoints[:-1], values, midpoints[1:])

    def var_range(self, var_name, chunksize=2**20):
        """Return minimum and maximum value taken by variable (over all
        dimensions).

        :param var_name: (str) name of variable
        :return (tuple) (min, max) minimum and maximum values
        """
        # TODO: What about fill values?
        variable = self.variables[var_name]
        range_min = float('inf')
        range_max = float('-inf')
        chunk_shape = opt_chunk_shape(variable.shape, chunksize)
        for chunk in chunks(variable, chunk_shape):
            range_min = min(range_min, np.nanmin(chunk))
            range_max = max(range_max, np.nanmax(chunk))
        return range_min, range_max

    ###########################################################################
    # Variables - time
    # It is up to the caller of nchelpers functions to check is_time_invariant
    # and to not call time-related accessor functions on a dataset with no time
    # axis. The following accessors will throw a CFValueError "No axis is
    # attributed with time information" when called on a time-invariant dataset:
    # * time_var
    # * time_var_values
    # * time_steps
    # * time_step_size
    # * time_range
    # * time_range_as_dates
    # 
    # time_resolution returns a resolution of "fixed" for time-invariant datasets.
    @property
    def time_var(self):
        """The time variable (netCDF4.Variable) in this file"""
        axes = self.axes_dim()
        if 'T' in axes:
            time_axis = axes['T']
        else:
            raise CFValueError("No axis is attributed with time information")
        t = self.variables[time_axis]
        assert hasattr(t, 'units') and hasattr(t, 'calendar')
        return t

    @cached_property
    def time_var_values(self):
        return self.time_var[:]

    @cached_property
    def time_steps(self):
        """List of timesteps, i.e., values of the time dimension, in this file.
        """
        # This method appears to be very slow -- probably because of all the
        # frequently unnecessary work it does computing the properties
        # 'numeric' and 'datetime' it returns.
        t = self.time_var
        values = self.time_var_values
        return {
            'units': t.units,
            'calendar': t.calendar,
            'numeric': values,
            'datetime': num2date(values, t.units, t.calendar)
        }

    @cached_property
    def time_step_size(self):
        """Median of all intervals between successive timesteps in the file"""
        scale = time_scale(self.time_var)
        times = self.time_var_values
        median_difference = np.median(np.diff(times))
        return time_to_seconds(median_difference, scale)

    @property
    def time_resolution(self):
        """A standard string that describes the time resolution of the file"""
        if self.is_multi_year_mean:
            return {
                12: 'monthly',
                4: 'seasonal',
                1: 'yearly',
                5: 'seasonal,yearly',
                13: 'monthly,yearly',
                17: 'monthly,seasonal,yearly',
            }.get(self.time_var.size, 'other')
        if self.is_time_invariant:
            return "fixed"
        return resolution_standard_name(self.time_step_size)

    @cached_property
    def time_range(self):
        """Minimum and maximum timesteps in the file"""
        t = self.time_var_values
        return np.min(t), np.max(t)  # yup, this is actually necessary

    @property
    def time_range_as_dates(self):
        time_var = self.time_var
        return num2date(self.time_range, time_var.units, time_var.calendar)

    @property
    def time_bounds_var_name(self):
        """Return the name of the time bounds variable,
        None if no such variable exists.

        If `self.options['strict_metadata']` is True, use strict rules only for
        identifying the time bounds variable.
        Otherwise, use heuristics as well.
        """
        # Strict rules begin here

        # If there is no time axis, there are no time bounds. Fail.
        try:
            time_var = self.time_var
        except CFValueError:
            return None

        # If time:bounds attribute exists, use it.
        try:
            var_name = time_var.bounds
            if hasattr(self.variables, var_name):
                return var_name
        except AttributeError:
            pass

        if self._cf_dataset_options['strict_metadata']:
            return None

        # Non-strict heuristics begin here

        # Heuristic: A variable with a likely name exists
        for name in ['time_bounds', 'time_bnds']:
            if name in self.variables:
                return name

        # Alas
        return None

    @property
    def time_bounds_values(self):
        """Return values of the time bounds variable as a Python list."""
        if self.time_bounds_var_name is None:
            raise ValueError(
                'No time bounds variable is detectable in this file.')
        time_bounds_var = self.variables[self.time_bounds_var_name]
        return time_bounds_var[...]

    @property
    def climatology_bounds_var_name(self):
        """Return the name of the climatological time bounds variable,
        None if no such variable exists.

        If `self.options['strict_metadata']` is True, use strict rules only
        for identifying climatology bounds variable.
        Otherwise, use heuristics as well.
        """
        # Strict rules begin here

        # If there is no time axis, there are no climo bounds. Fail.
        try:
            time_var = self.time_var
        except CFValueError:
            return None

        # If time:climatology attribute exists, use it.
        try:
            return time_var.climatology
        except AttributeError:
            if self._cf_dataset_options['strict_metadata']:
                return None

        # Non-strict heuristics begin here

        # Heuristic: A variable with a likely name exists
        for name in ['climatology_bounds', 'climatology_bnds',
                     'climo_bounds', 'climo_bnds']:
            if name in self.variables:
                return name

        def multi_year_bounds(time_bounds, scale):
            """Return True iff time bounds is non-empty and each time bound
            spans at least 2 years.

            Note: 2 years is small, but this has to accommodate test code which
            uses relatively short multi-year means.
            """
            return time_bounds.size > 0 and all(
                time_to_seconds(end_time, scale) -
                time_to_seconds(start_time, scale) >=
                time_to_seconds(720, 'days')
                for start_time, end_time in time_bounds[:]
            )

        # Heuristic: Time variable has 'bounds' (not 'climatology') attribute
        # identifying an existing variable AND that time bounds variable
        # brackets multi-year periods (corresponding to the climatological
        # averaging)
        if hasattr(time_var, 'bounds'):
            scale = time_scale(time_var)
            time_bounds_name = time_var.bounds
            try:
                time_bounds = self.variables[time_bounds_name]
                if multi_year_bounds(time_bounds, scale):
                    return time_bounds_name
            except KeyError:
                pass  # claimed time bounds variable does not exist

        # Heuristic: Variable with name 'time_bounds' or 'time_bnds' exists
        # (but not identified by time:bounds) AND that time bounds variable
        # brackets multi-year periods (corresponding to the climatological
        # averaging)
        for time_bounds_name in ['time_bounds', 'time_bnds']:
            scale = time_scale(time_var)
            if time_bounds_name in self.variables:
                time_bounds = self.variables[time_bounds_name]
                if multi_year_bounds(time_bounds, scale):
                    return time_bounds_name

        # Alas
        return None

    @property
    def climatology_bounds_values(self):
        """Return the values of the climatology bounds variable
        as a numpy array of numeric values (not datetimes)"""
        if not self.is_multi_year_mean:
            raise ValueError('climatology bounds are defined only for files'
                             'containing multi-year means')
        if self.climatology_bounds_var_name is None:
            raise ValueError(
                'No climatology bounds variable is detectable in this file.')
        climatology_bounds_var = \
            self.variables[self.climatology_bounds_var_name]
        return climatology_bounds_var[...]

    def time_bounds_extrema(self, nominal=True, closed=True):
        """Extrema of the time bounds, or in the case of a file of multi-year
        means, the extrema of the climatological bounds. Values returned are in
        native numerical units of the file.

        :param nominal: (bool) if True, return nominal extrema (see note 1
            below); otherwise return unadjusted extrema.
        :param closed: (bool) if True, return bounds as a closed interval
            ``[start, end]``; otherwise return as a half-open interval
            ``[start, end)``. (See note 2 below.)

        The extrema of time bounds is defined by the mininum of the lower time
        bounds and the maximum of the upper time bounds. They bracket the
        interval covered by the data in the file.

        1. Nominal extrema

        The nominal extrema for a non-climo file is just the extrema of the
        time bounds.

        The nominal extrema of climo bounds are the bounds of th enominal
        period of averaging, which in the case of seasonal averages is slightly
        different than the exact bounds.
        Seasons are defined in 3-month periods beginning in
        December. The period of multi-year average nominally from the beginning
        (Jan 1) of one year to the end (end Dec) of another year is actually
        shifted back 1 month because of this. This function adjusts to make
        the nominal range comparable for all averaging periods (monthly,
        seasonal, yearly).

        2. Closed vs. half-open bounds

        Standard practice in CF compliant files
        is to specify time bounds as a half-open interval ``[start, end)``,
        such that a time ``x`` is in the interval iff ``start <= x < end``.
        (Note strict inequality.)

        However, in common *usage* (e.g., unique ids, file names, speech),
        time bounds are expressed as closed intervals, ``[start, end]``,
        ``start <= x <= end``

        This function accommodates both styles with the ``closed`` parameter.
        When ``closed`` is ``True``, the endpoint is returned with a small
        amount (1 second) subtracted so that the interval is closed. This
        introduces a slight inaccuracy which for our purposes does not matter.
        When ``closed`` is ``False``, the half-open interval is returned
        unchanged (except for adjustments for seasonal averaging period).
        """
        units, calendar = self.time_var.units, self.time_var.calendar

        if self.is_multi_year_mean:
            bounds_values = self.climatology_bounds_values
        else:
            bounds_values = self.time_bounds_values

        extrema = (bounds_values[0, 0], bounds_values[-1, 1])

        if nominal and \
                self.is_multi_year_mean and self.time_resolution == 'seasonal':
            # Seasonal climo bounds are a month back of the nominal averaging
            # period. Add it back in.

            def add_1_month(num):
                """Add a relative time specified in kwargs as for relativedelta.
                Easiest way to do that is to convert to a real datetime,
                add a month, and convert back.
                """
                return date2num(
                    to_datetime(num2date(num, units, calendar)) +
                    relativedelta(months=1),
                    units,
                    calendar
                )

            extrema = tuple(add_1_month(e) for e in extrema)

        if closed:
            delta = seconds_to_time(1.0, units=time_scale(self.time_var))
            extrema = (extrema[0], extrema[1] - delta)

        return extrema

    @cached_property
    def nominal_time_span(self):
        """Nominal time coverage of the file.

        In the case of multi-year means, nominal coverage is the nominal range
        of times covered by the avearaging periods in the file, and equals
        the extrema of the climatological bounds, adjusted to closed interval
        form and nominal period.

        In the case of non multi-year mean files, nominal coverage is just
        the extrema of values in the time variable. A more natural and uniform
        definition would be the extrema of the time bounds, but time bounds are
        not always present in our data files, or not always correct (sigh),
        so we use to this simpler definition.
        """
        if self.is_multi_year_mean:
            return self.time_bounds_extrema(nominal=True, closed=True)
        else:
            return self.time_range

    ###########################################################################
    # Variables - for DSG files

    def _check_dsg_sampling_geometry(self, what):
        if self.sampling_geometry != 'dsg.timeSeries':
            raise CFValueError(
                'A(n) {} is defined only for files with '
                'discrete sampling geometry. This file has a sampling'
                'geometry type of {}'.format(what, self.sampling_geometry))

    def coordinate_vars(self, var_name):
        """Return list of coordinate variables (instance variables) associated
        with the named variable in this file.

        Valid only for DSG files.
        """
        self._check_dsg_sampling_geometry('coordinate variable')
        variable = self.variables[var_name]
        return [self.variables[name] for name in variable.coordinates.split()]

    def instance_dim(self, var_name):
        """Return the instance dimension associated with the named
        variable in this file.

        Valid only for DSG files.
        """
        self._check_dsg_sampling_geometry('instance dimension')
        return self.dimensions[self.coordinate_vars(var_name)[0].dimensions[0]]

    def id_instance_var(self, var_name, cf_role='timeseries_id'):
        """Return the instance variable associated with the named
        variable in this file with attribute cf_role equal to specified cf_role.

        IOW: Return the instance variable providing a unique id for the
        instances of var_name in this file.

        Valid only for DSG files.
        """
        self._check_dsg_sampling_geometry('instance variable')
        try:
            return next(
                c for c in self.coordinate_vars(var_name)
                if getattr(c, 'cf_role', None) == cf_role
            )
        except StopIteration:
            raise CFValueError(
                'No coordinate of variable {} in this file has attribute '
                'cf_role with value {}'.format(var_name, cf_role))

    def spatial_instance_var(self, var_name, axis):
        """Return the spatial instance variable associated with the named
        variable in this file for the specified axis (X/lon or Y/lat).

        IOW: Return the instance variable providing a lon/lat for the
        instances of var_name in this file.

        Valid only for DSG files.
        """
        self._check_dsg_sampling_geometry('instance variable')
        axis_to_coord_names = {
            'X': ['lon', 'longitude'],
            'Y': ['lat', 'latitude'],
        }
        try:
            coord_names = axis_to_coord_names[axis.upper()]
        except KeyError:
            raise CFValueError(
                'axis arg must be one of {}, but was {}'
                .format(axis_to_coord_names.keys(), axis)
            )
        try:
            return next(
                c for c in self.coordinate_vars(var_name)
                if c.name in coord_names
            )
        except StopIteration:
            raise CFValueError(
                'No coordinate of variable {} in this file has name in the'
                'expected list of {}-axis names {}'
                .format(var_name, axis, coord_names))

    ###########################################################################
    # Variables - spatial

    @property
    def lat_var(self):
        """The latitude variable (netCDF4.Variable) in this file"""
        axes = self.axes_dim()
        try:
            return self.variables[axes['Y']]
        except KeyError:
            raise CFValueError(
                'No axis is attributed with latitude information')

    @property
    def lon_var(self):
        """The longitude variable (netCDF4.Variable) in this file"""
        axes = self.axes_dim()
        try:
            return self.variables[axes['X']]
        except KeyError:
            raise CFValueError(
                'No axis is attributed with longitude information')

    def proj4_string(self, var_name, default=None, ellps='WGS84'):
        """
        Return a PROJ.4 definition string for the specified variable, based
        on the `CF Convention standard projection definition attributes
        <http://cfconventions.org/Data/cf-conventions/cf-conventions-1.7/build/ch05s06.html>`_
        defined in the NetCDF file for that variable.

        :param var_name: (str) name of variable
        :param default: (str) default value in case no CRS data is detected
        :param ellps: (str) default value for proj4 parameter +ellps in cases
            (projections) where the CF Conventions do not specify metadata
            attributes for the Earth's figure (geoid).
        :returns (str): PROJ.4 definition string
        :raises:
            ``CFAttributeError`` if any expected CF Conventions standard metadata
            attribute is missing.
            ``CFValueError`` if the projection name specified in the metadata is
            not recognized (i.e., not covered by one of the functions below).

        The default value is returned when (a) it is not None and (b) no CRS
        data appears to be defined for the variable, which is equivalent to the
        condition that the variable has no attribute ``grid_mapping``.

        Exceptions are raised for all other erroneous CRS metadata conditions
        regardless of the value of ``default``.
        """

        # The following functions return a PROJ.4 definition string for
        # the specific cases we handle. Each is named with the
        # ``grid_mapping_name`` defined in the CF Convention standard.

        def polar_stereographic(var, ellps=ellps):
            """
            Return PROJ.4 definition string for a polar stereographic
            projection.
            """
            lat_ts = getattr_cf_error(var, 'standard_parallel')
            lat_0 = getattr_cf_error(var, 'latitude_of_projection_origin')
            lon_0 = getattr_cf_error(var, 'straight_vertical_longitude_from_pole')
            x_0 = getattr_cf_error(var, 'false_easting')
            y_0 = getattr_cf_error(var, 'false_northing')
            if x_0 == '':
                x_0 = 0
            if y_0 == '':
                y_0 = 0
            return (
                '+proj=stere +ellps={ellps} '
                '+lat_ts={lat_ts} +lat_0={lat_0} +lon_0={lon_0} '
                '+x_0={x_0} +y_0={y_0} +k_0=1'
                    .format(**locals())
            )

        def rotated_latitude_longitude(var):
            """
            Return PROJ.4 definition string for a rotated pole grid.
            """
            try:
                lat_0 = getattr_cf_error(var, "north_pole_latitude")
                lon_0 = getattr_cf_error(var, "north_pole_longitude")
            except CFAttributeError:
                lat_0 = getattr_cf_error(var, "grid_north_pole_latitude")
                lon_0 = getattr_cf_error(var, "grid_north_pole_longitude")

            # TODO: Verify this computation and the form of the string below.
            lon_0 = _normalize180(lon_0 + 180)

            # Comment below is from original R code.
            # The more or less direct way here is to generate an inverse
            # projection by feeding the values directly in as o_lon_p and
            # o_lat_p; this is to generate a normal, forward projection.
            return (
                '+proj=ob_tran +o_proj=longlat +lon_0={lon_0} +o_lat_p={lat_0} '
                '+a=1 +to_meter=0.0174532925199 +no_defs'
                    .format(**locals())
            )

        def lambert_conformal_conic(var, ellps=ellps):
            """
            Return PROJ.4 definition string for a Lambert conformal conic
            projection.
            """
            lat_ts = getattr_cf_error(var, 'standard_parallel')
            if isinstance(lat_ts, np.ndarray):
                if lat_ts.size != 2:
                    raise CFValueError(
                        'List of standard_parallel values must have length '
                        'exactly 2')
                lat_1, lat_2 = lat_ts
            else:
                lat_1 = lat_ts
                # TODO: Is it really legit to have component '+lat2=' in
                # PROJ.4 defn string?
                lat_2 = ''
            lat_0 = getattr_cf_error(var, 'latitude_of_projection_origin')
            lon_0 = getattr_cf_error(var, 'longitude_of_central_meridian')
            x_0 = getattr_cf_error(var, 'false_easting')
            y_0 = getattr_cf_error(var, 'false_northing')

            return (
                '+proj=lcc +ellps={ellps} '
                '+lat_0={lat_0} +lat_1={lat_1} +lat_2={lat_2} '
                '+lon_0={lon_0} +y_0={y_0} +x_0={x_0}'
                    .format(**locals())
            )

        def transverse_mercator(var, ellps=ellps):
            """
            Return PROJ.4 definition string for a transverse Mercator
            projection.
            """
            lat_0 = getattr_cf_error(var, 'latitude_of_projection_origin')
            lon_0 = getattr_cf_error(var, 'longitude_of_central_meridian')
            k_0 = getattr_cf_error(var, 'scale_factor_at_central_meridian')
            x_0 = getattr_cf_error(var, 'false_easting')
            y_0 = getattr_cf_error(var, 'false_northing')

            return (
                '+proj=tmerc +ellps={ellps} '
                '+lat_0={lat_0} +lon_0={lon_0} '
                '+k_0={k_0} +x_0={x_0} +y_0={y_0}'
                    .format(**locals())
            )

        def latitude_longitude(var):
            """
            Return PROJ.4 definition string for a latitude-longitude
            (spherical earth) projection.
            """
            parts = ["+proj=longlat"]

            for template, attr_name in (
                    ('+a={}', 'semi_major_axis'),
                    ('+rf={}', 'inverse_flattening'),
                    ('+b={}', 'semi_minor_axis'),
                    ('+lon_0={}', 'longitude_of_prime_meridian'),
            ):
                try:
                    parts.append(template.format(getattr(var, attr_name)))
                except AttributeError:
                    pass

            return ' '.join(parts)

        try:
            grid_mapping_var_name = getattr(
                self.variables[var_name], 'grid_mapping')
        except AttributeError:
            if default is not None:
                return default
            raise CFAttributeError(
                'No coordinate reference system metadata found in file.')
        grid_mapping_var = self.variables[grid_mapping_var_name]
        grid_mapping_name = getattr_cf_error(
            grid_mapping_var, 'grid_mapping_name')
        try:
            # Select the function that returns the desired PROJ.4 definition
            # string, and invoke it. Using ``locals()`` here is slightly fragile
            # (``locals()`` contains other objects than the PROJ.4 functions),
            # but it is handy and concise.
            return locals()[grid_mapping_name](grid_mapping_var)
        except KeyError:
            raise CFValueError(
                "'{}' is not a recognized value for grid_mapping_name"
            )

    ###########################################################################
    # Standard file identifiers

    def _cmor_type_filename_components(
            self,
            tres_to_mip_table=standard_tres_to_mip_table,
            **override
    ):
        """Return a dict containing appropriate arguments to function
        ``cmor_type_filename`` (q.v.), with content built from this file's
        metadata.

        :param tres_to_mip_table: (dict) a dict mapping time resolution
            (as computed by the property ``self.time_resolution``) to a valid
            MIP table name.
        :param override: keyword arguments that can override or extend the
            base components computed here.
        :return: (dict) as above
        """

        # File content-independent components
        components = { 'variable': '+'.join(sorted(self.dependent_varnames()))}

        if not self.is_time_invariant:
            components["time_range"] = _cmor_formatted_time_range(
                *to_datetime(
                    num2date(
                        self.nominal_time_span,
                        self.time_var.units, self.time_var.calendar
                    )
                )
            )

        if self.is_multi_year:
            components.update(
                frequency=self.frequency
            )
        else:
            # Regarding how the 'mip_table' component is defined here,
            # see the discussion in section titled "MIP table / table_id" in
            # https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data
            # Specifically, we do not consult the value of the attribute
            # ``table_id`` because it is too limited for our needs. Instead we
            # map the file's time resolution to a value.
            components.update(
                mip_table=tres_to_mip_table and
                          tres_to_mip_table.get(self.time_resolution, None)
            )

        if self.is_gcm_derivative:

            components.update(ensemble_member=self.ensemble_member)

            # Components depending on the type of file
            if self.is_unprocessed_gcm_output:
                components.update(
                    model=self.metadata.model,
                    experiment=self.metadata.emissions,
                )
            elif self.is_downscaled_output:
                components.update(
                    downscaling_method=self.method_id,
                    model=self.gcm.model_id,
                    experiment=_replace_commas(self.gcm.experiment_id),
                    geo_info=getattr(self, 'domain', None)
                )
            elif self.is_hydromodel_dgcm_output:
                components.update(
                    hydromodel_method=_replace_commas(self.method_id),
                    model=self.gcm.model_id,
                    experiment=_replace_commas(self.gcm.experiment_id),
                    geo_info=getattr(self, 'domain', None)
                )
            elif self.is_hydromodel_iobs_output:
                components.update(
                    hydromodel_method=_replace_commas(self.method_id),
                    obs_dataset_id=self.observations__dataset_id,
                    geo_info=getattr(self, 'domain', None)
                )
            elif self.is_streamflow_model_dgcm_output:
                components.update(
                    model=self.gcm.model_id,
                    experiment=_replace_commas(self.gcm.experiment_id),
                    geo_info=getattr(self, 'domain', None)
                )
            elif self.is_climdex_output:
                components.update(
                    downscaling_method=self.downscaling__method_id,
                    model=self.gcm.model_id,
                    experiment=_replace_commas(self.gcm.experiment_id),
                    geo_info=getattr(self, 'domain', None)
                )

        elif self.is_other:
            # CAUTION: Temporary solution to a bigger problem here
            # https://pcic.uvic.ca/confluence/display/CSG/Indexing+Gridded+Observation+Datasets
            components.update(
                model=self.metadata.model,
                experiment=self.metadata.experiment,
                geo_info=getattr(self, 'domain', None)
            )

        # Override with supplied args
        components.update(**override)

        return components

    @property
    def cmor_filename(self):
        """A CMOR standard filename for this file, based on its metadata
        contents."""
        return cmor_type_filename(
            extension='.nc', **self._cmor_type_filename_components()
        )

    @property
    def unique_id(self):
        """A unique id for this file, based on its CMOR filename"""
        unique_id = cmor_type_filename(**self._cmor_type_filename_components())

        dim_axes = set(self.dim_axes_from_names().values())
        if not (dim_axes <= {'X', 'Y', 'Z', 'T'}):
            unique_id += "_dim" + ''.join(sorted(dim_axes))

        return unique_id.replace('+', '-')  # In original code, but why?

    ###########################################################################
    # Climatology-specific methods

    @property
    def climo_periods(self):
        """List of the standard climatological periods (see function
        ``standard_climo_periods``) that are a subset of the date range in
        the file."""

        def last_required_climo_timestamp(e):
            """Returns the first day of the final interval (individual month,
            season, etc) needed for this climatology.
            To verify that data is present to calculate the climatology,
            a timestamp during or after this interval is needed (>= the date
            returned by this function)."""
            if self.time_resolution == 'seasonal' and e.month == 12:
                # PCIC's definition of a "seasonal" climatology that runs from
                # year N to year M includes the winter spanning years N-1 to N,
                # but not the winter spanning years M to M+1.
                # Therefore, even though December of the final year M
                # falls within the span of years N-M designated by the climatology
                # interval, we don't require data for this month.
                # The final required timestamp is Autumn of year M.
                return truncate_to_resolution(e - relativedelta(months=1),
                                              self.time_resolution)
            else:
                return truncate_to_resolution(e, self.time_resolution)

        time_var = self.time_var
        s_time, e_time = self.time_range
        units = time_var.units
        calendar = time_var.calendar
        return {
            k: (climo_start_date, climo_end_date)
            for k, (climo_start_date, climo_end_date)
            in standard_climo_periods(calendar).items()
            if s_time <= date2num(climo_start_date, units, calendar) and
            date2num(last_required_climo_timestamp(climo_end_date), units, calendar) <= e_time
        }
