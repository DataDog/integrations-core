# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

import pytest

from ddev.ai.config.classify import classify
from ddev.ai.config.loading.files import MarkdownFile, YamlFile
from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig
from ddev.ai.config.registry import BrokenEntry, ValidEntry

PATH = Path("/x/a.md")
YAML_PATH = Path("/x/a.yaml")


def test_markdown_agent_happy_path():
    md = MarkdownFile(path=PATH, meta={"type": "agent", "name": "a", "model": "m"}, body="sys")
    output = classify(md)

    assert not output.file_errors
    (entry,) = output.entries
    assert isinstance(entry, ValidEntry)
    assert entry.kind == "agent"
    assert entry.name == "a"
    assert entry.source_file == PATH
    assert isinstance(entry.config, AgentConfig)
    assert entry.config.system_prompt == "sys"
    assert entry.config.model == "m"


@pytest.mark.parametrize("type_", ["prompt", "goal", "memory_prompt"])
def test_markdown_body_bearing_happy_path(type_):
    md = MarkdownFile(path=PATH, meta={"type": type_, "name": "n"}, body="the body")
    output = classify(md)

    assert not output.file_errors
    (entry,) = output.entries
    assert isinstance(entry, ValidEntry)
    assert entry.kind == type_
    assert entry.name == "n"
    assert entry.config == "the body"


def test_markdown_without_type_skipped_silently():
    md = MarkdownFile(path=PATH, meta={"name": "a"}, body="sys")
    output = classify(md)

    assert output.entries == []
    assert output.file_errors == []


def test_markdown_unknown_type_is_file_error():
    md = MarkdownFile(path=PATH, meta={"type": "bogus", "name": "a"}, body="sys")
    output = classify(md)

    assert output.entries == []
    (error,) = output.file_errors
    assert error.path == PATH
    assert "bogus" in error.message


@pytest.mark.parametrize("type_", ["phase", "flow"])
def test_markdown_with_yaml_only_type_is_file_error(type_):
    md = MarkdownFile(path=PATH, meta={"type": type_, "name": "a"}, body="sys")
    output = classify(md)

    assert output.entries == []
    (error,) = output.file_errors
    assert type_ in error.message
    assert "not valid in a Markdown file" in error.message


def test_markdown_missing_name_is_file_error():
    md = MarkdownFile(path=PATH, meta={"type": "agent"}, body="sys")
    output = classify(md)

    assert output.entries == []
    (error,) = output.file_errors
    assert "missing required 'name'" in error.message


def test_markdown_agent_invalid_field_is_broken_entry():
    md = MarkdownFile(
        path=PATH,
        meta={"type": "agent", "name": "a", "tools": ["nonexistent_tool"]},
        body="sys",
    )
    output = classify(md)

    assert output.file_errors == []
    (entry,) = output.entries
    assert isinstance(entry, BrokenEntry)
    assert entry.kind == "agent"
    assert entry.name == "a"
    assert entry.source_file == PATH
    assert entry.error


def test_yaml_phase_happy_path():
    doc = {"type": "phase", "config": {"name": "p"}}
    yaml_file = YamlFile(path=YAML_PATH, docs=[doc])
    output = classify(yaml_file)

    assert not output.file_errors
    (entry,) = output.entries
    assert isinstance(entry, ValidEntry)
    assert entry.kind == "phase"
    assert entry.name == "p"
    assert isinstance(entry.config, PhaseConfig)


def test_yaml_flow_happy_path():
    doc = {"type": "flow", "config": {"name": "f", "flow": [{"phase": "p"}]}}
    yaml_file = YamlFile(path=YAML_PATH, docs=[doc])
    output = classify(yaml_file)

    assert not output.file_errors
    (entry,) = output.entries
    assert isinstance(entry, ValidEntry)
    assert entry.kind == "flow"
    assert entry.name == "f"
    assert isinstance(entry.config, FlowConfig)


def test_yaml_non_dict_and_typeless_docs_skipped_silently():
    yaml_file = YamlFile(path=YAML_PATH, docs=["not a dict", {"no_type": "here"}])
    output = classify(yaml_file)

    assert output.entries == []
    assert output.file_errors == []


def test_yaml_unknown_type_is_file_error():
    yaml_file = YamlFile(path=YAML_PATH, docs=[{"type": "bogus", "config": {"name": "x"}}])
    output = classify(yaml_file)

    assert output.entries == []
    (error,) = output.file_errors
    assert "item 0:" in error.message
    assert "bogus" in error.message


def test_yaml_markdown_only_type_is_file_error():
    yaml_file = YamlFile(path=YAML_PATH, docs=[{"type": "agent", "name": "a"}])
    output = classify(yaml_file)

    assert output.entries == []
    (error,) = output.file_errors
    assert "item 0:" in error.message
    assert "not valid in a YAML file" in error.message


def test_yaml_named_but_invalid_is_broken_entry():
    doc = {"type": "flow", "config": {"name": "f", "flow": "not-a-list"}}
    yaml_file = YamlFile(path=YAML_PATH, docs=[doc])
    output = classify(yaml_file)

    assert output.file_errors == []
    (entry,) = output.entries
    assert isinstance(entry, BrokenEntry)
    assert entry.kind == "flow"
    assert entry.name == "f"
    assert entry.source_file == YAML_PATH


def test_yaml_nameless_invalid_is_file_error():
    doc = {"type": "phase", "config": "not-a-dict"}
    yaml_file = YamlFile(path=YAML_PATH, docs=[doc])
    output = classify(yaml_file)

    assert output.entries == []
    (error,) = output.file_errors
    assert "item 0:" in error.message


def test_yaml_multiple_docs_produce_indexed_entries_and_errors():
    docs = [
        {"type": "phase", "config": {"name": "p"}},
        {"type": "bogus"},
        {"type": "flow", "config": {"name": "f", "flow": [{"phase": "p"}]}},
    ]
    yaml_file = YamlFile(path=YAML_PATH, docs=docs)
    output = classify(yaml_file)

    assert {(e.kind, e.name) for e in output.entries} == {("phase", "p"), ("flow", "f")}
    (error,) = output.file_errors
    assert "item 1:" in error.message
