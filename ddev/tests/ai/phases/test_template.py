# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from ddev.ai.phases.template import render_prompt


def _write(tmp_path, name: str, content: str):
    p = tmp_path / name
    p.write_text(content)
    return p


def test_plain_text_is_returned_unchanged(tmp_path):
    p = _write(tmp_path, "t.md", "Hello, world!")
    assert render_prompt(p, {}) == "Hello, world!"


def test_variable_is_substituted(tmp_path):
    p = _write(tmp_path, "t.md", "Project: {{ project_name }}")
    assert render_prompt(p, {"project_name": "myapp"}) == "Project: myapp"


def test_undefined_variable_renders_as_empty_string(tmp_path):
    p = _write(tmp_path, "t.md", "Value: {{ does_not_exist }}")
    result = render_prompt(p, {})
    assert result == "Value: "


def test_nested_dict_access(tmp_path):
    p = _write(tmp_path, "t.md", "Name: {{ metadata.project }}")
    result = render_prompt(p, {"metadata": {"project": "openmetrics"}})
    assert result == "Name: openmetrics"


def test_unused_context_variables_are_ignored(tmp_path):
    p = _write(tmp_path, "t.md", "Only uses: {{ used }}")
    result = render_prompt(p, {"used": "this", "ignored": "that", "also_ignored": 42})
    assert result == "Only uses: this"


def test_multiple_variables_substituted(tmp_path):
    p = _write(tmp_path, "t.md", "{{ a }} and {{ b }}")
    assert render_prompt(p, {"a": "foo", "b": "bar"}) == "foo and bar"
