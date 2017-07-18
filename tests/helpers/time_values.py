"""
Helper module defining "suspicious" time values for testing `is_multi_year_mean`.
See that function for definition of "suspicious".
"""
from datetime import datetime
from netCDF4 import date2num

units = 'days since 1850-01-01 00:00:00'
calendar = '365_day'

year = 2000


def d2n(month_days):
    return date2num([datetime(year, month, day) for month, day in month_days], units, calendar)


suspicious_yearly_time_values = d2n([(7, 2)]).tolist()
suspicious_seasonal_time_values = d2n([(1, 15), (4, 16), (7, 17), (10, 15)]).tolist()
suspicious_monthly_time_values = d2n([(1, 14), (2, 15), (3, 16)] + [(m, 15) for m in range(4, 13)]).tolist()

suspicious_time_values = [
    suspicious_yearly_time_values,
    suspicious_seasonal_time_values,
    suspicious_monthly_time_values,
    suspicious_seasonal_time_values + suspicious_yearly_time_values,
    suspicious_monthly_time_values + suspicious_yearly_time_values,
    suspicious_monthly_time_values + suspicious_seasonal_time_values,
    suspicious_monthly_time_values + suspicious_seasonal_time_values + suspicious_yearly_time_values,
]


non_suspicious_yearly_time_values = d2n([(1, 1)]).tolist()
non_suspicious_seasonal_time_values = d2n([(1, 1), (4, 16), (7, 17), (10, 15)]).tolist()
non_suspicious_monthly_time_values = d2n([(1, 1), (2, 15), (3, 16)] + [(m, 15) for m in range(4, 13)]).tolist()
non_suspicious_number_of_values = d2n([(1, 15), (2, 15)]).tolist()

non_suspicious_time_values = [
    non_suspicious_yearly_time_values,
    non_suspicious_seasonal_time_values,
    non_suspicious_monthly_time_values,
    non_suspicious_seasonal_time_values + non_suspicious_yearly_time_values,
    non_suspicious_monthly_time_values + non_suspicious_yearly_time_values,
    non_suspicious_monthly_time_values + non_suspicious_seasonal_time_values,
    non_suspicious_monthly_time_values + non_suspicious_seasonal_time_values + non_suspicious_yearly_time_values,
    non_suspicious_number_of_values
]