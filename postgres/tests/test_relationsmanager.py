# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.relationsmanager import (
    ALL_SCHEMAS,
    IDX_METRICS,
    LOCK_METRICS,
    RelationsManager,
    get_pg_class_query,
)
from datadog_checks.postgres.version_utils import V9_6, V13, V16, V18

from .common import SCHEMA_NAME

pytestmark = pytest.mark.unit
default_max_relations = 300


@pytest.mark.parametrize(
    'relations_config,expected_filter',
    [
        (
            [
                {'relation_regex': 'ix.*', 'schemas': ['public', 's1', 's2']},
                {'relation_regex': 'ibx.*', 'schemas': ['public']},
                {'relation_regex': 'icx.*', 'schemas': ['public']},
            ],
            "(( relname ~ 'ix.*' AND schemaname = ANY(array['public','s1','s2']::text[]) ) "
            "OR ( relname ~ 'ibx.*' AND schemaname = ANY(array['public']::text[]) ) "
            "OR ( relname ~ 'icx.*' AND schemaname = ANY(array['public']::text[]) ))",
        ),
        (
            [
                {'relation_regex': '.+_archive'},
            ],
            "(( relname ~ '.+_archive' ))",
        ),
        (
            [
                {'relation_name': 'my_table', 'schemas': ['public', 'app'], 'relkind': ['r']},  # relkind ignored
                {'relation_name': 'my_table2', 'relkind': ['p', 'r']},  # relkind ignored
                {'relation_regex': 'table.*'},
            ],
            "(( relname = 'my_table' AND schemaname = ANY(array['public','app']::text[]) ) "
            "OR ( relname = 'my_table2' ) "
            "OR ( relname ~ 'table.*' ))",
        ),
        (
            ['table1', 'table2'],
            "(( relname = 'table1' ) OR ( relname = 'table2' ))",
        ),
    ],
)
def test_relations_cases(relations_config, expected_filter):
    query = '{relations}'
    relations = RelationsManager(relations_config, default_max_relations)
    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == expected_filter


def test_relation_filter():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_name': 'breed', 'schemas': ['public']}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert (
        query_filter
        == "Select foo from bar where (( relname = 'breed' AND schemaname = ANY(array['public']::text[]) ))"
    )


def test_relation_filter_no_schemas():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_name': 'persons', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where (( relname = 'persons' ))"


def test_relation_filter_regex():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where (( relname ~ 'b.*' ))"


def test_relation_filter_relkind():
    query = LOCK_METRICS['query'].replace('{metrics_columns}', 'foo')
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r', 't']}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert "AND relkind = ANY(array['r','t'])" in query_filter


def test_relation_filter_limit():
    query = get_pg_class_query(V18)['query']
    relations_config = [{'relation_regex': '.*', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert 'LIMIT 300' in query_filter


def test_relkind_does_not_apply_to_index_metrics():
    query = IDX_METRICS['query'].replace('{metrics_columns}', 'foo')
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r']}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert "relkind = ANY(array['r'])" not in query_filter


# Golden output of get_pg_class_query, pinned byte-for-byte. The builder replaced the former static
# QUERY_PG_CLASS constant; this locks the emitted SQL and column set so a refactor of the builder cannot
# silently change what the check collects. No column is version-gated yet, so every supported version
# produces this identical query: when a version-gated column is later added, give the affected versions
# their own expected output here.
GOLDEN_PG_CLASS_QUERY = """
SELECT
  current_database(),
  N.nspname,
  C.relname,
  pg_stat_get_numscans(C.oid),
  pg_stat_get_tuples_returned(C.oid),
  I.idx_scan,
  I.idx_tup_fetch,
  pg_stat_get_tuples_inserted(C.oid),
  pg_stat_get_tuples_updated(C.oid),
  pg_stat_get_tuples_deleted(C.oid),
  pg_stat_get_tuples_hot_updated(C.oid),
  pg_stat_get_live_tuples(C.oid),
  pg_stat_get_dead_tuples(C.oid),
  pg_stat_get_vacuum_count(C.oid),
  pg_stat_get_autovacuum_count(C.oid),
  pg_stat_get_analyze_count(C.oid),
  pg_stat_get_autoanalyze_count(C.oid),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_vacuum_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autovacuum_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_analyze_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autoanalyze_time(C.oid))),
  pg_stat_get_numscans(idx_toast.indexrelid),
  pg_stat_get_tuples_fetched(idx_toast.indexrelid),
  pg_stat_get_tuples_inserted(C.reltoastrelid),
  pg_stat_get_tuples_deleted(C.reltoastrelid),
  pg_stat_get_live_tuples(C.reltoastrelid),
  pg_stat_get_dead_tuples(C.reltoastrelid),
  pg_stat_get_vacuum_count(C.reltoastrelid),
  pg_stat_get_autovacuum_count(C.reltoastrelid),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_vacuum_time(C.reltoastrelid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autovacuum_time(C.reltoastrelid))),
  C.xmin
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
LEFT JOIN pg_index idx_toast ON (idx_toast.indrelid = C.reltoastrelid)
LEFT JOIN LATERAL (
    SELECT sum(pg_stat_get_numscans(indexrelid))::bigint AS idx_scan,
           sum(pg_stat_get_tuples_fetched(indexrelid))::bigint AS idx_tup_fetch
      FROM pg_index
     WHERE pg_index.indrelid = C.oid) I ON true
WHERE C.relkind = 'r'
    AND NOT (nspname = ANY('{{pg_catalog,information_schema}}'))
    AND NOT EXISTS (
        SELECT 1
        from pg_locks
        WHERE locktype = 'relation'
        AND mode = 'AccessExclusiveLock'
        AND granted = true
        AND relation = C.oid
    )
    AND {relations} {limits}
"""

GOLDEN_PG_CLASS_COLUMNS = [
    {'name': 'db', 'type': 'tag'},
    {'name': 'schema', 'type': 'tag'},
    {'name': 'table', 'type': 'tag'},
    {'name': 'seq_scans', 'type': 'rate'},
    {'name': 'seq_rows_read', 'type': 'rate'},
    {'name': 'index_rel_scans', 'type': 'rate'},
    {'name': 'index_rel_rows_fetched', 'type': 'rate'},
    {'name': 'rows_inserted', 'type': 'rate'},
    {'name': 'rows_updated', 'type': 'rate'},
    {'name': 'rows_deleted', 'type': 'rate'},
    {'name': 'rows_hot_updated', 'type': 'rate'},
    {'name': 'live_rows', 'type': 'gauge'},
    {'name': 'dead_rows', 'type': 'gauge'},
    {'name': 'vacuumed', 'type': 'monotonic_count'},
    {'name': 'autovacuumed', 'type': 'monotonic_count'},
    {'name': 'analyzed', 'type': 'monotonic_count'},
    {'name': 'autoanalyzed', 'type': 'monotonic_count'},
    {'name': 'last_vacuum_age', 'type': 'gauge'},
    {'name': 'last_autovacuum_age', 'type': 'gauge'},
    {'name': 'last_analyze_age', 'type': 'gauge'},
    {'name': 'last_autoanalyze_age', 'type': 'gauge'},
    {'name': 'toast.index_scans', 'type': 'monotonic_count'},
    {'name': 'toast.rows_fetched', 'type': 'monotonic_count'},
    {'name': 'toast.rows_inserted', 'type': 'monotonic_count'},
    {'name': 'toast.rows_deleted', 'type': 'monotonic_count'},
    {'name': 'toast.live_rows', 'type': 'gauge'},
    {'name': 'toast.dead_rows', 'type': 'gauge'},
    {'name': 'toast.vacuumed', 'type': 'monotonic_count'},
    {'name': 'toast.autovacuumed', 'type': 'monotonic_count'},
    {'name': 'toast.last_vacuum_age', 'type': 'gauge'},
    {'name': 'toast.last_autovacuum_age', 'type': 'gauge'},
    {'name': 'relation.xmin', 'type': 'gauge'},
]


@pytest.mark.parametrize('version', [V9_6, V13, V16, V18])
def test_get_pg_class_query_golden_output(version):
    """The builder emits byte-identical SQL and columns to the former static QUERY_PG_CLASS constant."""
    query = get_pg_class_query(version)
    assert query['name'] == 'pg_class'
    assert query['query'] == GOLDEN_PG_CLASS_QUERY
    assert query['columns'] == GOLDEN_PG_CLASS_COLUMNS
