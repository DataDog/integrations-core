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


def test_empty_file_returns_none(tmp_path):
    path = tmp_path / "empty.md"
    write(path, "")

    assert parse_markdown(path) is None


@pytest.mark.parametrize(
    "body_text, expected_body",
    [
        ("\n\n  Hello.  \n\n", "Hello."),
        ("\n", ""),
        ("", ""),
    ],
)
def test_body_extracted_and_stripped(tmp_path, body_text, expected_body):
    path = tmp_path / "spaced.md"
    write(path, f"---\nname: x\n---{body_text}")

    result = parse_markdown(path)

    assert result is not None
    assert result.meta == {"name": "x"}
    assert result.body == expected_body


def test_invalid_yaml_front_matter_raises(tmp_path):
    path = tmp_path / "invalid.md"
    write(path, "---\nthis: : bad: [\n---\nbody\n")

    with pytest.raises(ConfigError):
        parse_markdown(path)


def test_unreadable_file_raises(tmp_path):
    path = tmp_path / "missing.md"

    with pytest.raises(ConfigError):
        parse_markdown(path)
