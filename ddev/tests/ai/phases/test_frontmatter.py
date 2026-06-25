# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.phases.config import FlowConfigError
from ddev.ai.phases.config import parse_md_file


def test_parse_md_file_returns_front_matter_and_body(tmp_path):
    f = tmp_path / "agent.md"
    f.write_text("---\ntype: agent\nmodel: claude-3\n---\n\nYou are a writer.")
    meta, body = parse_md_file(f)
    assert meta == {"type": "agent", "model": "claude-3"}
    assert body == "You are a writer."


def test_parse_md_file_strips_body_whitespace(tmp_path):
    f = tmp_path / "agent.md"
    f.write_text("---\ntype: agent\n---\n\n\nBody text.\n\n")
    _, body = parse_md_file(f)
    assert body == "Body text."


def test_parse_md_file_empty_body(tmp_path):
    f = tmp_path / "agent.md"
    f.write_text("---\ntype: agent\n---\n")
    _, body = parse_md_file(f)
    assert body == ""


def test_parse_md_file_missing_front_matter_raises(tmp_path):
    f = tmp_path / "agent.md"
    f.write_text("No front matter here.")
    with pytest.raises(FlowConfigError, match="missing YAML front matter"):
        parse_md_file(f)


def test_parse_md_file_invalid_yaml_raises(tmp_path):
    f = tmp_path / "agent.md"
    f.write_text("---\n: bad: [yaml\n---\nBody.")
    with pytest.raises(FlowConfigError, match="Invalid YAML"):
        parse_md_file(f)


def test_parse_md_file_missing_file_raises(tmp_path):
    with pytest.raises(FlowConfigError, match="Cannot read"):
        parse_md_file(tmp_path / "nonexistent.md")
