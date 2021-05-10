# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres.relationsmanager import ALL_SCHEMAS, RelationsManager

from .common import SCHEMA_NAME

pytestmark = pytest.mark.unit


def test_relation_filter():
    relations_config = [{'relation_name': 'breed', 'schemas': ['public']}]
    relations = RelationsManager(relations_config)

    query_filter = relations.build_relations_filter(SCHEMA_NAME)
    assert query_filter == "( relname = 'breed' AND schemaname = ANY(array['public']::text[]) )"


def test_relation_filter_no_schemas():
    relations_config = [{'relation_name': 'persons', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config)

    query_filter = relations.build_relations_filter(SCHEMA_NAME)
    assert query_filter == "( relname = 'persons' )"


def test_relation_filter_regex():
    relations_config = [{'relation_regex': 'b.*', 'schemas': [ALL_SCHEMAS]}]
    relations = RelationsManager(relations_config)

    query_filter = relations.build_relations_filter(SCHEMA_NAME)
    assert query_filter == "( relname ~ 'b.*' )"
