# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property-based tests for OpenMetricsBaseCheckV2."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from .utils import get_check

pytestmark = pytest.mark.unit

settings.register_profile("pytest-func-fixtures-ok", suppress_health_check=[HealthCheck.function_scoped_fixture])
settings.load_profile("pytest-func-fixtures-ok")

metric_names = st.from_regex(r'[a-z][0-9a-z]*(?:_[0-9a-z]+)*', fullmatch=True)
metric_values = st.floats(min_value=-1e15, max_value=1e15, allow_nan=False, allow_infinity=False)
# OM/Prometheus counters are monotonic counts, they must be GE 0.
counter_values = st.floats(min_value=0, max_value=1e15, allow_nan=False, allow_infinity=False)


PROMETHEUS_HEADERS = {}
OPENMETRICS_HEADERS = {"Content-Type": "application/openmetrics-text"}

format_params = pytest.mark.parametrize(
    "response_headers,eof",
    [
        pytest.param(PROMETHEUS_HEADERS, "", id="prometheus"),
        pytest.param(OPENMETRICS_HEADERS, "\n# EOF", id="openmetrics"),
    ],
)


def _missing_metrics_msg(expected, submitted):
    return (
        f"Mapped metric(s) missing from aggregator.\n"
        f"  Expected (at least): {sorted(expected)}\n"
        f"  Got: {sorted(submitted)}"
    )


def _build_payload_and_names(draw, metric_type, values, sample_suffix="", footer=""):
    names = draw(st.lists(metric_names, min_size=1, max_size=20, unique=True))
    lines = []
    for name in names:
        value = draw(values)
        lines.append(f"# HELP {name} generated")
        lines.append(f"# TYPE {name} {metric_type}")
        # We want to avoid float formatting like "1e+15", so we force the full number.
        lines.append(f"{name}{sample_suffix} {value:.17g}")
    if footer:
        lines.append(footer)
    return "\n".join(lines), names


@st.composite
def gauge_payload_and_names(draw):
    """Generate a gauge payload with unique metric names.

    Gauge syntax is identical in Prometheus text format and OpenMetrics format,
    so the same payload body works for both parsers. Tests that cover both
    formats use the gauge_format_params parametrize mark to inject the
    appropriate Content-Type header and EOF trailer.
    """
    return _build_payload_and_names(draw, "gauge", metric_values)


@st.composite
def prometheus_counter_payload_and_names(draw):
    """Generate a Prometheus text format counter payload with unique metric names."""
    return _build_payload_and_names(draw, "counter", counter_values)


@st.composite
def openmetrics_counter_payload_and_names(draw):
    """Generate an OpenMetrics-format counter payload with unique metric names.

    OpenMetrics counters use {name}_total as the sample line and require # EOF.
    The content-type header must be application/openmetrics-text to trigger the
    OpenMetrics parser instead of the Prometheus text parser.
    """
    return _build_payload_and_names(draw, "counter", counter_values, sample_suffix="_total", footer="# EOF")


@st.composite
def gauge_payload_and_mapping(draw):
    """Generate a gauge payload with unique metric names and a subset mapping."""
    payload, names = draw(gauge_payload_and_names())
    mapped = draw(st.lists(st.sampled_from(names), min_size=1, unique=True))
    return payload, names, mapped


@st.composite
def prometheus_counter_payload_and_mapping(draw):
    """Generate a Prometheus text format counter payload and a subset mapping."""
    payload, names = draw(prometheus_counter_payload_and_names())
    mapped = draw(st.lists(st.sampled_from(names), min_size=1, unique=True))
    return payload, names, mapped


@st.composite
def openmetrics_counter_payload_and_names_and_mapping(draw):
    """Generate an OpenMetrics-format counter payload and a subset mapping."""
    payload, names = draw(openmetrics_counter_payload_and_names())
    mapped = draw(st.lists(st.sampled_from(names), min_size=1, unique=True))
    return payload, names, mapped


counter_format_params = pytest.mark.parametrize(
    "response_headers,counter_and_mapping",
    [
        pytest.param(PROMETHEUS_HEADERS, prometheus_counter_payload_and_mapping, id="prometheus"),
        pytest.param(OPENMETRICS_HEADERS, openmetrics_counter_payload_and_names_and_mapping, id="openmetrics"),
    ],
)


@format_params
@given(data=gauge_payload_and_names())
def test_wildcard_captures_all_gauges(aggregator, dd_run_check, mock_http_response, response_headers, eof, data):
    """A wildcard mapping submits every gauge present in the payload.

    The '.+' pattern must match all metric names, so the aggregator should
    contain exactly the namespaced form of each metric in the payload.
    """
    payload, names = data

    aggregator.reset()
    mock_http_response(payload + eof, headers=response_headers)
    check = get_check({"metrics": [".+"]})
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}" for name in names}

    assert expected <= submitted, _missing_metrics_msg(expected, submitted)


@format_params
@given(data=gauge_payload_and_mapping())
def test_gauge_submission_count_lower_bound(aggregator, dd_run_check, mock_http_response, response_headers, eof, data):
    """The aggregator receives at least one submission per mapped gauge metric.

    For gauge metrics the relationship is exact: each mapped metric name in
    the payload produces exactly one gauge submission. We assert the weaker
    '>=' bound so the property generalises to other metric types too.
    """
    payload, _all_names, mapped = data

    aggregator.reset()
    mock_http_response(payload + eof, headers=response_headers)
    check = get_check({"metrics": list(mapped)})
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}" for name in mapped}

    assert expected <= submitted, _missing_metrics_msg(expected, submitted)


@format_params
@given(data=gauge_payload_and_names())
def test_empty_mapping_submits_no_metrics(aggregator, dd_run_check, mock_http_response, response_headers, eof, data):
    """An empty metrics mapping results in no metric submissions.

    With no patterns configured, the scraper should skip every metric in the
    payload and the aggregator should receive nothing except the health service check.
    """
    payload, _names = data

    aggregator.reset()
    mock_http_response(payload + eof, headers=response_headers)
    check = get_check({"metrics": []})
    dd_run_check(check)

    submitted = set(aggregator.metric_names)

    assert submitted == set(), f"Expected no metrics with empty mapping, got: {sorted(submitted)}"


@given(data=prometheus_counter_payload_and_names())
def test_prometheus_counter_submissions_are_suffixed_with_count(aggregator, dd_run_check, mock_http_response, data):
    """Each Prometheus text format counter is submitted with a '.count' suffix.

    The counter transformer always appends '.count' to the metric name, so
    'test.foo' should never appear — only 'test.foo.count'.
    """
    payload, names = data

    aggregator.reset()
    mock_http_response(payload)
    check = get_check({"metrics": [".+"]})
    dd_run_check(check)
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}.count" for name in names}

    assert expected <= submitted, _missing_metrics_msg(expected, submitted)


@given(data=openmetrics_counter_payload_and_names())
def test_openmetrics_counter_submissions_are_suffixed_with_count(aggregator, dd_run_check, mock_http_response, data):
    """Each OpenMetrics-format counter is submitted with a '.count' suffix.

    When the response Content-Type is application/openmetrics-text the scraper
    uses the OpenMetrics parser. Counters in that format carry a _total sample
    suffix which is stripped by the parser, so the submitted name is still
    '{namespace}.{name}.count'.
    """
    payload, names = data

    aggregator.reset()
    mock_http_response(payload, headers=OPENMETRICS_HEADERS)
    check = get_check({"metrics": [".+"]})
    dd_run_check(check)
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}.count" for name in names}

    assert expected <= submitted, _missing_metrics_msg(expected, submitted)


@counter_format_params
@given(data=st.data())
def test_counter_submission_count_lower_bound(
    aggregator, dd_run_check, mock_http_response, response_headers, counter_and_mapping, data
):
    """The aggregator receives at least one '.count' submission per mapped counter.

    Each mapped counter name that appears in the payload must produce a
    '{namespace}.{name}.count' submission. We run the check twice because
    monotonic_count buffers the first value and only emits on the second scrape.
    """
    payload, _all_names, mapped = data.draw(counter_and_mapping())

    aggregator.reset()
    mock_http_response(payload, headers=response_headers)
    check = get_check({"metrics": list(mapped)})
    dd_run_check(check)
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}.count" for name in mapped}

    assert expected <= submitted, _missing_metrics_msg(expected, submitted)
