News / Release Notes
====================

3.0.0
-----

*Release Date: 18-Sep-2017*

* Migrate time-bounds functions from ``modelmeta``. These now support ``modelmeta`` and provide more
  robust internal support for time-bounds based functions like ``unique_id`` and ``cmor_filename``.
* Add optional argument to ``CFDataset.dependent_varnames`` to specify the dimesions on which
  the returned variables must be dependent. Is a breaking change since this changes ``dependent_varnames``
  from a property to a method.


2.1.0
-----

*Release Date: 23-Aug-2017*

* Add path-conversion option to ``CFDataset.filepath``.
  See [Issue 26](https://github.com/pacificclimate/nchelpers/issues/26)

2.0.0
-----

*Release Date: 03-Aug-2017*

* Because of the change to exception-raising noted below, this is technically a breaking change.
  However, all unit tests of all clients of this package have been run against this new version
  without failure.
* Raises package-defined exceptions instead of generic exceptions. This corrects problems caused by
  ``netCDF4`` capturing and reraising ``AttributeError``s containing a generic error message and
  lacking stack context of the original error.
* Fixes a bug in which time units were attempted to be taken from a *time bounds* variable and not
  from the time variable proper. This affected the identification of climatological bounds and of
  files containing multi-year means released in ver 1.1.0.

1.1.0
-----

*Release Date: 18-Jul-2017*

* Makes identification of climatological bounds and identification of files containing
  multi-year means more flexible, i.e., accommodates files that do not comply with
  PCIC and CF metadata standards but which can be interpreted with the application of
  some reasonable heuristics.
  * Adds 'strict_metadata' flag to CFDataset to determine whether strict metadata standards
    are applied, or heuristics. Default non-strict.
  * Climatology bounds heuristics:
    * Look for variables with likely names, in some cases with addtional check for
      plausible bounds values
    * Allow 'bounds' attribute instead of 'climatology' attribute, check plausible
      bounds values.
    * For details, see https://github.com/pacificclimate/nchelpers/issues/22
  * Multi-year mean heuristics:
    * Climatology bounds identified in non-strict mode.
    * Time variable with suspicious length and with plausible values.
    * For details, see https://github.com/pacificclimate/nchelpers/issues/22
* Classifies time resolution more flexibly:
  * Returns 'seasonal' for time periods between 88 and 92 days. (new - breaking change)
  * Returns 'monthly' for time periods between 28 and 31 days. (extended)
  * Returns 'yearly' for time periods of 360, 365, and 366 days. (extended)


1.0.5
-----

*Release Date: 27-Jun-2017*

* Adds 'gcm' property, which automatically adds appropriate prefix to dataset attribute name
  to access the attributes describing the original GCM input data used by the program that
  generated the file.
* Uses 'gcm' auto-prefix properties for 'metadata' properties so that they are valid across
  all PCIC standard data files (not just GCM output).
* Makes code entirely PEP8 compliant.

1.0.4
-----

*Release Date: 12-Jun-2017*

* Fixes first_MiB_md5sum attribute of CFDataset to be hex rather than binary
* More updates in support of modelmeta index_netcdf.py
  * Adds 'depth' to set of recognized Z axis dimensions
  * Adds md5 attribute for a digest of the *full* file
  * Adds to_datetime to the date utils
  * Adds method var_range()
  * Adds method var_bounds_and_values()


1.0.3
-----

*Release Date: 06-Jun-2017*

* Adds undeclared dependency to setup.py (GH #17)


1.0.2
-----

*Release Date: 05-Jun-2017*

* Improves detection of GCM ensemble member attributes
* Improves the handling and detection of dimension attributes
* Reduces the size of testing files in the repo


1.0.1
-----

*Release Date: 11-Apr-2017*

* Adds support for "indirect values" in the CFDataset class
