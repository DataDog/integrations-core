# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property tests for JSON replay-body mutations."""

from __future__ import annotations

import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from datadog_checks.dev.replay.pbt.json import mutate_json_whitespace, mutate_object_key_order, mutate_string_escapes

pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(alphabet=st.characters(blacklist_categories=('Cs',)), max_size=40),
)
json_values = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=8),
        st.dictionaries(
            st.text(alphabet=st.characters(blacklist_categories=('Cs',)), max_size=20), children, max_size=8
        ),
    ),
    max_leaves=30,
)


@pbt_settings
@given(value=json_values)
def test_object_key_order_mutation_preserves_decoded_json(value):
    body = json.dumps(value, ensure_ascii=False)

    assert json.loads(mutate_object_key_order(body)) == value


@pbt_settings
@given(value=json_values)
def test_json_whitespace_mutation_preserves_decoded_json(value):
    body = json.dumps(value, ensure_ascii=False)

    assert json.loads(mutate_json_whitespace(body)) == value


@pbt_settings
@given(value=json_values)
def test_json_string_escape_mutation_preserves_decoded_json(value):
    body = json.dumps(value, ensure_ascii=False)

    assert json.loads(mutate_string_escapes(body)) == value


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda value: not value.lstrip().startswith(('{', '['))))
def test_json_mutations_preserve_non_json_bodies(body):
    assert mutate_object_key_order(body) == body
    assert mutate_json_whitespace(body) == body
    assert mutate_string_escapes(body) == body
