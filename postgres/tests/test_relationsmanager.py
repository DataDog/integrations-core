# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.relationsmanager import (
    ALL_SCHEMAS,
    IDX_METRICS,
    LOCK_METRICS,
    QUERY_PG_CLASS,
    RelationsManager,
)

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
    query = QUERY_PG_CLASS['query']
    relations_config = [{'relation_regex': '.*', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert 'LIMIT 300' in query_filter


def test_relkind_does_not_apply_to_index_metrics():
    query = IDX_METRICS['query'].replace('{metrics_columns}', 'foo')
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r']}]
    relations = RelationsManager(relations_config, default_max_relations)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert 'relkind' not in query_filter
