# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.config.errors import detect_cycles


def test_detect_cycles_finds_simple_cycle():
    cycles, truncated = detect_cycles({"a": ["b"], "b": ["a"]})
    assert truncated is False
    assert ["a", "b", "a"] in cycles


def test_detect_cycles_none_when_acyclic():
    cycles, truncated = detect_cycles({"a": ["b"], "b": []})
    assert cycles == []
    assert truncated is False
