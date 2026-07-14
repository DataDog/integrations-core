# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.yaml import load_yaml


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_list_of_docs(tmp_path):
    path = tmp_path / "docs.yaml"
    write(path, "- a: 1\n- b: 2\n")

    result = load_yaml(path)

    assert result is not None
    assert result.docs == [{"a": 1}, {"b": 2}]


def test_scalar_returns_none(tmp_path):
    path = tmp_path / "scalar.yaml"
    write(path, "just_a_string")

    assert load_yaml(path) is None


def test_mapping_normalized_to_single_document(tmp_path):
    path = tmp_path / "mapping.yaml"
    write(path, "type: flow\nconfig:\n  name: demo\n  flow: []\n")

    result = load_yaml(path)

    assert result is not None
    assert result.docs == [{"type": "flow", "config": {"name": "demo", "flow": []}}]


def test_yaml_syntax_error_raises(tmp_path):
    path = tmp_path / "broken.yaml"
    write(path, "this: : bad: [")

    with pytest.raises(ConfigError):
        load_yaml(path)


def test_invalid_utf8_raises(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_bytes(b"\xff")

    with pytest.raises(ConfigError, match="not valid UTF-8"):
        load_yaml(path)
