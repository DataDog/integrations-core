# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Coverage for OpenMetrics histogram buckets whose smallest threshold is zero.

The E2E test below runs the full daemon pipeline: a real Agent (with the local
base package installed via ``ddev env test --base``) scrapes a phase-controlled
exporter, decumulates the buckets, submits them through the Python/Go bridge,
interpolates them into DDSketch sketches, serializes and forwards them to a
local fake intake. The test then asserts on the parsed payloads the fake
intake received.

The primary regression: when every new observation is zero, the whole delta of
the ``le="0"`` bucket must reach the intake as a point-mass sketch at zero. A
regression that maps the smallest zero bucket to a ``-Inf`` lower bound makes
the Go aggregation silently discard that bucket, so its count vanishes from
the distribution while ``.count``/``.sum`` still include it; this test fails
with a missing sketch in that case.

Histogram families (see ``compose/zero-buckets/exporter.py``):

- ``e2e_zero_all_zero_seconds``: 3 new zero observations (the core case).
- ``e2e_zero_big_count_seconds``: 65,600 new zero observations, crossing 65,535.
- ``e2e_zero_mixed_seconds``: 3 new observations in ``(0, 5]``; the zero bucket
  does not advance and must not produce a zero-width bucket sketch.
- ``e2e_zero_negative_seconds``: explicit negative thresholds; the zero bucket
  keeps its existing ``(prev_le, 0]`` decumulation.

Both daemon instances (plain distributions and the
``collect_counters_with_distributions`` variant) are asserted.
"""

import json
import math

import pytest

from .zero_buckets import (
    ALL_ZERO,
    ALL_ZERO_DELTA,
    BIG,
    BIG_DELTA,
    COUNTERS_NAMESPACE,
    MIXED,
    MIXED_BUCKET_TAGS,
    NEGATIVE,
    NEGATIVE_BUCKET_TAGS,
    PLAIN_NAMESPACE,
    POSITIVE_DELTA,
    POSITIVE_DELTA_SUM,
    ZERO_BUCKET_TAGS,
    ExporterControl,
    FakeIntake,
    agent_status_start,
    flatten_series_points,
    flatten_sketch_points,
    format_point,
    restart_agent,
    select_points,
    wait_until,
)

NAMESPACES = [PLAIN_NAMESPACE, COUNTERS_NAMESPACE]

# Seconds to wait for the daemon to scrape the baseline phase with both
# instances before advancing to the update phase.
BASELINE_SCRAPE_TIMEOUT = 120
# Seconds to wait for the expected payloads to reach the fake intake after the
# phase switch (collection interval + sketch flush + forwarder retry budget).
INTAKE_TIMEOUT = 180


def _sketch_problems(sketches):
    """Return a list of human-readable problems for the expected sketches.

    An empty list means every expected bucket context has at least one valid
    sketch point at the intake.
    """
    problems = []
    for namespace in NAMESPACES:
        all_zero = select_points(sketches, f'{namespace}.{ALL_ZERO}', ZERO_BUCKET_TAGS)
        if not all_zero:
            problems.append(f'no sketch for {namespace}.{ALL_ZERO} with tags {sorted(ZERO_BUCKET_TAGS)}')
        else:
            problems.extend(_zero_point_problems(all_zero[0], ALL_ZERO_DELTA))

        big = select_points(sketches, f'{namespace}.{BIG}', ZERO_BUCKET_TAGS)
        if not big:
            problems.append(f'no sketch for {namespace}.{BIG} with tags {sorted(ZERO_BUCKET_TAGS)}')
        else:
            problems.extend(_zero_point_problems(big[0], BIG_DELTA))

        for family in (MIXED, NEGATIVE):
            positive = select_points(sketches, f'{namespace}.{family}', MIXED_BUCKET_TAGS)
            if not positive:
                problems.append(f'no sketch for {namespace}.{family} with tags {sorted(MIXED_BUCKET_TAGS)}')
            else:
                problems.extend(_positive_point_problems(positive[0], POSITIVE_DELTA))
    return problems


def _zero_point_problems(point, expected_cnt):
    """Validate a point-mass sketch at zero: exact count, zero summaries.

    Large counts are split across multiple zero bins (observed as
    ``k=[0, 0], n=[65, 65535]`` for 65,600 observations), so every bin key must
    be zero and the bin counts must sum to the total count.
    """
    problems = []
    if point['cnt'] != expected_cnt:
        problems.append(f"cnt is {point['cnt']}, expected {expected_cnt}: {format_point(point)}")
    if any(k != 0 for k in point['k']) or sum(point['n']) != expected_cnt or not point['n']:
        problems.append(
            f"bins are k={point['k']} n={point['n']}, expected only zero-bin keys with counts summing to {expected_cnt}"
        )
    for field in ('min', 'max', 'avg', 'sum'):
        value = point[field]
        if value != 0.0 or not math.isfinite(value):
            problems.append(f'{field} is {value!r}, expected exactly 0')
    return problems


def _positive_point_problems(point, expected_cnt):
    """Validate a bucket of interpolated observations in (0, 5]."""
    problems = []
    if point['cnt'] != expected_cnt:
        problems.append(f"cnt is {point['cnt']}, expected {expected_cnt}: {format_point(point)}")
    for field in ('min', 'max', 'avg', 'sum'):
        if not math.isfinite(point[field]):
            problems.append(f'{field} is not finite: {format_point(point)}')
    if point['min'] < 0 or point['max'] > 5.0:
        problems.append(f'values outside [0, 5]: {format_point(point)}')
    if not 0 <= point['avg'] <= 5.0:
        problems.append(f'average outside [0, 5]: {format_point(point)}')
    if sum(point['n']) != expected_cnt:
        problems.append(f"bin counts {point['n']} do not sum to {expected_cnt}")
    return problems


def _assert_absent_contexts(sketches):
    """Buckets that must never emit a sketch in this scenario."""
    for namespace in NAMESPACES:
        for family in (MIXED, NEGATIVE):
            stale = select_points(sketches, f'{namespace}.{family}', ZERO_BUCKET_TAGS)
            assert not stale, f'unexpected zero-bucket sketch for {family}: {format_point(stale[0])}'

        negative_span = select_points(sketches, f'{namespace}.{NEGATIVE}', NEGATIVE_BUCKET_TAGS)
        assert not negative_span, f'unexpected sketch for the constant (-5, 0] bucket: {format_point(negative_span[0])}'

    infinite = [point for point in sketches if 'lower_bound:-inf' in point['tags']]
    assert not infinite, f'sketches with an infinite lower bound must never be aggregated: {format_point(infinite[0])}'


def _series_problems(series):
    """Validate the monotonic count deltas of the counters variant."""
    problems = []
    expected = {
        f'{COUNTERS_NAMESPACE}.{ALL_ZERO}.count': ALL_ZERO_DELTA,
        f'{COUNTERS_NAMESPACE}.{MIXED}.count': POSITIVE_DELTA,
        f'{COUNTERS_NAMESPACE}.{MIXED}.sum': POSITIVE_DELTA_SUM,
        f'{COUNTERS_NAMESPACE}.{NEGATIVE}.count': POSITIVE_DELTA,
        f'{COUNTERS_NAMESPACE}.{NEGATIVE}.sum': POSITIVE_DELTA_SUM,
        f'{COUNTERS_NAMESPACE}.{BIG}.count': BIG_DELTA,
    }
    for metric, expected_value in expected.items():
        points = select_points(series, metric)
        if not points:
            problems.append(f'no series point for {metric}')
        elif not any(math.isclose(point['value'], expected_value) for point in points):
            values = [point['value'] for point in points]
            problems.append(f'{metric} has values {values}, expected {expected_value}')
    return problems


def _diagnostics(intake, exporter):
    lines = []
    for label, func in (
        ('fake intake route stats', intake.routestats),
        ('exporter stats', exporter.stats),
    ):
        try:
            lines.append(f'{label}: {json.dumps(func(), sort_keys=True)}')
        except Exception as e:  # noqa: BLE001
            lines.append(f'{label}: unavailable ({e})')
    try:
        sketches = intake.sketches()
        lines.append(f'sketch points received ({len(sketches)}):')
        lines.extend(f'  {format_point(point)}' for point in sketches[:100])
    except Exception as e:  # noqa: BLE001
        lines.append(f'sketch points: unavailable ({e})')
    return '\n'.join(lines)


@pytest.mark.e2e
def test_zero_bucket_distributions_reach_intake(dd_agent_check, dd_get_state):
    # Requesting dd_agent_check makes the plugin skip this test during regular
    # unit runs. The returned one-shot check runner is intentionally unused:
    # this test exercises the already-running Agent daemon and fake intake.
    state = dd_get_state('zero_buckets')
    assert state, 'missing zero_buckets state; the E2E environment did not start'
    exporter = ExporterControl(state['exporter_url'])
    intake = FakeIntake(state['fakeintake_url'])

    agent_start = agent_status_start()

    # Both daemon instances must scrape the baseline phase before it is
    # replaced: monotonic buckets suppress the first value they ever see, and
    # a bucket that was zero on its first scrape is not tracked at all. Two
    # scrapes per instance (4 total) prove both baselines were established.
    try:
        exporter.wait_for_phase_scrapes('baseline', minimum=4, timeout=BASELINE_SCRAPE_TIMEOUT)
    except TimeoutError as e:
        if exporter.stats()['scrapes'] != 0:
            pytest.fail(
                'the Agent daemon scraped the exporter but not enough baseline phases.\n'
                f'{_diagnostics(intake, exporter)}\n\nOriginal error: {e}',
                pytrace=False,
            )

        # Zero scrapes of any phase means the daemon booted without scheduling
        # the openmetrics check. This happens intermittently in `ddev env test
        # --base` sessions: the check configuration is renamed while local
        # packages install, and the post-install Agent restart occasionally
        # comes up without it. Restarting the Agent re-reads the mounted
        # configuration, which is safe here (before the update phase) because
        # all monotonic baselines are (re)established by the wait below.
        restart_agent()
        # The restart changes the Agent start time; the no-crash assertion
        # below must compare against the post-recovery boot.
        agent_start = agent_status_start()
        try:
            exporter.wait_for_phase_scrapes('baseline', minimum=4, timeout=BASELINE_SCRAPE_TIMEOUT)
        except TimeoutError as e:
            pytest.fail(
                'the Agent daemon never scraped the exporter baseline phase, even after a config reload.\n'
                f'{_diagnostics(intake, exporter)}\n\nOriginal error: {e}',
                pytrace=False,
            )

    exporter.set_phase('update')

    try:
        sketches = wait_until(
            lambda: None if _sketch_problems(intake.sketches()) else intake.sketches(),
            timeout=INTAKE_TIMEOUT,
            interval=5,
            description='the expected zero-bucket sketches at the fake intake',
        )
    except TimeoutError as e:
        problems = _sketch_problems(intake.sketches())
        pytest.fail(
            'expected sketches never reached the fake intake.\nProblems:\n'
            + '\n'.join(f'  - {problem}' for problem in problems)
            + f'\n\n{_diagnostics(intake, exporter)}\n\nOriginal error: {e}',
            pytrace=False,
        )

    # Buckets that must not emit anything in this scenario.
    _assert_absent_contexts(sketches)

    # The counters variant must also submit its monotonic .count/.sum deltas;
    # these prove the variant branch ran and do not substitute for the sketch
    # assertions above.
    try:
        series = wait_until(
            lambda: None if _series_problems(intake.series()) else intake.series(),
            timeout=INTAKE_TIMEOUT,
            interval=5,
            description='the expected monotonic counter deltas at the fake intake',
        )
    except TimeoutError as e:
        problems = _series_problems(intake.series())
        pytest.fail(
            'expected series never reached the fake intake.\nProblems:\n'
            + '\n'.join(f'  - {problem}' for problem in problems)
            + f'\n\n{_diagnostics(intake, exporter)}\n\nOriginal error: {e}',
            pytrace=False,
        )

    final_series_problems = _series_problems(series)
    assert not final_series_problems, '\n'.join(final_series_problems)

    # The Agent process must not have been restarted, and it must have kept
    # scraping the update phase after the deltas were submitted.
    assert agent_status_start() == agent_start, 'the Agent process restarted during the test'
    update_scrapes = exporter.stats()['scrapes_by_phase']['update']
    assert update_scrapes >= 2, f'only {update_scrapes} scrapes of the update phase; the daemon stopped scraping'


def test_flatten_sketch_points_defaults_and_deduplicates():
    payloads = [
        {
            'data': [
                {
                    'metric': 'openmetrics.e2e_zero_all_zero_seconds',
                    'host': 'h1',
                    'tags': ['lower_bound:0', 'upper_bound:0'],
                    'dogsketches': [{'ts': 100, 'cnt': 3, 'k': [0], 'n': [3]}],
                }
            ]
        },
        # Forwarder retries can POST the same payload twice; the duplicate must
        # not be counted twice.
        {
            'data': [
                {
                    'metric': 'openmetrics.e2e_zero_all_zero_seconds',
                    'host': 'h1',
                    'tags': ['lower_bound:0', 'upper_bound:0'],
                    'dogsketches': [{'ts': 100, 'cnt': 3, 'k': [0], 'n': [3]}],
                }
            ]
        },
        # A second flush interval for the same context is a distinct point.
        {
            'data': [
                {
                    'metric': 'openmetrics.e2e_zero_all_zero_seconds',
                    'host': 'h1',
                    'tags': ['lower_bound:0', 'upper_bound:0'],
                    'dogsketches': [{'ts': 110, 'cnt': 7, 'min': 0.5, 'max': 4.5, 'avg': 2.0, 'sum': 14.0}],
                }
            ]
        },
    ]

    points = flatten_sketch_points(payloads)

    assert len(points) == 2
    first = points[0]
    # min/max/avg/sum are omitted by proto3 JSON when zero; missing keys mean 0.
    assert (first['cnt'], first['min'], first['max'], first['avg'], first['sum']) == (3, 0.0, 0.0, 0.0, 0.0)
    assert first['k'] == [0]
    assert first['n'] == [3]
    assert first['ts'] == 100
    second = points[1]
    assert (second['cnt'], second['min'], second['max'], second['avg'], second['sum']) == (7, 0.5, 4.5, 2.0, 14.0)
    assert second['k'] == [] and second['n'] == []


def test_flatten_series_points_defaults_and_deduplicates():
    payloads = [
        {
            'data': [
                {
                    'metric': 'openmetrics_counters.e2e_zero_mixed_seconds.count',
                    'tags': ['endpoint:test'],
                    'points': [{'value': 3, 'timestamp': 100}],
                }
            ]
        },
        {
            'data': [
                {
                    'metric': 'openmetrics_counters.e2e_zero_mixed_seconds.count',
                    'tags': ['endpoint:test'],
                    'points': [{'value': 3, 'timestamp': 100}, {'value': 4, 'timestamp': 110}],
                }
            ]
        },
    ]

    points = flatten_series_points(payloads)

    assert sorted((point['ts'], point['value']) for point in points) == [(100, 3.0), (110, 4.0)]


def test_select_points_requires_all_tags():
    points = [
        {'metric': 'm', 'tags': frozenset({'lower_bound:0', 'upper_bound:0'}), 'ts': 1, 'cnt': 3},
        {'metric': 'm', 'tags': frozenset({'lower_bound:0', 'upper_bound:5.0'}), 'ts': 1, 'cnt': 3},
        {'metric': 'other', 'tags': frozenset({'lower_bound:0', 'upper_bound:0'}), 'ts': 1, 'cnt': 3},
    ]

    selected = select_points(points, 'm', {'lower_bound:0', 'upper_bound:0'})

    assert len(selected) == 1
    assert selected[0]['tags'] == frozenset({'lower_bound:0', 'upper_bound:0'})


def test_wait_until_times_out():
    with pytest.raises(TimeoutError, match='never-ready condition'):
        wait_until(lambda: None, timeout=0.2, interval=0.05, description='never-ready condition')


def test_zero_point_problems_accepts_split_bins():
    # 65,600 zero observations serialize as two zero bins (bin counts split at
    # 65,535); min/max/avg/sum are omitted by proto3 JSON when zero.
    point = {
        'metric': 'openmetrics.e2e_zero_big_count_seconds',
        'host': 'h',
        'tags': frozenset({'lower_bound:0', 'upper_bound:0'}),
        'ts': 1790080247,
        'cnt': 65600,
        'min': 0.0,
        'max': 0.0,
        'avg': 0.0,
        'sum': 0.0,
        'k': [0, 0],
        'n': [65, 65535],
    }

    assert _zero_point_problems(point, 65600) == []

    bad = dict(point, cnt=3)
    assert _zero_point_problems(bad, 65600)

    non_zero_bin = dict(point, k=[0, 12], n=[65, 65535])
    assert _zero_point_problems(non_zero_bin, 65600)


def test_positive_point_problems_rejects_out_of_range():
    point = {
        'metric': 'openmetrics.e2e_zero_mixed_seconds',
        'host': 'h',
        'tags': frozenset({'lower_bound:0', 'upper_bound:5.0'}),
        'ts': 1790080247,
        'cnt': 3,
        'min': 0.0,
        'max': 3.35,
        'avg': 1.67,
        'sum': 5.02,
        'k': [0, 1371, 1416],
        'n': [1, 1, 1],
    }

    assert _positive_point_problems(point, 3) == []

    out_of_range = dict(point, max=5.5)
    assert _positive_point_problems(out_of_range, 3)

    wrong_count = dict(point, cnt=4)
    assert _positive_point_problems(wrong_count, 3)
