from setuptools import setup


__version__ = (0, 0, 1)


setup(
    name="nchelpers",
    description="Helper classes and methods for Climate and Forecast NetCDF datasets",
    keywords="NetCDF climate forecast",
    packages=['nchelpers'],
    version='.'.join(str(d) for d in __version__),
    url="http://www.pacificclimate.org/",
    author="Rod Glover",
    author_email="rglover@uvic.ca",
    zip_safe=True,
    install_requires = ['netCDF4', 'cached-property'],
    package_data = {'nchelpers': [
        'data/tiny_gcm.nc',
        'data/tiny_downscaled.nc',
        'data/tiny_hydromodel_gcm.nc',
    ]},
    include_package_data = True,
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Console',
                 'Intended Audience :: Developers',
                 'Intended Audience :: Science/Research',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Topic :: Scientific/Engineering',
                 'Topic :: Database',
                 'Topic :: Software Development :: Libraries :: Python Modules'
                 ]

)