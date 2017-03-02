import hashlib
import re

from netCDF4 import Dataset, num2date, date2num
import numpy as np
from nchelpers.util import resolution_standard_name, time_to_seconds, standard_climo_periods


class CFDataset(Dataset):
    """Represents a CF (climate and forecast) dataset stored in a NetCDF file.
    Methods on this class expose metadata that is expected to be found in such files,
    and values computed from that metadata.
    
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
    get_important_varnames -> important_varnames, dependent_varnames
    """

    def __init__(self, *args, **kwargs):
        super(CFDataset, self).__init__(*args, **kwargs)

    @property
    def first_MiB_md5sum(self):
        """MD5 digest of first MiB of this file"""
        m = hashlib.md5()
        with open(self.filepath(), 'rb') as f:
            m.update(f.read(2**20))
        return m.digest()

    @property
    def important_varnames(self):
        """A list of the primary (dependent) variables in this file.

        Many variables in a NetCDF file describe the *structure* of the data and aren't necessarily the
        values that we actually care about. For example a file with temperature data also has to include
        latitude/longitude variables, a time variable, and possibly bounds variables for each of the dimensions.
        These dimensions and bounds are independent variables.

        This function filters out the names of all independent variables and just gives you the "important" (dependent)
        variable names.
        """
        variables = set(self.variables.keys())
        dimensions = set(self.dimensions.keys())
        return [v for v in variables - dimensions if 'bnds' not in v]
    # Define an alias with a more explantory name
    dependent_varnames = important_varnames

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
        axes = self.dim_axes()
        if 'T' in axes:
            time_axis = axes['T']
        else:
            return None

        # TODO: Do we really mean 'climatology' in self.variables[time_axis].ncattrs()? If so, use that. This looks
        # imprecise and hard to understand
        if 'climatology' in self.variables[time_axis]:
            return self.variables[time_axis].climatology
        else:
            return None

    @property
    def is_multi_year_mean(self):
        """True if the metadata indicates that the data consists of a multi-year mean"""
        # TODO: Is it really true that every data file that consists of a multi-year mean actually (should) contain a
        # time dimension with attribute 'climatology'? Or is there a better condition, perhaps based on cell_method?
        return bool(self.climatology_bounds_var_name)

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

    @property
    def time_steps(self):
        """List of timesteps, i.e., values of the time dimension, in this file"""
        # This method appears to be very slow -- probably because of all the frequently unnecessary work it does
        # computing the properties 'numeric' and 'datetime' it returns.
        t = self.time_var
        return {
            'units': t.units,
            'calendar': t.calendar,
            'numeric': t[:],
            'datetime': num2date(t[:], t.units, t.calendar)
        }

    @property
    def time_range(self):
        """Minimum and maximum timesteps in the file"""
        # TODO: Must we really compute min and max of t? Can time variables really be non-monotonic?
        # t = self.time_steps['numeric']
        # return np.min(t), np.max(t)
        # Let's do this instead of relying on the very slow computation of self.time_steps
        t = self.time_var
        return t[0], t[-1]

    # TODO: Is this property useful anywhere except in unique_id? If not, inline it.
    @property
    def time_range_formatted(self):
        """Format the time range as string in YYYY[mm[dd]] format, min and max separated by a dash"""
        format = {'yearly': '%Y', 'monthly': '%Y%m', 'daily': '%Y%m%d'}.get(self.time_resolution, None)
        if not format:
            raise ValueError("Cannot format a time range with resolution '{}' (only yearly, monthly or daily)"
                             .format(self.time_resolution))
        t_min, t_max = num2date(self.time_range, self.time_steps['units'], self.time_steps['calendar'])
        return '{}-{}'.format(t_min.strftime(format), t_max.strftime(format))

    @property
    def time_step_size(self):
        """Median of all intervals between successive timesteps in the file"""
        time_var = self.time_var
        match = re.match('(days|hours|minutes|seconds) since.*', time_var.units)
        if match:
            scale = match.groups()[0]
        else:
            raise ValueError("cf_units param must be a string of the form '<time units> since <reference time>'")
        times = time_var[:]
        median_difference = np.median(np.diff(times))
        return time_to_seconds(median_difference, scale)

    @property
    def time_resolution(self):
        """A standard string that describes the time resolution of the file"""
        #if self.is_multi_year_mean:
        #    return 'other'
        return resolution_standard_name(self.time_step_size)

    # TODO: Remove when all the juice has been squeezed
    # def _get_file_metadata(nc, map_):
    #     missing = []
    #     required = map_.keys()
    #     for key in required:
    #         if not hasattr(nc, key):
    #             missing.append(key)
    #     if missing:
    #         raise ValueError(required_nc_attributes_msg.format(required, nc.filepath(), missing))
    #
    #     return {
    #         to_: getattr(nc, from_)
    #         for from_, to_ in map_.items()
    #         }
    #
    # def file_metadata(nc):
    #     """Return important global attributes from this file"""
    #     if self.project_id == 'CMIP5':
    #         meta = _get_file_metadata(nc, global_to_res_map_cmip5)
    #     else:
    #         meta = _get_file_metadata(nc, global_to_res_map_cmip3)
    #
    #     # Which variable(s) does this file contain?
    #     meta['var'] = '+'.join(get_important_varnames(nc))  # just do the computation where needed
    #
    #     # Compute time metadata from the time value
    #     time = get_timeseries(nc)
    #     meta['tres'] = get_time_resolution(time['numeric'], time['units'])  # == self.time_resolution
    #     tmin, tmax = get_time_range(nc)
    #     tmin, tmax = num2date([tmin, tmax], time['units'], time['calendar'])
    #     meta['trange'] = format_time_range(tmin, tmax, meta['tres'])  # == self.time_range_formatted
    #
    #     return meta

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
        # TODO: Make this a singleton

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
    def unique_id(self):
        """A metadata-based unique id for this file"""
        dim_axes = set(self.dim_axes_from_names().keys())
        if dim_axes <= {'X', 'Y', 'Z', 'T'}:
            axes = ''
        else:
            axes = "_dim" + ''.join(sorted(dim_axes))
        return '{vars}_{tres}_{model}_{emissions}_{run}_{trange}{axes}'.format(
            vars='-'.join(self.dependent_varnames),
            tres=self.time_resolution,
            model=self.metadata.model,
            emissions=self.metadata.emissions,
            run=self.metadata.run,
            trange=self.time_range_formatted,
            axes=axes,
        )\
            .replace('+', '-')

    @property
    def is_unprocessed_model_output(self):
        """True iff the content of the file is unprocessed model output.
        This allows us to discern between raw amd downscaled model output, for example"""
        try:
            self.metadata.model
        except AttributeError:
            return False
        else:
            return True

    @property
    def climo_periods(self):
        """List of those standard climatological periods (see util.standard_climo_periods) that are a subset of the
        date range in the file."""
        time_var = self.time_var
        s_time, e_time = self.time_range
        return dict([(k, v) for k, v in standard_climo_periods(time_var.calendar).items()
                     if date2num(v[0], units=time_var.units, calendar=time_var.calendar) > s_time and
                     date2num(v[1], units=time_var.units, calendar=time_var.calendar) < e_time])
