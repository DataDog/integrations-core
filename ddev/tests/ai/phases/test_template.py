# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

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


def test_render_inline_renders_objects_as_compact_json():
    result = render_inline(
        "Endpoint: ${endpoint}",
        {"endpoint": {"url": "https://example.test", "enabled": "true"}},
    )

    assert result == 'Endpoint: {"url":"https://example.test","enabled":"true"}'


def test_render_inline_preserves_unicode_and_escapes_object_json():
    result = render_inline(
        "Endpoint: ${endpoint}",
        {"endpoint": {"label": 'café "primary"\nline'}},
    )

    assert result == 'Endpoint: {"label":"café \\"primary\\"\\nline"}'


def test_render_inline_supports_one_level_braced_object_field_access():
    result = render_inline(
        "URL: ${endpoint.url}",
        {"endpoint": {"url": "https://example.test"}},
    )

    assert result == "URL: https://example.test"


@pytest.mark.parametrize("prompt", ["Tags: ${tags}", "Name: ${endpoints.name}"])
def test_render_inline_rejects_multi_value_interpolation(prompt):
    with pytest.raises(ValueError, match="List variable .* cannot be rendered"):
        render_inline(prompt, {"tags": ["api", "worker"], "endpoints": [{"name": "api"}]})


@pytest.mark.parametrize(
    ("prompt", "context", "message"),
    [
        ("${endpoint.url}", {}, "Object variable 'endpoint' is missing"),
        ("${endpoint.url}", {"endpoint": "scalar"}, "Variable 'endpoint' is not an object"),
        ("${endpoint.url}", {"endpoint": {}}, "Object field 'endpoint.url' is missing"),
        (
            "${endpoint.url.scheme}",
            {"endpoint": {"url": "https://example.test"}},
            "Invalid placeholder",
        ),
    ],
)
def test_render_inline_rejects_invalid_object_field_access(prompt, context, message):
    with pytest.raises(ValueError, match=message):
        render_inline(prompt, context)


def test_render_inline_does_not_treat_unbraced_dots_as_object_access():
    result = render_inline(
        "$endpoint.url",
        {"endpoint": {"url": "https://example.test"}},
    )

    assert result == '{"url":"https://example.test"}.url'
