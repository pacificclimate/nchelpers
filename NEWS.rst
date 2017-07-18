News / Release Notes
====================

1.0.6
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
