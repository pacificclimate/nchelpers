import sys
import os

from pytest import fixture
from pkg_resources import resource_filename
from nchelpers import CFDataset

from .helpers.nc_file_specs import create_fake_nc_dataset


@fixture
def cwd():
    return os.getcwd()


@fixture
def raw_dataset(request, cwd):
    """Return a dataset, based on request param.

    request.param: (str) filepath to data file to be returned
    returns: (nchelpers.CFDataset) test file as a CFDataset object

    This fixture should be invoked with indirection.

    This fixture should be used only for testing filepath manipulation.
    For other purposes, use ``dataset`` or ``tiny_dataset``, which use
    ``resource_filename`` to locate the dataset.
    """
    return CFDataset(request.param.format(cwd=cwd))


@fixture
def dataset(request):
    """Return a test dataset, based on request param.

    request.param: (str) selects the test file to be returned
    returns: (nchelpers.CFDataset) test file as a CFDataset object

    This fixture should be invoked with indirection.

    If you're testing with tiny_ datasets, use the fixture `tiny_dataset`.
    """
    filename = 'data/{}.nc'.format(request.param)
    return CFDataset(resource_filename('nchelpers', filename))


@fixture
def tiny_dataset(request):
    """Return a 'tiny' test dataset, based on request param.

    request.param: (str) selects the test file to be returned
    returns: (nchelpers.CFDataset) test file as a CFDataset object

    This fixture should be invoked with indirection.
    """
    filename = 'data/tiny_{}.nc'.format(request.param)
    return CFDataset(resource_filename('nchelpers', filename))


@fixture(scope='function')
def temp_nc(tmpdir_factory):
    return str(tmpdir_factory.mktemp('temp').join('file.nc'))


@fixture
def fake_nc_dataset(request, temp_nc):
    create_fake_nc_dataset(temp_nc, request.param)
    return temp_nc


@fixture
def indir_dataset(tmpdir):
    """Yield an otherwise empty netCDF file containing some indirected attributes for testing."""
    fp = tmpdir.join('indirect_test.nc')
    with CFDataset(fp, mode='w') as cf:
        # ordinary values
        cf.one = 1
        cf.two = 2
        # indirect values
        cf.uno = '@one'  # one level
        cf.un = '@uno'   # two levels
        # circular indirection
        cf.foo = '@bar'
        cf.bar = '@foo'
        # indirect without corresponding property
        cf.baz = '@qux'
        yield cf
