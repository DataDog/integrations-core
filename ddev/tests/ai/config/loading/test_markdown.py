# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.markdown import parse_markdown


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_front_matter_parsed(tmp_path):
    path = tmp_path / "agent.md"
    write(path, "---\nname: my-agent\ntype: agent\nmodel: sonnet\n---\nHello there.\n")

    result = parse_markdown(path)

    assert result is not None
    assert result.meta == {"name": "my-agent", "type": "agent", "model": "sonnet"}
    assert result.body == "Hello there."


def test_no_front_matter_returns_none(tmp_path):
    path = tmp_path / "plain.md"
    write(path, "no front matter")

    assert parse_markdown(path) is None


def test_unclosed_front_matter_raises(tmp_path):
    path = tmp_path / "broken.md"
    write(path, "---\n")

    with pytest.raises(ConfigError):
        parse_markdown(path)


def test_invalid_yaml_front_matter_raises(tmp_path):
    path = tmp_path / "invalid.md"
    write(path, "---\nthis: : bad: [\n---\nbody\n")

    with pytest.raises(ConfigError):
        parse_markdown(path)


def test_non_mapping_front_matter_raises(tmp_path):
    path = tmp_path / "list.md"
    write(path, "---\n- a\n- b\n---\nbody")

    with pytest.raises(ConfigError):
        parse_markdown(path)


def test_body_whitespace_stripped(tmp_path):
    path = tmp_path / "spaced.md"
    write(path, "---\nname: x\n---\n\n  Hello.  \n\n")

    result = parse_markdown(path)

    assert result.body == "Hello."


def test_empty_body(tmp_path):
    path = tmp_path / "empty.md"
    write(path, "---\nname: x\n---\n")

    result = parse_markdown(path)

    assert result.body == ""


def test_closing_delimiter_without_trailing_newline(tmp_path):
    path = tmp_path / "no_trailing.md"
    write(path, "---\ntype: agent\n---")

    result = parse_markdown(path)

    assert result.meta == {"type": "agent"}
    assert result.body == ""


def test_name_surfaced_in_meta(tmp_path):
    path = tmp_path / "named.md"
    write(path, "---\nname: my-model-key\n---\nbody")

    result = parse_markdown(path)

    assert result.meta["name"] == "my-model-key"
