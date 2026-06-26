# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.md import parse_md_file


def test_parse_md_file_splits_front_matter_and_body(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("---\ntype: agent\nmodel: x\n---\nHello body\n")
    meta, body = parse_md_file(f)
    assert meta == {"type": "agent", "model": "x"}
    assert body == "Hello body"


def test_parse_md_file_missing_front_matter(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("no front matter")
    try:
        parse_md_file(f)
        raise AssertionError("expected FlowConfigError")
    except FlowConfigError:
        pass
