# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared helpers for the zero-bound histogram bucket E2E test.

The test runs against a real Agent daemon (started by ``ddev env start``) that
scrapes the phase-controlled exporter from ``compose/zero-buckets/exporter.py``
and forwards distribution sketches to a local Datadog fake intake. Assertions
read what actually arrived at the intake, via the fake intake's parsed-JSON
payload endpoints, so no protobuf decoding is needed on the test side.

Wire-format notes (agent-payload ``SketchPayload`` marshaled to JSON by the
fake intake): scalar summary fields of a dogsketch (``min``, ``max``, ``avg``,
``sum``) are omitted when zero because of proto3 ``omitempty`` semantics, so an
all-zero sketch serializes as ``{"ts": ..., "cnt": N, "k": [0], "n": [N]}``.
Missing keys are therefore treated as ``0.0``, which is exactly the value an
all-zero point mass must have.
"""

import os
import re
import subprocess
import time

import requests

from datadog_checks.dev._env import E2E_PARENT_PYTHON

ALL_ZERO = 'e2e_zero_all_zero_seconds'
MIXED = 'e2e_zero_mixed_seconds'
NEGATIVE = 'e2e_zero_negative_seconds'
BIG = 'e2e_zero_big_count_seconds'

HISTOGRAM_FAMILIES = [ALL_ZERO, MIXED, NEGATIVE, BIG]

PLAIN_NAMESPACE = 'openmetrics'
COUNTERS_NAMESPACE = 'openmetrics_counters'

# Bucket tag pairs as the Agent submits them (label canonicalization maps
# le="0.0" to upper_bound:0 and le="5" to upper_bound:5.0).
ZERO_BUCKET_TAGS = frozenset({'lower_bound:0', 'upper_bound:0'})
MIXED_BUCKET_TAGS = frozenset({'lower_bound:0', 'upper_bound:5.0'})
NEGATIVE_BUCKET_TAGS = frozenset({'lower_bound:-5.0', 'upper_bound:0'})

SKETCHES_ROUTE = '/api/beta/sketches'
SERIES_ROUTE = '/api/v2/series'

# Fixed host ports for the E2E compose services (the prometheus service in the
# same compose file already uses a fixed 9090). Fixed ports also let a ddev
# org configuration that overrides the main intake URL be neutralized with
# explicit `-e DD_DD_URL=...`/`-e DD_API_KEY=...` flags, since those values must
# be known before the environment starts.
EXPORTER_PORT = 8999
FAKEINTAKE_PORT = 8107

# The exporter advances the le="0" bucket of this family by exactly 3 between
# the baseline and update phases, all with zero-valued observations.
ALL_ZERO_DELTA = 3
# The big-count family advances by 65,600 zero-valued observations, crossing
# the 65,535 boundary of DDSketch bin counts.
BIG_DELTA = 65600
# The mixed and negative families advance their (0, 5] bucket by 3 observations
# with values 1, 1 and 2.
POSITIVE_DELTA = 3
POSITIVE_DELTA_SUM = 4


def build_instances(hostname, exporter_port):
    """Build the two daemon instances: plain distributions and the
    ``collect_counters_with_distributions`` variant.

    The two instances use distinct namespaces so their submitted metric names
    never collide; each instance keeps its own monotonic bucket baselines.
    """
    endpoint = f'http://{hostname}:{exporter_port}/metrics'
    common = {
        'openmetrics_endpoint': endpoint,
        'metrics': list(HISTOGRAM_FAMILIES),
        'histogram_buckets_as_distributions': True,
        # Deterministic first-scrape behavior: never flush the first value of a
        # monotonic series, so the baseline phase only records state.
        'use_process_start_time': False,
        'min_collection_interval': 5,
    }
    return [
        {**common, 'namespace': PLAIN_NAMESPACE},
        {**common, 'namespace': COUNTERS_NAMESPACE, 'collect_counters_with_distributions': True},
    ]


def wait_until(predicate, timeout, interval=2.0, description='condition'):
    """Poll ``predicate`` until it returns a truthy value or ``timeout`` passes.

    Returns the truthy value; raises ``TimeoutError`` otherwise. Uses a
    monotonic deadline so the test can never hang indefinitely.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(f'Timed out after {timeout}s waiting for {description}')
        time.sleep(interval)


class ExporterControl:
    """Client for the exporter's control endpoints."""

    def __init__(self, base_url):
        self.base_url = base_url

    def stats(self):
        response = requests.get(f'{self.base_url}/control/stats', timeout=10)
        response.raise_for_status()
        return response.json()

    def set_phase(self, phase):
        response = requests.get(f'{self.base_url}/control/set', params={'phase': phase}, timeout=10)
        response.raise_for_status()

    def wait_for_phase_scrapes(self, phase, minimum, timeout=60):
        """Wait until the current (or a previous) phase was scraped ``minimum`` times."""
        return wait_until(
            lambda: self.stats()['scrapes_by_phase'].get(phase, 0) >= minimum,
            timeout,
            description=f'at least {minimum} scrapes of phase {phase!r}',
        )


class FakeIntake:
    """Client for the fake intake's test endpoints."""

    def __init__(self, base_url):
        self.base_url = base_url

    def parsed_payloads(self, endpoint):
        response = requests.get(
            f'{self.base_url}/fakeintake/payloads', params={'endpoint': endpoint, 'format': 'json'}, timeout=30
        )
        response.raise_for_status()
        return response.json()['payloads']

    def sketches(self):
        return flatten_sketch_points(self.parsed_payloads(SKETCHES_ROUTE))

    def series(self):
        return flatten_series_points(self.parsed_payloads(SERIES_ROUTE))

    def routestats(self):
        response = requests.get(f'{self.base_url}/fakeintake/routestats', timeout=10)
        response.raise_for_status()
        return response.json()


def flatten_sketch_points(payloads):
    """Flatten parsed sketch payloads into deduplicated point records.

    Each parsed payload's ``data`` is a list of sketch entries (one per
    metric/tagset) whose ``dogsketches`` hold one entry per flush interval.
    Forwarder retries can POST the same payload more than once, so points are
    deduplicated by (metric, host, tags, ts).
    """
    points = []
    seen = set()
    for payload in payloads:
        for entry in payload.get('data') or []:
            metric = entry.get('metric', '')
            host = entry.get('host', '')
            tags = frozenset(entry.get('tags') or [])
            for dogsketch in entry.get('dogsketches') or []:
                ts = int(dogsketch.get('ts') or 0)
                key = (metric, host, tags, ts)
                if key in seen:
                    continue
                seen.add(key)
                points.append(
                    {
                        'metric': metric,
                        'host': host,
                        'tags': tags,
                        'ts': ts,
                        'cnt': int(dogsketch.get('cnt') or 0),
                        'min': float(dogsketch.get('min') or 0.0),
                        'max': float(dogsketch.get('max') or 0.0),
                        'avg': float(dogsketch.get('avg') or 0.0),
                        'sum': float(dogsketch.get('sum') or 0.0),
                        'k': [int(k) for k in dogsketch.get('k') or []],
                        'n': [int(n) for n in dogsketch.get('n') or []],
                    }
                )
    return points


def flatten_series_points(payloads):
    """Flatten parsed /api/v2/series payloads into deduplicated point records."""
    points = []
    seen = set()
    for payload in payloads:
        for entry in payload.get('data') or []:
            metric = entry.get('metric', '')
            tags = frozenset(entry.get('tags') or [])
            for point in entry.get('points') or []:
                ts = int(point.get('timestamp') or 0)
                key = (metric, tags, ts)
                if key in seen:
                    continue
                seen.add(key)
                points.append({'metric': metric, 'tags': tags, 'ts': ts, 'value': float(point.get('value') or 0.0)})
    return points


def select_points(points, metric, tags=None):
    """Select points for ``metric`` whose tag set contains every tag in ``tags``."""
    tags = frozenset(tags or ())
    return [point for point in points if point['metric'] == metric and tags <= point['tags']]


def agent_status_start(check_name='openmetrics', timeout=180):
    """Return the Agent daemon's start time from ``ddev env agent ... status``.

    Used to prove the Agent process was not restarted during the test: a change
    in this value means the core process crashed and the supervisor restarted
    it. Retries until the status command succeeds because the daemon may still
    be booting when the test starts. Raises ``RuntimeError`` if the status
    command keeps failing, since missing evidence must not be silently ignored.
    """
    parent_python = os.environ.get(E2E_PARENT_PYTHON)
    environment = os.environ.get('HATCH_ENV_ACTIVE')
    if not parent_python or not environment:
        raise RuntimeError(
            f'missing {E2E_PARENT_PYTHON}/HATCH_ENV_ACTIVE environment variables; '
            'the test must run in a ddev E2E session'
        )

    command = [parent_python, '-m', 'ddev', 'env', 'agent', check_name, environment, 'status']

    def query():
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return None
        if result.returncode != 0:
            return None
        match = re.search(r'^\s*Agent start:\s*(.+?)\s*$', result.stdout, re.MULTILINE)
        if not match:
            return None
        return match.group(1)

    start = wait_until(query, timeout, interval=5, description='the agent status command to succeed')
    return start


def restart_agent(check_name='openmetrics'):
    """Restart the Agent daemon via ``ddev env reload`` (``agent.restart``).

    Used as a bounded recovery when the daemon booted without scheduling the
    integration's check: restarting re-reads the mounted ``conf.d``
    configuration. Must only be used before any baseline-dependent state is
    established, because a restart resets all check state.
    """
    parent_python = os.environ.get(E2E_PARENT_PYTHON)
    environment = os.environ.get('HATCH_ENV_ACTIVE')
    if not parent_python or not environment:
        raise RuntimeError(
            f'missing {E2E_PARENT_PYTHON}/HATCH_ENV_ACTIVE environment variables; '
            'the test must run in a ddev E2E session'
        )

    command = [parent_python, '-m', 'ddev', 'env', 'reload', check_name, environment]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f'`ddev env reload` failed:\n{result.stdout}\n{result.stderr}')


def format_point(point):
    """Render a sketch point for assertion messages."""
    return (
        f"metric={point['metric']} tags={sorted(point['tags'])} ts={point['ts']} cnt={point['cnt']} "
        f"min={point['min']} max={point['max']} avg={point['avg']} sum={point['sum']} k={point['k']} n={point['n']}"
    )
