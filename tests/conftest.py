import pytest
from pytest import fixture, mark
from pkg_resources import resource_filename
from nchelpers import CFDataset


@fixture
def tiny_gcm():
    return CFDataset(resource_filename('nchelpers', 'data/tiny_gcm.nc'))
