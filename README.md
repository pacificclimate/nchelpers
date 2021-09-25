# nchelpers

![Python CI](https://github.com/pacificclimate/nchelpers/workflows/Python%20CI/badge.svg)
![Pypi Publishing](https://github.com/pacificclimate/nchelpers/workflows/Pypi%20Publishing/badge.svg)

This module contains the `CFDataset` class, which extends the `netcdf4.Dataset`
class to provide additional properties, memory-efficient data access, and improved
error handling for netCDF files that comply with the [CF Metadata Conventions](http://cfconventions.org/)
and the PCIC metadata conventions that extend them.

It supports several PCIC tools that work with netCDF files that adhere to the
CF and PCIC metadata conventions. The class provides several properties that
specify information about a file's contents and metadata and can be used to
guide data processing. It does not provide any new tools to directly
modify netCDF files, but all file-modifying procedures in the netcdf4.Dataset
class are still available.

## Data chunking
`iteration.py` contains generators for iterating over a netCDF file and loading
on chunk at a time so that enormous files can be read without a `MemoryError`.

## PCIC Metadata Model
PCIC has a [process-oriented metadata model](https://pcic.uvic.ca/confluence/display/CSG/PCIC+metadata+standard+for+downscaled+data+and+hydrology+modelling+data).

Data originates as either model output (simulated by a Global Climate Model
or Regional Climate Model) or observations (measured directly in some fashion).

The data can then be used as input to one or more further processes. Each
new process preserves all the metadata describing the data origin and previous
process. When a new dataset B is generated from a process that uses dataset
A as input, all metadata attributes describing A's generation will be
present in B, prepended with a prefix that refers to A's role in generating
B.

For example, suppose you have a model output dataset A, with a metadata attribute
giving the name of the generating model, `example_model`.

A has the metadata attribute `model_id` with the value `example_model`.

If A is used as input to a downscaling process, the output dataset B will
have an attribute called `GCM__model_id` with the value `example_model`. A
is used as the GCM (global climate model) intput to the downscaling process,
so the prefix `GCM` is used.

If B is further used as input to a hydrological modeling process, the output
dataset C will have an attribute called `downscaling__GCM__model_id` with the
value `example_model`. B is a downscaled dataset used as forcing data for the
hydrological model, so its attributes are prepended with `downscaling`, including
the attributes it inherited from A to show its own inputs.

The metadata preserves the entire chain of processes followed
to create any given dataset so that its origin can always be traced and
recreated.

The functions in this module handle determining what sort of data a particular
netCDF is, which processes were used to generate it, validating that required
metadata is present, and navigating the metadata "tree" to find desired metadata.

## Data Supported
Most of the time, this module will take care of the low level details related
to handling various types of datasets. Data is usually cubes with a latitude,
longitude, and time dimension. While it may have different origins and different
origin- or process- specific metadata, the module should seamlessly traverse the
metadata formats of various different data types and provide a unified interface
to accessing needed metadata.

### Supported Data Origins

#### Model Output
Model output is the majority of netCDF data used by PCIC. Model output data has
latitude, longitude, and time dimensions and metadata attributes specifying the
model, scenario, and run used to generate the data.

Model data that has not been further processed has the `is_unprocessed_gcm_output`
property of `True`. Data that is either model output or was created by processes
that used model output has the `is_gcm_derivative` property of `True`.

#### Observations
Observation data is historical data that is derived from real world observations
and then extrapolated to cover geographic or chronological gaps by an algorithmic
process. (This module and the netCDF file format are not well suited for handling
sparse, non-gridded observation data.)

Note that, confusingly, observation data usually *does* have a `model_id` attribute:
typically this is the name of the algorithm used to extrapolate measurements to
cover an entire grid. It is not a Global Climate Model, though, and simulation
attributes relevant to GCMs, like `experiment`, will not be present.

Observational data values usually, but not always, takes the form of a cube
with lat, lon, and time dimensions, similar to model output.

Observation data has the `is_gridded_obs` property of `True`.

### Data-generating Processes

#### Downscaling
This process produces data with a higher spatial resolution, but otherwise
similar to the input data. It is only run on model output data; observation data
is already downscaled by the extrapolation process used to create it.

It will have the property `is_downscaled_output` of `True` and metadata
specifying the downscaling algorithm (typically either BCCAQ, PRISM, or both).

#### Climdex calculation
This process takes model output and calculates [various derived statistics](https://www.climdex.org/)
about it. The output data will have the same dimensions as the input data
(lat, lon, time), but a different variable.

All climdex datasets have the property `is_climdex_output` set to `True`, and
one of `is_climdex_gcm_output` or `is_climdex_ds_gcm_output` will be `True`
as well, depending on whether the input dataset was downscaled or not.

#### Hydrological Modeling
Unlike Downscaling or Climdex calculation, hydrological modeling produces
data that is *not* a cube with lat, lon, and time dimensions, and applications
that use this module to work with streamflow data will definitely need to
check whether the data is streamflow and handle it seperately if so.

The hydrological model takes a downscaled model output or gridded
observation dataset as input, and outputs streamflow at one particular
location. The resulting dataset has a `True` `is_streamflow_model_output`
property.

### Supported Data Shapes

#### Raster Timeseries
The most common type of PCIC data is a raster timeseries. Data is stored in one or
more data cubes with latitude, longitude, and time dimensions. This is the default and
doesn't usually require explicit handling, but can be checked for if needed.

The `sampling_geometry` property will have the value `gridded` and the `time_invariant`
property will be `False`.

#### Climatologies
A subset of raster timeseries; a climatology contains values that are averaged over a
multi-year time period, typically 30 years. Climatologies may contain annual data
(one timestamp), seasonal data (four timestamps), monthly data (12 timestamps) or
some combination of those time resolutions. For example, a January timestamp would
represent the average of all Januaries occuring over the time period.
It has a `climatology_bounds_value` property specifying the period over which each
value is averaged.

A climatology will return `True` on the `is_multi_year` property.

#### Discrete Structured Geometries
Discrete Structured Geometries have a time series of data associated with
one or more specific points (like measuring stations), but not a full grid.
The collection of individual points is the "instance" dimension; data is
stored in a rectanlge with dimensions corresponding to "instance" and "time".
It has an `instance_dim` property and an `id_instance_var` property in
accordance with the CF Standards for DSG data. The list of instance variables
is available in the `coordinate_vars` property.

A discrete structured geometry has a value other than `gridded` as its
`sampling_geometry` property.

#### Time Invariant Data
Time invariant data is gridded data that describes characteristics that do not change
over time, like elevation or soil type. Time Invariant Data is always observations;
climate model output necessarily has a time component. It lacks a time dimension.

A time-invariant dataset returns `True` on the `is_time_invariant` property.
Most time-related properties will throw errors if accessed on a time-invariant
dataset.

## Building and Testing

While this module is usually imported to some other project, it can be built and
tested on its own for debugging or development.

```
git clone http://github.com/pacificclimate/nchelpers
cd nchelpers
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.pacificclimate.org/simple/
pip install .
```

Tests can be run with `pytest`.
