# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ``advanced_queries`` JSON loader."""

from __future__ import annotations

import json

import pytest

from datadog_checks.clickhouse import advanced_queries

MATCH_FORMAT_NAMES = ('SystemEvents', 'SystemMetrics', 'SystemAsynchronousMetrics')
ALL_NAMES = (*MATCH_FORMAT_NAMES, 'SystemErrors')


@pytest.fixture(autouse=True)
def _reset_cache():
    """Clear the module-level cache so each test sees a fresh load."""
    advanced_queries._cache.clear()
    yield
    advanced_queries._cache.clear()


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect ``load()`` to a temporary directory so tests can author JSON inputs."""
    monkeypatch.setattr(advanced_queries, 'DATA_DIR', str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Module attribute access (__getattr__)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('name', ALL_NAMES)
def test_module_attribute_returns_querymanager_shape(name):
    spec = getattr(advanced_queries, name)
    assert isinstance(spec['name'], str) and spec['name']
    assert isinstance(spec['query'], str) and spec['query']
    assert isinstance(spec['columns'], list) and spec['columns']


def test_module_attribute_caches_result():
    first = advanced_queries.SystemEvents
    second = advanced_queries.SystemEvents
    assert first is second


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match=r"module .* has no attribute 'SystemNonsense'"):
        advanced_queries.SystemNonsense  # noqa: B018


# ---------------------------------------------------------------------------
# Compact format: load() + _build_items()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('name', MATCH_FORMAT_NAMES)
def test_match_format_has_source_and_match_columns(name):
    spec = getattr(advanced_queries, name)
    source_col, match_col = spec['columns']
    assert source_col == {'name': 'metric_value', 'type': 'source'}
    assert match_col['name'] == 'metric_name'
    assert match_col['type'] == 'match'
    assert match_col['source'] == 'metric_value'
    assert isinstance(match_col['items'], dict)


@pytest.mark.parametrize('name', MATCH_FORMAT_NAMES)
def test_match_format_items_are_alphabetically_sorted(name):
    items = getattr(advanced_queries, name)['columns'][1]['items']
    assert list(items) == sorted(items)


@pytest.mark.parametrize('name', MATCH_FORMAT_NAMES)
def test_match_format_items_carry_name_and_type(name):
    items = getattr(advanced_queries, name)['columns'][1]['items']
    for key, entry in items.items():
        assert entry['type']
        assert entry['name'].endswith('.' + key) or entry['name'] == f"{entry['name'].split('.', 1)[0]}.{key}"


def test_temporal_percent_entries_carry_scale():
    items = advanced_queries.SystemEvents['columns'][1]['items']
    scaled = [(key, entry) for key, entry in items.items() if entry['type'] == 'temporal_percent']
    assert scaled, "system_events should ship at least one temporal_percent entry"
    for _, entry in scaled:
        assert entry['scale'] in {'second', 'millisecond', 'microsecond', 'nanosecond'}


def test_dotted_key_is_preserved_in_name():
    # `jemalloc.epoch` is the canonical key with a dot; it must round-trip into
    # `name = '<prefix>.<key>'` without the loader mis-splitting the dotted segment.
    items = advanced_queries.SystemAsynchronousMetrics['columns'][1]['items']
    assert items['jemalloc.epoch']['name'] == 'asynchronous_metrics.jemalloc.epoch'


# ---------------------------------------------------------------------------
# Verbatim format (system_errors)
# ---------------------------------------------------------------------------


def test_verbatim_format_passes_columns_through():
    spec = advanced_queries.SystemErrors
    assert spec['name'] == 'system.errors'
    assert spec['columns'][0] == {'name': 'errors.raised', 'type': 'monotonic_count'}
    assert spec['columns'][-1] == {'name': 'remote', 'type': 'tag', 'boolean': True}


# ---------------------------------------------------------------------------
# Error wrapping (RuntimeError boundary on malformed inputs)
# ---------------------------------------------------------------------------


def _write_spec(tmp_path, name, payload):
    (tmp_path / f'{name}.json').write_text(json.dumps(payload), encoding='utf-8')


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param('not valid json', id='invalid-json'),
        pytest.param('{"name": "x"}', id='missing-query-and-shape'),
        pytest.param('{"name": "x", "query": "y", "items": ["should-be-dict"]}', id='items-as-list'),
        pytest.param('{"name": "x", "query": "y", "items": 5, "prefix": "p"}', id='items-as-scalar'),
    ],
)
def test_load_wraps_malformed_payloads_in_runtime_error(isolated_data_dir, payload):
    (isolated_data_dir / 'broken.json').write_text(payload, encoding='utf-8')
    with pytest.raises(RuntimeError, match=r"failed to load advanced query 'broken'"):
        advanced_queries.load('broken')


def test_load_wraps_missing_file_in_runtime_error(isolated_data_dir):
    with pytest.raises(RuntimeError, match=r"failed to load advanced query 'missing'") as excinfo:
        advanced_queries.load('missing')
    assert isinstance(excinfo.value.__cause__, FileNotFoundError)


def test_load_preserves_cause_chain(isolated_data_dir):
    _write_spec(isolated_data_dir, 'no_query', {'name': 'x'})
    with pytest.raises(RuntimeError) as excinfo:
        advanced_queries.load('no_query')
    assert isinstance(excinfo.value.__cause__, KeyError)


# ---------------------------------------------------------------------------
# warm_cache idempotency
# ---------------------------------------------------------------------------


def test_warm_cache_populates_every_known_name():
    assert advanced_queries._cache == {}
    advanced_queries.warm_cache()
    assert set(advanced_queries._cache) == set(ALL_NAMES)


def test_warm_cache_does_not_overwrite_existing_entries():
    sentinel = object()
    advanced_queries._cache['SystemEvents'] = sentinel
    advanced_queries.warm_cache()
    assert advanced_queries._cache['SystemEvents'] is sentinel
    assert set(advanced_queries._cache) == set(ALL_NAMES)
