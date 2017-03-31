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
