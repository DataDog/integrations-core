# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.relationsmanager import ALL_SCHEMAS, IDX_METRICS, RelationsManager

from .common import SCHEMA_NAME

pytestmark = pytest.mark.unit


def test_relation_filter():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_name': 'breed', 'schemas': ['public']}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert (
        query_filter == "Select foo from bar where ( relname = 'breed' AND schemaname = ANY(array['public']::text[]) )"
    )


def test_relation_filter_no_schemas():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_name': 'persons', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where ( relname = 'persons' )"


def test_relation_filter_regex():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where ( relname ~ 'b.*' )"


def test_relation_filter_relkind():
    query = "Select foo from bar where {relations}"
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r', 't']}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where ( relname ~ 'b.*' AND relkind = ANY(array['r' ,'t']) )"


def test_relkind_does_not_override():
    query = "Select foo from bar where relkind = 's' AND {relations}"
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r', 't']}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert query_filter == "Select foo from bar where relkind = 's' AND ( relname ~ 'b.*' )"


def test_relkind_does_not_apply_to_index_metrics():
    query = IDX_METRICS['query'].replace('{metrics_columns}', '(a, b)')
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS], 'relkind': ['r']}]
    relations = RelationsManager(relations_config)

    query_filter = relations.filter_relation_query(query, SCHEMA_NAME)
    assert 'relkind' not in query_filter
