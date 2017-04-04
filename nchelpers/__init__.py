from datetime import datetime
import dateutil.parser
import hashlib
import re

from cached_property import cached_property
import numpy as np
import six

from netCDF4 import Dataset, num2date, date2num
from nchelpers.date_utils import resolution_standard_name, time_to_seconds, d2ss
from nchelpers.decorators import prevent_infinite_recursion

# Map of nchelpers time resolution strings to MIP table names, standard where possible.
# For an explanation of the content of this map, see the discussion in section titled "MIP table / table_id" in
# https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data
standard_tres_to_mip_table = {
    '1-minute': 'subhr', # frequency std
    '2-minute': 'subhr', # frequency std
    '5-minute': 'subhr', # frequency std
    '15-minute': 'subhr', # frequency std
    '30-minute': 'subhr', # frequency std
    '1-hourly': '1hr', # custom: neither a MIP table nor a frequency standard term
    '3-hourly': '3hr', # frequency std
    '6-hourly': '6hr', # frequency std
    '12-hourly': '12hr', # custom: neither a MIP table nor a frequency standard term
    'daily': 'day', # MIP table and frequency standard
    'monthly': 'mon', # frequency std
    'yearly': 'yr', # frequency std
}


def cmor_type_filename(extension='', **component_values):
    """Return a filename built from supplied component values, following the a CMOR-based filename standards in
    https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data    .

    Produces a CMOR standard filename if all and only required CMOR filename components are defined.
    Omits any components not in list of component names. Omits any component with a None value.

    Warning: This thing is no smarter than it has to be. Does not enforce required components or any rules other than
    order.
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
    return '_'.join(component_values[cname] for cname in component_names if component_values.get(cname, None) != None) \
           + extension


def standard_climo_periods(calendar='standard'):
    """Returns a dict containing the start and end dates, under the specified calendar, of standard climatological
    periods, keyed by abbreviations for those periods, e.g., '6190' for 1961-1990"""
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


def _replace_commas(s, sep='+'):
    """Return a string constructed by joining with `sep` the substrings of `s` delimited by commas and arbitrary spaces.

    :param s: (str) string to split on commas and join with sep
    :param sep: (str) separator string for join
    :return: see above
    """
    return re.sub(r'\s*,\s*', sep, s)


def _cmor_formatted_time_range(t_min, t_max, time_resolution='daily'):
    """Format a time range as string in YYYY[mm[dd]] format, min and max separated by a dash."""
    try:
        format = {'yearly': '%Y', 'monthly': '%Y%m', 'daily': '%Y%m%d'}[time_resolution]
    except KeyError:
        raise ValueError("Cannot format a time range with resolution '{}' (only yearly, monthly or daily)"
                         .format(time_resolution))
    return '{}-{}'.format(t_min.strftime(format), t_max.strftime(format))


def _handle_indirection(value):
    """Return (True, <property name>) iff ``value`` is a string that indirects to another property value.
    Otherwise return (False, None).
    See CFDataset docstring for explanation of indirect values.

    :param value: (str) literal value (uninterpreted under indirection rule) of a property
    :return: (tuple) (is_indirected, property_name) see above
    """
    if isinstance(value, six.string_types) and value[0] == '@':
        return True, value[1:]
    return False, None


class CFDataset(Dataset):
    """Represents a CF (climate and forecast) dataset stored in a NetCDF file.

    Properties and methods on this class expose metadata that is expected to be found in such files,
    and values computed from that metadata.

    Indirect values
    ---------------

    Any property of a CFDataset object can be given an "indirect value," which is a string of the form

        ``@<property name>``

    ``@`` signfies indirection
    ``<property name>`` is the name of any property of the object

    The value of a property with an indirect value is the value of the property named in the indirect value.
    If the property named in the indirect value does not exist, then the value of the property is just the unprocessed
    value of the original property.

    Example: Let cf be a CFDataset object. Then the following test passes::

        cf.alpha = 'hello'              # ordinary string value
        cf.beta = '@alpha'              # indirect value
        assert cf.beta == 'hello'       # indirection works
        cf.gamma = '@not_here'          # indirect to a non-existent property ...
        assert cf.gamma == '@not_here'  # and get back the unprocessed string


    Because indirection hides the uninterpreted value (e.g., '@alpha') of a property with an indirect value,
    this class also has the methods::

        is_indirected(name)
        get_direct_value(name)

    where ``name`` is the name of any property.

    Helper functions in modelmeta
    -----------------------------

    Some of this class replaces the functionality of helper functions defined in pacificclimate/modelmeta. The
    following list maps those functions to properties/methods of this class.

    get_file_metadata -> metadata.<global attribute>
        - <global attribute> is the unified name for actual CF standard global attributes in the NetCDF file
        - doesn't include time metadata; use properties below instead
    create_unique_id -> unique_id
    nc_get_dim_axes_from_names -> dim_axes_from_names
    nc_get_dim_names -> dim_names
    nc_get_dim_axes -> dim_axes
    get_climatology_bounds_var_name -> climatology_bounds_var_name
    is_multi_year_mean -> is_multi_year_mean
    get_time_step_size -> time_step_size
    get_time_resolution -> time_resolution
    get_timeseries -> time_steps
    get_time_range -> time_range
    get_first_MiB_md5sum -> first_MiB_md5sum
    get_important_varnames -> dependent_varnames
    """

    def __init__(self, *args, **kwargs):
        super(CFDataset, self).__init__(*args, **kwargs)

    def is_indirected(self, name):
        """Return True iff the property named has an indirect value.
        See class docstring for explanation of indirect values.
        """
        return _handle_indirection(self.get_direct_value(name))[0]

    def get_direct_value(self, name):
        """Return the value of the named property without indirection processing.
        See class docstring for explanation of indirect values.
        """
        return super(CFDataset, self).__getattribute__(name)

    @prevent_infinite_recursion
    def __getattribute__(self, name):
        """Handle indirect values for properties.
        See class docstring for explanation of indirect values.

        :param name: (str) name of attribute
        """
        value = super(CFDataset, self).__getattribute__(name)  # cannot use ``getattr``, otherwise infinite recursion
        is_indirected, indirected_property = _handle_indirection(value)
        if is_indirected:
            # The condition for retrieving the value of an indirected property is
            #   ``is_indirected`` and <the property named by ``indirected_property`` exists>
            # We must test attribute existence using ``super(CFDataset, self).__getattribute__`` instead of ``hasattr``
            # in order to process circular indirection correctly. Cannot use ``hasattr`` because it captures the
            # ``getattr`` infinite recursion exception and prevents this method from raising it correctly.
            try:
                super(CFDataset, self).__getattribute__(indirected_property)
                return getattr(self, indirected_property)  # process indirect attribute normally, including indirection in it
            except AttributeError:
                return value
        return value

    @property
    def first_MiB_md5sum(self):
        """MD5 digest of first MiB of this file"""
        m = hashlib.md5()
        with open(self.filepath(), 'rb') as f:
            m.update(f.read(2**20))
        return m.digest()

    @property
    def dependent_varnames(self):
        """A list of the primary (dependent) variables in this file.

        Many variables in a NetCDF file describe the *structure* of the data and aren't necessarily the
        values that we actually care about. For example a file with temperature data also has to include
        latitude/longitude variables, a time variable, and possibly bounds variables for each of the dimensions.
        These dimensions and bounds are independent variables.

        This function filters out the names of all independent variables and just gives you the "important" (dependent)
        variable names.
        """
        variables = set(self.variables.keys())
        non_dependent_variables = set(self.dimensions.keys())
        for variable in self.variables.values():
            if hasattr(variable, 'bounds'):
                non_dependent_variables.add(variable.bounds)
            if hasattr(variable, 'climatology'):
                non_dependent_variables.add(variable.climatology)
            if hasattr(variable, 'coordinates'):
                non_dependent_variables.update(variable.coordinates.split())
        return [v for v in variables - non_dependent_variables]

    def dim_names(self, var_name=None):
        """Return names of dimensions of a specified variable (or all dimensions) in this file
        
        :param var_name: (str) Name of variable of interest (or None for all dimensions)
        :return (tuple): A tuple containing the names of the dimensions of the specified variable or of
            all dimensions in the file
        """
        if var_name:
            return self.variables[var_name].dimensions
        else:
            return tuple(k for k in self.dimensions.keys())

    def dim_axes_from_names(self, dim_names=None):
        """Translate well-known dimension names to canonical axis names.
        Canonical axis names are 'X', 'Y', 'Z', 'T'.
        See dict dim_to_axis for dimension names recognized.
        
        :param dim_names: (list of str) List of names of dimensions of interest, None for all dimensions in file
        :return: (dict) Dictionary mapping canonical axis name back to dimension name, for specified dimension names
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
            'level': 'Z'
        }
        return {dim_to_axis[dim]: dim for dim in dim_names if dim in dim_to_axis}

    def dim_axes(self, dim_names=None):
        """Return a dictionary mapping specified dimension names (or all dimensions in file) to
        the canonical axis name for each dimension.
        
        :param dim_names: (str) List of names of dimensions of interest, None for all dimensions in file
        :return: (dict) Dictionary mapping dimension name to canonical axis name, for specified dimension names
        """
        if not dim_names:
            dim_names = self.dim_names()

        if len(dim_names) == 0:
            return {}

        # Start with our best guess
        axis_to_dim = self.dim_axes_from_names(dim_names)

        # Then fill in the rest from the 'axis' attributes
        # TODO: Does this happen? i.e., when are dimension names the same as axis names?
        # Alternatively, is this some kind of (relatively benign) programming error?
        for axis in axis_to_dim.keys():
            if axis in self.dimensions and axis in self.variables \
                    and hasattr(self.variables[axis], 'axis'):
                axis_to_dim[axis] = self.variables[axis].axis

                # Apparently this is how a "space" dimension is attributed?
                if hasattr(self.variables[axis], 'compress'):
                    axis_to_dim[axis] = 'S'

        # Invert {axis: dim} to {dim: axis}
        return {dim: axis for axis, dim in axis_to_dim.items()}

    @property
    def climatology_bounds_var_name(self):
        """Return the name of the climatological time bounds variable, None if no such variable exists"""
        axes = self.dim_axes_from_names()
        if 'T' in axes:
            time_axis = axes['T']
        else:
            return None

        try:
            return self.variables[time_axis].climatology
        except AttributeError:
            return None

    @property
    def is_multi_year_mean(self):
        """True if the metadata indicates that the data consists of a multi-year mean,
        i.e., if the file contains a climatological time bounds variable.
        See http://cfconventions.org/Data/cf-conventions/cf-conventions-1.6/build/cf-conventions.html#climatological-statistics,
        section 7.4"""
        return bool(self.climatology_bounds_var_name)

    @property
    def lat_var(self):
        """The latitude variable (netCDF4.Variable) in this file"""
        axes = self.dim_axes_from_names()
        try:
            return self.variables[axes['Y']]
        except KeyError:
            raise ValueError('No axis is attributed with latitude information')

    @property
    def lon_var(self):
        """The longitude variable (netCDF4.Variable) in this file"""
        axes = self.dim_axes_from_names()
        try:
            return self.variables[axes['X']]
        except KeyError:
            raise ValueError('No axis is attributed with longitude information')

    @property
    def time_var(self):
        """The time variable (netCDF4.Variable) in this file"""
        axes = self.dim_axes_from_names()
        if 'T' in axes:
            time_axis = axes['T']
        else:
            raise ValueError("No axis is attributed with time information")
        t = self.variables[time_axis]
        assert hasattr(t, 'units') and hasattr(t, 'calendar')
        return t

    @cached_property
    def time_var_values(self):
        return self.time_var[:]

    @cached_property
    def time_steps(self):
        """List of timesteps, i.e., values of the time dimension, in this file"""
        # This method appears to be very slow -- probably because of all the frequently unnecessary work it does
        # computing the properties 'numeric' and 'datetime' it returns.
        t = self.time_var
        values = self.time_var_values
        return {
            'units': t.units,
            'calendar': t.calendar,
            'numeric': values,
            'datetime': num2date(values, t.units, t.calendar)
        }

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
    def time_range_formatted(self):
        """Format the time range of this file string in YYYY[mm[dd]] format, min and max separated by a dash"""
        return _cmor_formatted_time_range(*self.time_range_as_dates, time_resolution=self.time_resolution)

    @cached_property
    def time_step_size(self):
        """Median of all intervals between successive timesteps in the file"""
        time_var = self.time_var
        match = re.match('(days|hours|minutes|seconds) since.*', time_var.units)
        if match:
            scale = match.groups()[0]
        else:
            raise ValueError("cf_units param must be a string of the form '<time units> since <reference time>'")
        times = self.time_var_values
        median_difference = np.median(np.diff(times))
        return time_to_seconds(median_difference, scale)

    @property
    def time_resolution(self):
        """A standard string that describes the time resolution of the file"""
        #if self.is_multi_year_mean:
        #    return 'other'
        return resolution_standard_name(self.time_step_size)

    class UnifiedMetadata(object):
        """Presents a unified interface to certain global metadata attributes in a CFDataset object.
        Why?
        - A CFDataset can have metadata attributes named according to CMIP3 or CMIP5 standards, depending on the file's
          origin (which is indicated by project_id).
        - We want a common interface, i.e., common names, for a selected set of those differently named attributes.
        - We must avoid shadowing existing properties and methods on a CFDataset (or really, a netCDF4.Dataset) object
          with the unified names we'd like to use for these metadata properties.
        - We'd like to present them as properties instead of as a dict, which has uglier syntax
        How?
        - Create a property called metadata on CFDataset that is an instance of this class.
        """

        def __init__(self, dataset):
            self.dataset = dataset

        _aliases = {
            'institution': {
                'CMIP3': 'institute',
                'CMIP5': 'institute_id',
            },
            'model': {
                'CMIP3': 'source',
                'CMIP5': 'model_id',
            },
            'emissions': {
                'CMIP3': 'experiment_id',
                'CMIP5': 'experiment_id',
            },
            'run': {
                'CMIP3': 'realization',
                'CMIP5': 'parent_experiment_rip',
            },
            'project': {
                'CMIP3': 'project_id',
                'CMIP5': 'project_id',
            },
        }

        def __getattr__(self, alias):
            project_id = self.dataset.project_id
            if project_id not in ['CMIP3', 'CMIP5']:
                raise ValueError("Expected file to have project id of 'CMIP3' or 'CMIP5', found '{}'"
                                 .format(project_id))
            if alias not in self._aliases.keys():
                raise AttributeError("No such unified attribute: '{}'".format(alias))
            attr = self._aliases[alias][project_id]
            try:
                return getattr(self.dataset, attr)
            except:
                raise AttributeError("Expected file to contain attribute '{}' but no such attribute exists"
                                     .format(attr))

    @property
    def metadata(self):
        """Prefix for all aliased (common-name) global metadata attributes"""
        return self.UnifiedMetadata(self)

    @property
    def is_unprocessed_gcm_output(self):
        """True iff the content of the file is unprocessed GCM output."""
        return self.product == 'output'

    @property
    def is_downscaled_output(self):
        """True iff the content of the file is downscaling output."""
        return self.product == 'downscaled output'

    @property
    def is_hydromodel_output(self):
        """True iff the content of the file is hydrological model output of any kind."""
        return self.product == 'hydrological model output'

    @property
    def is_hydromodel_dgcm_output(self):
        """True iff the content of the file is output of a hydrological model forced by downscaled GCM data."""
        return self.is_hydromodel_output and self.forcing_type == 'downscaled gcm'

    @property
    def is_hydromodel_iobs_output(self):
        """True iff the content of the file is output of a hydrological model forced by interpolated observational data."""
        return self.is_hydromodel_output and self.forcing_type == 'gridded observations'

    @property
    def climo_periods(self):
        """List of the standard climatological periods (see function standard_climo_periods)
        that are a subset of the date range in the file."""
        time_var = self.time_var
        s_time, e_time = self.time_range
        return {k: (climo_start_date, climo_end_date)
                for k, (climo_start_date, climo_end_date) in standard_climo_periods(time_var.calendar).items()
                if s_time < date2num(climo_start_date, units=time_var.units, calendar=time_var.calendar) and
                date2num(climo_end_date, units=time_var.units, calendar=time_var.calendar) < e_time
                }

    @property
    def ensemble_member(self):
        """CMIP5 standard ensemble member code for this file"""
        template = 'r{r}i{i}p{p}'
        if self.is_unprocessed_gcm_output:
            return template.format(r=self.realization,
                                   i=self.initialization_method,
                                   p=self.physics_version)
        elif self.is_downscaled_output:
            return template.format(r=self.driving_realization,
                                   i=self.driving_initialization_method,
                                   p=self.driving_physics_version)
        elif self.is_hydromodel_dgcm_output:
            return template.format(r=self.forcing_driving_realization,
                                   i=self.forcing_driving_initialization_method,
                                   p=self.forcing_driving_physics_version)
        elif self.is_hydromodel_iobs_output:
            raise ValueError('ensemble_member has no meaning for a hydrological model forced by observational data')
        else:
            raise ValueError('cannot generate ensemble_member for a file without a recognized type')

    def _cmor_type_filename_components(self, tres_to_mip_table=standard_tres_to_mip_table, **override):
        """Return a dict containing appropriate arguments to function cmor_type_filename (q.v.),
        with content built from this file's metadata.

        :param tres_to_mip_table: (dict) a dict mapping time resolution (as computed by the property
            self.time_resolution) to a valid MIP table name.
        :param override: keyword arguments that can override or extend the base components computed here.
        :return: (dict) as above
        """

        # File content-independent components
        components = {
            'variable': '+'.join(sorted(self.dependent_varnames)),
            'ensemble_member': self.ensemble_member,
        }

        # Components depending on the type of file
        if self.is_multi_year_mean:
            components.update(
                time_range=_cmor_formatted_time_range(dateutil.parser.parse(self.climo_start_time),
                                                      dateutil.parser.parse(self.climo_end_time)),
                frequency=self.frequency
            )
        else:
            # Regarding how the 'mip_table' component is defined here, see the discussion in section titled
            # "MIP table / table_id" in
            # https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data
            # Specifically, we do not consult the value of the attribute table_id because it is too limited for our
            # needs. Instead we map the file's time resolution to a value.
            components.update(
                time_range=self.time_range_formatted,
                mip_table = tres_to_mip_table and tres_to_mip_table.get(self.time_resolution, None)
            )

        if self.is_unprocessed_gcm_output:
            components.update(
                model=self.metadata.model,
                experiment=self.metadata.emissions,
            )
        elif self.is_downscaled_output:
            components.update(
                downscaling_method=self.downscaling_method_id,
                model=self.driving_model_id,
                experiment=_replace_commas(self.driving_experiment_id),
                geo_info=getattr(self, 'domain', None)
            )
        elif self.is_hydromodel_dgcm_output:
            components.update(
                hydromodel_method=_replace_commas(self.hydromodel_method_id),
                model=self.forcing_driving_model_id,
                experiment=_replace_commas(self.forcing_driving_experiment_id),
                geo_info=getattr(self, 'domain', None)
            )
        elif self.is_hydromodel_iobs_output:
            components.update(
                hydromodel_method=_replace_commas(self.hydromodel_method_id),
                obs_dataset_id=self.forcing_obs_dataset_id,
                geo_info=getattr(self, 'domain', None)
            )

        # Override with supplied args
        components.update(**override)

        return components

    @property
    def cmor_filename(self):
        """A CMOR standard filename for this file, based on its metadata contents"""
        return cmor_type_filename(extension='.nc', **self._cmor_type_filename_components())

    @property
    def unique_id(self):
        """A unique id for this file, based on its CMOR filename"""
        unique_id = cmor_type_filename(**self._cmor_type_filename_components())

        dim_axes = set(self.dim_axes_from_names().keys())
        if not (dim_axes <= {'X', 'Y', 'Z', 'T'}):
            unique_id += "_dim" + ''.join(sorted(dim_axes))

        return unique_id.replace('+', '-')  # In original code, but why?

    def climo_output_filename(self, t_start, t_end, variable=None):
        """Return an appropriate CMOR based filename for a climatology output file based on this file as input.

        :param t_start: (datetime.datetime) start date of output file
        :param t_end: (datetime.datetime) end date of output file
        :param variable: (str) name of variable to use in filename; None for all dependent variable names concatenated
        :return: (str) filename
        """
        return cmor_type_filename(extension='.nc', **self._cmor_type_filename_components(
            variable=variable or '+'.join(sorted(self.dependent_varnames)),
            # See section Generating Filenames in
            # https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data
            frequency={
                'daily': 'msaClim',
                'monthly': 'saClim',
                'yearly': 'aClim'
            }.get(self.time_resolution, None),
            tres_to_mip_table=None,
            time_range=_cmor_formatted_time_range(t_start, t_end)
        ))
