# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev.testing import requires_py3

from .utils import get_check

pytestmark = [requires_py3]


test_use_process_start_time_data = """\
# HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
# TYPE go_memstats_alloc_bytes_total counter
go_memstats_alloc_bytes_total 9.339544592e+09
# HELP skydns_skydns_dns_request_duration_seconds Histogram of the time (in seconds) each request took to resolve.
# TYPE skydns_skydns_dns_request_duration_seconds histogram
skydns_skydns_dns_request_duration_seconds_bucket{system="auth",le="10"} 1.359194e+06
skydns_skydns_dns_request_duration_seconds_bucket{system="auth",le="+Inf"} 1.359194e+06
skydns_skydns_dns_request_duration_seconds_sum{system="auth"} 44.31446715499896
skydns_skydns_dns_request_duration_seconds_count{system="auth"} 1.359194e+06
# HELP go_gc_duration_seconds A summary of the GC invocation durations.
# TYPE go_gc_duration_seconds summary
go_gc_duration_seconds{quantile="0"} 0.00036825700000000004
go_gc_duration_seconds{quantile="0.25"} 0.00041007200000000004
go_gc_duration_seconds{quantile="0.5"} 0.00043824300000000005
go_gc_duration_seconds{quantile="0.75"} 0.00048369000000000005
go_gc_duration_seconds{quantile="1"} 0.0025860830000000003
go_gc_duration_seconds_sum 1.154763349
go_gc_duration_seconds_count 2351
"""


def _make_test_data(process_start_time):
    test_data = test_use_process_start_time_data
    if process_start_time:
        if not test_data.endswith('\n'):
            test_data += '\n'
        test_data += "# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.\n"
        test_data += "# TYPE process_start_time_seconds gauge\n"
        for seq, pst in enumerate(process_start_time):
            label = '{pid="%d"}' % (seq,) if len(process_start_time) > 1 else ""
            test_data += "process_start_time_seconds%s %f\n" % (
                label,
                pst,
            )
    return test_data


@pytest.mark.parametrize(
    'with_buckets, use_process_start_time, expect_first_flush, agent_start_time, process_start_time',
    [
        (False, False, False, None, None),
        (False, True, True, 10, [20]),
        (False, True, False, 20, [10]),
        (False, True, False, 10, []),
        (False, True, True, 10, [20, 30, 40]),
        (False, True, False, 20, [10, 30, 40]),
        (True, False, False, None, None),
        (True, True, True, 10, [20]),
        (True, True, False, 20, [10]),
        (True, True, False, 10, []),
        (True, True, True, 10, [20, 30, 40]),
        (True, True, False, 20, [10, 30, 40]),
    ],
    ids=[
        "disabled",
        "enabled, agent is older",
        "enabled, agent is newer",
        "enabled, metric n/a",
        "enabled, many metrics, all newer",
        "enabled, many metrics, some newer",
        "with buckets, disabled",
        "with buckets, enabled, agent is older",
        "with buckets, enabled, agent is newer",
        "with buckets, enabled, metric n/a",
        "with buckets, enabled, many metrics, all newer",
        "with buckets, enabled, many metrics, some newer",
    ],
)
def test_first_scrape_handler(
    aggregator,
    dd_run_check,
    mock_http_response,
    with_buckets,
    use_process_start_time,
    expect_first_flush,
    agent_start_time,
    process_start_time,
):
    mock_http_response(_make_test_data(process_start_time))

    check = get_check(
        {
            'metrics': ['.*'],
            'use_process_start_time': use_process_start_time,
            'histogram_buckets_as_distributions': with_buckets,
        }
    )

    datadog_agent.set_process_start_time(agent_start_time)

    for _ in range(0, 5):
        aggregator.reset()
        dd_run_check(check)

        aggregator.assert_metric(
            'test.go_memstats_alloc_bytes.count',
            metric_type=aggregator.MONOTONIC_COUNT,
            count=1,
            flush_first_value=expect_first_flush,
        )
        aggregator.assert_metric(
            'test.go_gc_duration_seconds.count',
            metric_type=aggregator.MONOTONIC_COUNT,
            count=1,
            flush_first_value=expect_first_flush,
        )

        if with_buckets:
            aggregator.assert_histogram_bucket(
                'test.skydns_skydns_dns_request_duration_seconds',
                None,
                None,
                None,
                True,
                None,
                None,
                count=2,
                flush_first_value=expect_first_flush,
            )
        else:
            aggregator.assert_metric(
                'test.skydns_skydns_dns_request_duration_seconds.count',
                metric_type=aggregator.MONOTONIC_COUNT,
                count=1,
                flush_first_value=expect_first_flush,
            )
            aggregator.assert_metric(
                'test.skydns_skydns_dns_request_duration_seconds.sum',
                metric_type=aggregator.MONOTONIC_COUNT,
                count=1,
                flush_first_value=expect_first_flush,
            )
            aggregator.assert_metric(
                'test.skydns_skydns_dns_request_duration_seconds.bucket',
                metric_type=aggregator.MONOTONIC_COUNT,
                count=1,
                flush_first_value=expect_first_flush,
            )

        expect_first_flush = True
