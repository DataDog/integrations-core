# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.base.utils.genresources import INCLUDE_ALL, GenericResourceEvent

VALUE_INCLUDE = {"paths": ["metadata.name"], "map_paths": [], "annotation_keys": []}


@pytest.fixture
def check():
    return AgentCheck("argocd", {}, [{}])


def _decode(payload: bytes) -> GenericResourceEvent:
    event = GenericResourceEvent()
    event.ParseFromString(payload)
    return event


def test_submit_generic_resource_emits_expected_event(aggregator, check):
    check.submit_generic_resource(
        type="argocd_application",
        key="cluster:argocd:guestbook",
        fields={
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
            "status": {"health": {"status": "Healthy"}, "sync": {"status": "Synced"}},
        },
        include={
            "paths": [
                "metadata.name",
                "metadata.namespace",
                "spec.project",
                "spec.sources[*].repoURL",
                "spec.sources[*].path",
                "status.health.status",
            ],
            "map_paths": ["metadata.labels"],
            "annotation_keys": ["owner"],
        },
        seen_at=1700000000,
        expire_at=1700021600,
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    event = _decode(payload)
    assert event.source == "integrations-core"
    assert event.resource.type == "argocd_application"
    assert event.resource.key == "cluster:argocd:guestbook"
    assert event.resource.seen_at.seconds == 1700000000
    assert event.resource.expire_at.seconds == 1700021600
    assert json.loads(event.resource.fields_json) == {
        "metadata": {
            "name": "guestbook",
            "namespace": "argocd",
            "labels": {"team": "platform", "env": "prod"},
            "annotations": {"owner": "team-a"},
        },
        "spec": {
            "project": "default",
            "sources": [{"repoURL": "https://a", "path": "p1"}, {"repoURL": "https://b", "path": "p2"}],
        },
        "status": {"health": {"status": "Healthy"}},
    }
    datadog_agent.assert_telemetry("argocd", "datadog.agent.check.genresources.emitted", "count", 1)


def test_submit_generic_resource_given_include_all_ships_constructed_fields(aggregator, check):
    check.submit_generic_resource(
        type="sonarqube_project",
        key="my-proj",
        fields={"name": "my-proj", "quality_gate": "OK", "ncloc": 1234},
        include=INCLUDE_ALL,
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    event = _decode(payload)
    assert event.resource.type == "sonarqube_project"
    assert json.loads(event.resource.fields_json) == {"name": "my-proj", "quality_gate": "OK", "ncloc": 1234}


@pytest.mark.parametrize(
    "kwargs, expected_log",
    [
        (
            {"type": "t", "key": "", "fields": {"metadata": {"name": "x"}}, "include": VALUE_INCLUDE},
            "empty key",
        ),
        (
            {"type": "", "key": "k", "fields": {"metadata": {"name": "x"}}, "include": VALUE_INCLUDE},
            "empty type",
        ),
        (
            {"type": "t", "key": "k", "fields": ["not", "a", "dict"], "include": VALUE_INCLUDE},
            "non-dict fields",
        ),
        (
            {"type": "t", "key": "k", "fields": {"metadata": {"name": "x"}}, "include": None},
            "non-dict include",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"metadata": {"name": "x"}},
                "include": {"paths": "metadata.name", "map_paths": [], "annotation_keys": []},
            },
            "malformed include",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"metadata": {"name": "x"}},
                "include": {"paths": [], "map_paths": [], "annotation_keys": ["*"]},
            },
            "catch-all annotation pattern",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"spec": {"project": "p"}},
                "include": {"paths": ["spec"], "map_paths": [], "annotation_keys": []},
            },
            "nested include value",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"spec": {"source": {"repoURL": "r", "helm": {"x": 1}}}},
                "include": {"paths": [], "map_paths": ["spec.source"], "annotation_keys": []},
            },
            "non-flat map_path",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"metadata": {"name": "x"}},
                "include": {"paths": ["does.not.exist"], "map_paths": [], "annotation_keys": []},
            },
            "empty inclusion",
        ),
        (
            {
                "type": "t",
                "key": "k",
                "fields": {"spec": {"ratio": float("nan")}},
                "include": {"paths": ["spec.ratio"], "map_paths": [], "annotation_keys": []},
            },
            "failed to encode fields",
        ),
        (
            {"type": "t", "key": "k", "fields": {"metadata": {"name": "x" * 2_000_000}}, "include": VALUE_INCLUDE},
            "oversize resource",
        ),
    ],
    ids=[
        "empty_key",
        "empty_type",
        "non_dict_fields",
        "non_dict_include",
        "malformed_include",
        "catch_all_annotation",
        "nested_object_include",
        "invalid_map_path",
        "empty_inclusion",
        "nan_value",
        "oversize_payload",
    ],
)
def test_submit_generic_resource_drops_and_counts_invalid_input(aggregator, check, caplog, kwargs, expected_log):
    check.submit_generic_resource(**kwargs)
    assert aggregator.get_event_platform_events("genresources", parse_json=False) == []
    datadog_agent.assert_telemetry("argocd", "datadog.agent.check.genresources.dropped", "count", 1)
    assert any(expected_log in record.getMessage() for record in caplog.records)


def test_submit_generic_resource_ignores_non_int_timestamps(aggregator, check):
    check.submit_generic_resource(
        type="argocd_application",
        key="k",
        fields={"metadata": {"name": "x"}},
        include=VALUE_INCLUDE,
        seen_at=1700000000.9,
        expire_at=1700000000.5,
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    event = _decode(payload)
    assert event.resource.seen_at.seconds == 0
    assert event.resource.expire_at.seconds == 0
