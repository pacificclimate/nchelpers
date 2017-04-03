from pytest import fixture
from pkg_resources import resource_filename
from nchelpers import CFDataset


@fixture
def tiny_dataset(request):
    """Return a 'tiny' test dataset, based on request param.

    request.param: (str) selects the test file to be returned
    returns: (nchelpers.CFDataset) test file as a CFDataset object

    This fixture should be invoked with indirection.
    """
    filename = 'data/tiny_{}.nc'.format(request.param)
    return CFDataset(resource_filename('nchelpers', filename))


@fixture
def indir_dataset(tmpdir):
    fp = tmpdir.join('fake.nc')
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
