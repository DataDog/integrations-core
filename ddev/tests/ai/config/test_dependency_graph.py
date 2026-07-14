# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.config.dependency_graph import detect_cycles, topological_sort
from ddev.ai.config.models import FlowEntry


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


def test_detect_cycles_finds_two_independent_cycles():
    """Two disjoint cycles that share no edges are both reported, not just one."""
    # dependency edges: p1 -> p3 -> p2 -> p1 and p1 -> p4 -> p2 -> p1
    graph = {"p1": ["p3", "p4"], "p2": ["p1"], "p3": ["p2"], "p4": ["p2"]}
    cycles, truncated = detect_cycles(graph)
    assert truncated is False
    assert ["p1", "p3", "p2", "p1"] in cycles
    assert ["p1", "p4", "p2", "p1"] in cycles
    assert len(cycles) == 2


def test_topological_sort_is_stable():
    """Independent phases keep their original declaration order; deps still come first."""
    flow = [
        FlowEntry(phase="p2", dependencies=["p1"]),
        FlowEntry(phase="p3"),
        FlowEntry(phase="p1"),
    ]
    # p1 must precede p2; p3 has no constraints so it stays as early as its declaration allows.
    ordered = topological_sort(flow)
    assert [entry.phase for entry in ordered] == ["p3", "p1", "p2"]
