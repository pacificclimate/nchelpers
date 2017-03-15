from pytest import mark
from nchelpers.date_utils import resolution_standard_name


@mark.parametrize('arg, result', [
    (60, '1-minute'),
    (2678400, 'monthly'),
    (999, 'other')
])
def test_resolution_standard_name(arg, result):
    assert resolution_standard_name(arg) == result