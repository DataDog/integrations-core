# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.postgres import relationsmanager, util
from datadog_checks.postgres.version_utils import V14, V18

from .common import _iterate_metric_name

pytestmark = pytest.mark.unit


def _is_metric_descriptor(value):
    """True if value is a (metric_name, ..., submit_fn) tuple."""
    return isinstance(value, tuple) and bool(value) and isinstance(value[0], str) and callable(value[-1])


def _is_metric_container(obj):
    """True for the metric-bearing dict shapes _iterate_metric_name understands.

    Two shapes are declared throughout the integration: structured query dicts (a 'columns' or
    'metrics' key) and plain metric dicts mapping a SQL expression to a (metric_name, submit_fn)
    tuple. Other module-level dicts (lookup tables, config maps) are ignored.

    A dict with some metric descriptors and some malformed entries fails loudly rather than being
    silently dropped: skipping it would hide the exact missing-metadata mistake this test exists to
    catch (a typo'd descriptor would quietly remove every metric in its dict from the checked set).
    """
    if not isinstance(obj, dict) or not obj:
        return False
    if 'columns' in obj or 'metrics' in obj:
        return True
    values = list(obj.values())
    if not any(_is_metric_descriptor(v) for v in values):
        return False
    malformed = [v for v in values if not _is_metric_descriptor(v)]
    assert not malformed, f'Dict looks like a metric map but has malformed descriptors: {malformed}'
    return True


def _declared_metric_names():
    """Every postgresql.* metric the integration declares through util/relationsmanager.

    Collected by introspection so a new metric added to any existing declaration (a util dict, a
    relation query, or a version-gated query builder) is covered with no edit here. Builders are
    evaluated across the versions that bound their column sets so every gated column is included: the
    pg_class builder only adds columns in newer majors (highest version suffices), but pg_stat_wal
    dropped its I/O timing columns in PG 18, so both sides of that split are evaluated.
    """
    names = set()
    for module in (util, relationsmanager):
        for obj in vars(module).values():
            if _is_metric_container(obj):
                names.update(_iterate_metric_name(obj))
    names.update(_iterate_metric_name(relationsmanager.get_pg_class_query(V18)))
    for version in (V14, V18):
        names.update(_iterate_metric_name(util.get_stat_wal_query(version)))
    return names


def test_declared_metrics_have_metadata_row():
    """Every declared postgresql.* metric must have a row in metadata.csv.

    This is the common bundle mistake (add a metric, forget the metadata row) and it now fails in the
    unit suite, naming the offending metric, instead of only in `ddev validate metadata`.

    The reverse direction (orphan metadata rows) is intentionally not asserted here: activity,
    statement and other DBM metrics are emitted through dynamic code paths outside this declarative
    collection, so a metadata row absent from it is not necessarily dead. `ddev validate metadata`
    remains the backstop for those.
    """
    documented = set(get_metadata_metrics())
    missing = sorted(_declared_metric_names() - documented)
    assert not missing, f'Declared metrics missing a metadata.csv row: {missing}'


@pytest.mark.parametrize(
    'obj, expected',
    [
        ({'columns': [], 'query': 'x'}, True),
        ({'metrics': {}, 'query': 'x'}, True),
        ({'some_expr': ('postgresql.foo', len)}, True),
        ({'a': 'tag', 'b': 'gauge'}, False),
        ({'a': {'nested': 'dict'}}, False),
        ({}, False),
        ('not a dict', False),
        (['not', 'a', 'dict'], False),
    ],
)
def test_is_metric_container_classifies_shapes(obj, expected):
    """The classifier the whole consistency check rests on must recognise every metric-bearing shape."""
    assert _is_metric_container(obj) is expected


def test_is_metric_container_rejects_half_malformed_dict():
    """A dict that looks like a metric map but has a malformed descriptor fails loudly, not silently skipped."""
    half_malformed = {
        'good_expr': ('postgresql.good', len),
        'bad_expr': ('postgresql.bad',),  # missing submit fn
    }
    with pytest.raises(AssertionError):
        _is_metric_container(half_malformed)
