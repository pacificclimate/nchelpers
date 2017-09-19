from datetime import datetime
from pytest import mark
from nchelpers import cmor_type_filename, standard_climo_periods


keys = '''
    variable
    mip_table
    downscaling_method
    model
    experiment
    ensemble_member
    time_range
    geo_info
'''.split()
values = [str(v) for v in range(len(keys))]


@mark.parametrize('component_values, expected', [
    (dict(zip(keys, values)), '_'.join(values)),
    ({'variable': 'var', 'ensemble_member': 'em'}, 'var_em'),
    ({'variable': 'var', 'ensemble_member': 'em', 'irrelevant': 'i'}, 'var_em'),
])
def test_cmor_type_filename(component_values, expected):
    assert cmor_type_filename(**component_values) == expected


@mark.parametrize('calendar, key, start_date, end_date', [
    ('standard', '6190', datetime(1961, 1, 1), datetime(1990, 12, 31)),
    ('360_day', '2020', datetime(2010, 1, 1), datetime(2039, 12, 30)),
])
def test_standard_climo_periods(calendar, key, start_date, end_date):
    assert standard_climo_periods(calendar)[key] == (start_date, end_date)


