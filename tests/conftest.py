import pytest
from pytest import fixture, mark
from pkg_resources import resource_filename
from nchelpers import CFDataset


@fixture
def tiny_dataset(request):
    filename = 'data/tiny_{}.nc'.format(request.param)
    return CFDataset(resource_filename('nchelpers', filename))
