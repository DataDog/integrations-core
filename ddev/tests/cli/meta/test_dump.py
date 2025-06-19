from collections.abc import Callable

import pytest
from _pytest.mark.structures import ParameterSet
from datadog_checks.base.utils.tagging import GENERIC_TAGS
from datadog_checks.dev.http import MockResponse
from pytest_mock import MockerFixture

from tests.helpers.runner import CliRunner

OPEN_METRICS_CONTENT = """
# HELP go_goroutines Number of currently active goroutines.
# TYPE go_goroutines gauge
go_goroutines 18

# HELP go_heap_objects Number of allocated Go heap objects.
# TYPE go_heap_objects gauge
go_heap_objects 45049

# HELP go_heap_alloc_total_bytes Total bytes allocated in Go heap.
# TYPE go_heap_alloc_total_bytes counter
go_heap_alloc_total_bytes 1.028797712e+09

# HELP go_gc_duration_seconds Summary of Go GC pause duration.
# TYPE go_gc_duration_seconds summary
go_gc_duration_seconds{quantile="0.5"} 3.4001e-05
go_gc_duration_seconds{quantile="0.9"} 0.00062
go_gc_duration_seconds_sum 0.007118091
go_gc_duration_seconds_count 132

# HELP http_client_duration HTTP client request duration.
# TYPE http_client_duration histogram
# Using 'endpoint' as a simplified single tag from the original multi-tag metric.
http_client_duration_bucket{endpoint="/v1/users",le="0.05"} 4
http_client_duration_bucket{endpoint="/v1/users",le="0.1"} 4
http_client_duration_bucket{endpoint="/v1/users",le="0.25"} 4
http_client_duration_bucket{endpoint="/v1/users",le="0.5"} 5
http_client_duration_bucket{endpoint="/v1/users",le="+Inf"} 5
http_client_duration_sum{endpoint="/v1/users"} 0.311033333
http_client_duration_count{endpoint="/v1/users"} 5
"""


@pytest.fixture
def command_output(ddev: CliRunner, mocker: MockerFixture) -> set[str]:
    dynamic_metrics = [
        "# HELP generic_tagged_metric A metric with a generic tag.",
        "# TYPE generic_tagged_metric gauge",
    ]
    for tag in GENERIC_TAGS:
        dynamic_metrics.append(f'generic_tagged_metric{{{tag}="some-value"}} 1')

    content = f"{OPEN_METRICS_CONTENT}\n{'\n'.join(dynamic_metrics)}"

    mock_http = mocker.patch("requests.get")
    mock_http.return_value = MockResponse(content)

    result = ddev("meta", "prom", "dump", "-e", "http://localhost:9090/metrics")
    return set(result.output.splitlines())


def expected_metrics(namespace: str) -> list[ParameterSet]:
    return [
        pytest.param(
            [
                f"{namespace}.go_goroutines",
                f"{namespace}.go_heap_objects",
                f"{namespace}.go_heap_alloc_total_bytes.count",
            ],
            id="gauge",
        ),
        pytest.param(
            [
                f"{namespace}.go_gc_duration_seconds.quantile",
                f"{namespace}.go_gc_duration_seconds.sum",
                f"{namespace}.go_gc_duration_seconds.count",
            ],
            id="summary",
        ),
        pytest.param(
            [
                f"{namespace}.http_client_duration.bucket",
                f"{namespace}.http_client_duration.sum",
                f"{namespace}.http_client_duration.count",
            ],
            id="histogram",
        ),
        pytest.param([f"{namespace}.generic_tagged_metric"], id="generic_tags"),
    ]


@pytest.mark.parametrize("metric_names", expected_metrics("test"))
def test_dump(command_output: set[str], metric_names: list[str]):
    assert set(metric_names) <= command_output


def test_dump_with_errors(ddev: CliRunner, mock_http_response: Callable):
    mock_http_response(status_code=500)
    result = ddev("meta", "prom", "dump", "-e", "http://localhost:9090/metrics")

    assert "500 Server Error" in result.output
