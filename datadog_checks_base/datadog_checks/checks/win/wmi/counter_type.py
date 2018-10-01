# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.checks.win.wmi.counter_type import (
    _counter_type_calculators,
    UndefinedCalculator,
    calculator,
    get_calculator,
    get_raw,
    calculate_perf_counter_rawcount,
    calculate_perf_counter_large_rawcount,
    calculate_perf_100nsec_timer,
    calculate_perf_counter_bulk_count,
    calculate_perf_counter_counter,
    calculate_perf_average_timer,
    calculate_perf_counter_100ns_queuelen_type,
)
