import sys
import os

from pytest import fixture
from pkg_resources import resource_filename
from nchelpers import CFDataset

# Add helpers directory to pythonpath: See https://stackoverflow.com/a/33515264
sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))

from nc_file_specs import create_fake_nc_dataset


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
