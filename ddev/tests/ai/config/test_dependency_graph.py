# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.config.dependency_graph import detect_cycles


def test_detect_cycles_finds_simple_cycle():
    cycles, truncated = detect_cycles({"a": ["b"], "b": ["a"]})
    assert truncated is False
    assert ["a", "b", "a"] in cycles
    assert len(cycles) == 1


def test_detect_cycles_none_when_acyclic():
    cycles, truncated = detect_cycles({"a": ["b"], "b": []})
    assert cycles == []
    assert truncated is False


def test_detect_cycles_finds_self_loop():
    cycles, truncated = detect_cycles({"a": ["a"]})
    assert truncated is False
    assert ["a", "a"] in cycles


def test_detect_cycles_truncates_when_limit_reached():
    # A 3-node fully-connected graph has more simple cycles than this limit.
    graph = {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"]}
    cycles, truncated = detect_cycles(graph, limit=2)
    assert truncated is True
    assert len(cycles) == 2
