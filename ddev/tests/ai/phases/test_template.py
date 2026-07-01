# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.phases.template import _SafeMapping, render_inline

from .conftest import resolve_key

# ---------------------------------------------------------------------------
# _SafeMapping
# ---------------------------------------------------------------------------


def test_safe_mapping_key_in_context():
    mapping = _SafeMapping({"name": "Alice"})
    assert mapping["name"] == "Alice"


def test_safe_mapping_key_absent_with_resolver():
    mapping = _SafeMapping({}, resolve_key)
    assert mapping["missing"] == "resolved(missing)"


def test_safe_mapping_key_absent_no_resolver():
    mapping = _SafeMapping({})
    assert mapping["missing"] == "<VARIABLE UNDEFINED: missing>"


def test_safe_mapping_context_takes_precedence_over_resolver():
    def resolver(key):
        return "from_resolver"

    mapping = _SafeMapping({"key": "from_context"}, resolver)
    assert mapping["key"] == "from_context"


def test_safe_mapping_non_string_value_converted():
    mapping = _SafeMapping({"count": 42})
    assert mapping["count"] == "42"


# ---------------------------------------------------------------------------
# render_inline
# ---------------------------------------------------------------------------


def test_render_inline_substitutes_variables():
    result = render_inline("Hello ${name}.", {"name": "Bob"})
    assert result == "Hello Bob."


def test_render_inline_missing_variable_shows_placeholder():
    result = render_inline("Hello ${name}.", {})
    assert result == "Hello <VARIABLE UNDEFINED: name>."


def test_render_inline_uses_resolver():
    result = render_inline("Memory: ${draft_memory}", {}, resolve_key)
    assert result == "Memory: resolved(draft_memory)"


def test_render_inline_escaped_dollar():
    result = render_inline("Price: $$5", {})
    assert result == "Price: $5"
