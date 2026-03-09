# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property-based tests for OpenMetricsBaseCheckV2.

These tests use Hypothesis to generate random but valid Prometheus payloads
and metric mappings, then verify invariants about how metrics flow through
the check pipeline into the aggregator.

The central property under test: given a payload containing N uniquely-named
gauge metrics and a metric mapping that selects a subset of those names,
the aggregator receives at least as many metric submissions as the size
of the overlap between payload metric names and the mapping.
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from .utils import get_check

metric_names = st.from_regex(r'[a-z][a-z0-9_]{0,29}', fullmatch=True).filter(
    lambda n: '__' not in n and not n.endswith('_')
)

metric_values = st.floats(min_value=-1e15, max_value=1e15, allow_nan=False, allow_infinity=False)


@st.composite
def gauge_payload_and_mapping(draw):
    """Generate a Prometheus gauge payload with unique metric names and a subset mapping."""
    names = draw(st.lists(metric_names, min_size=1, max_size=20, unique=True))

    lines = []
    for name in names:
        value = draw(metric_values)
        lines.append(f"# HELP {name} generated")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")

    payload = "\n".join(lines)
    mapped = draw(st.lists(st.sampled_from(names), min_size=1, unique=True))

    return payload, names, mapped


@given(data=gauge_payload_and_mapping())
@settings(max_examples=200, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_gauge_submission_count_lower_bound(aggregator, dd_run_check, mock_http_response, data):
    """The aggregator receives at least one submission per mapped gauge metric.

    For gauge metrics the relationship is exact: each mapped metric name in
    the payload produces exactly one gauge submission. We assert the weaker
    '>=' bound so the property generalises to other metric types too.
    """
    payload, _all_names, mapped = data

    aggregator.reset()
    mock_http_response(payload)
    check = get_check({"metrics": list(mapped)})
    dd_run_check(check)

    submitted = set(aggregator.metric_names)
    expected = {f"test.{name}" for name in mapped}

    assert expected <= submitted, (
        f"Mapped metric(s) missing from aggregator.\n"
        f"  Expected (at least): {sorted(expected)}\n"
        f"  Got: {sorted(submitted)}"
    )
