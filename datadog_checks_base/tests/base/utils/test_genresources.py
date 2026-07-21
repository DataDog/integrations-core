# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest

from datadog_checks.base.utils.genresources.inclusion import apply_allow_list, find_invalid_include


def _fields():
    return {
        "metadata": {
            "name": "guestbook",
            "namespace": "argocd",
            "labels": {"team": "platform", "env": "prod"},
            "annotations": {"owner": "team-a", "kubectl.kubernetes.io/last-applied-configuration": "SECRET"},
        },
        "spec": {
            "project": "default",
            "source": {"repoURL": "https://repo", "helm": {"valuesObject": "SECRET"}},
            "sources": [
                {"repoURL": "https://a", "path": "p1", "ref": "x"},
                {"repoURL": "https://b", "path": "p2"},
            ],
        },
        "status": {"health": {"status": "Healthy"}},
        "operation": None,
    }


def test_apply_allow_list_given_value_map_and_annotation_includes_returns_only_those():
    result = apply_allow_list(
        _fields(),
        paths=["metadata.name", "spec.project", "status.health.status", "operation", "spec.missing"],
        map_paths=["metadata.labels"],
        annotation_keys=["owner"],
    )
    assert result == {
        "metadata": {
            "name": "guestbook",
            "labels": {"team": "platform", "env": "prod"},
            "annotations": {"owner": "team-a"},
        },
        "spec": {"project": "default"},
        "status": {"health": {"status": "Healthy"}},
        "operation": None,
    }


def test_apply_allow_list_given_two_wildcard_paths_returns_both_fields_per_element():
    result = apply_allow_list(
        _fields(),
        paths=["spec.sources[*].repoURL", "spec.sources[*].path"],
        map_paths=[],
        annotation_keys=[],
    )
    assert result == {
        "spec": {"sources": [{"repoURL": "https://a", "path": "p1"}, {"repoURL": "https://b", "path": "p2"}]}
    }


def test_apply_allow_list_given_partial_wildcard_match_drops_empty_elements():
    fields = {"spec": {"sources": [{"repoURL": "a"}, {"other": "b"}]}}
    result = apply_allow_list(fields, paths=["spec.sources[*].repoURL"], map_paths=[], annotation_keys=[])
    assert result == {"spec": {"sources": [{"repoURL": "a"}]}}


def test_apply_allow_list_given_object_annotation_value_skips_it():
    fields = {"metadata": {"annotations": {"flat": "ok", "obj": {"x": 1}, "arr": [1]}}}
    result = apply_allow_list(fields, paths=[], map_paths=[], annotation_keys=["flat", "obj", "arr"])
    assert result == {"metadata": {"annotations": {"flat": "ok"}}}


def test_apply_allow_list_does_not_mutate_input():
    fields = _fields()
    apply_allow_list(fields, paths=["metadata.name"], map_paths=["metadata.labels"], annotation_keys=["owner"])
    assert fields == _fields()


@pytest.mark.parametrize(
    "paths, map_paths, expected",
    [
        (["metadata.name", "spec.sources[*].repoURL"], [], None),
        (["metadata"], [], ("metadata", "nested include value")),
        (["spec.source"], [], ("spec.source", "nested include value")),
        (["spec.sources[*]"], [], ("spec.sources[*]", "nested include value")),
        ([], ["metadata.labels"], None),
        ([], ["spec.source"], ("spec.source", "non-flat map_path")),
        (["metadata.annotations"], [], None),
    ],
    ids=[
        "value_paths_ok",
        "flat_object_in_paths_rejected",
        "nested_object_in_paths_rejected",
        "array_of_objects_rejected",
        "flat_map_path_ok",
        "nested_map_path_rejected",
        "annotations_path_skipped",
    ],
)
def test_find_invalid_include_enforces_value_and_map_contract(paths, map_paths, expected):
    assert find_invalid_include(_fields(), paths, map_paths) == expected
