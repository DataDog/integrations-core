# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from datetime import datetime

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.genresources import GenericResourceEvent

NO_REDACT = {"paths": [], "annotation_keys": []}


@pytest.fixture
def check():
    return AgentCheck("argocd", {}, [{}])


def _decode(payload: bytes) -> GenericResourceEvent:
    event = GenericResourceEvent()
    event.ParseFromString(payload)
    return event


def _valid_fields():
    return {"metadata": {"name": "x"}, "spec": {}, "status": {}, "operation": None}


def test_submit_generic_resource_emits_expected_event(aggregator, check):
    check.submit_generic_resource(
        type="argocd_application",
        key="cluster:ns:name",
        fields=_valid_fields(),
        redact=NO_REDACT,
        seen_at=1700000000,
        expire_at=1700021600,
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    event = _decode(payload)
    assert event.source == "integrations-core"
    assert event.resource.type == "argocd_application"
    assert event.resource.key == "cluster:ns:name"
    assert event.resource.seen_at.seconds == 1700000000
    assert event.resource.expire_at.seconds == 1700021600
    assert json.loads(event.resource.fields_json) == _valid_fields()


def test_submit_generic_resource_applies_caller_provided_deny_list(aggregator, check):
    check.submit_generic_resource(
        type="argocd_application",
        key="k",
        fields={
            "metadata": {
                "annotations": {"kubectl.kubernetes.io/last-applied-configuration": '{"token":"SEEDED-A"}'},
            },
            "spec": {
                "source": {"helm": {"valuesObject": "SEEDED-B"}},
                "sources": [{"plugin": {"env": [{"name": "TOKEN", "value": "SEEDED-C"}]}}],
            },
            "status": {},
            "operation": None,
        },
        redact={
            "paths": ["spec.source.helm.valuesObject", "spec.sources[*].plugin.env[*].value"],
            "annotation_keys": ["*.kubernetes.io/last-applied-configuration"],
        },
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    body = _decode(payload).resource.fields_json.decode()
    for seeded in ("SEEDED-A", "SEEDED-B", "SEEDED-C"):
        assert seeded not in body


@pytest.mark.parametrize(
    "kwargs",
    [
        {"type": "argocd_application", "key": "k", "fields": None, "redact": NO_REDACT},
        {"type": "argocd_application", "key": "", "fields": _valid_fields(), "redact": NO_REDACT},
        {"type": "argocd_application", "key": "k", "fields": ["not", "a", "dict"], "redact": NO_REDACT},
        {
            "type": "argocd_application",
            "key": "k",
            "fields": {"metadata": {"name": "x" * 2_000_000}, "spec": {}, "status": {}, "operation": None},
            "redact": NO_REDACT,
        },
        {
            "type": "argocd_application",
            "key": "k",
            "fields": {"metadata": {}, "spec": {"ts": datetime(2026, 1, 1)}, "status": {}, "operation": None},
            "redact": NO_REDACT,
        },
    ],
    ids=["fields_none", "empty_key", "non_dict_fields", "oversize_payload", "non_serializable_value"],
)
def test_submit_generic_resource_drops_invalid_input(aggregator, check, kwargs):
    check.submit_generic_resource(**kwargs)
    assert aggregator.get_event_platform_events("genresources", parse_json=False) == []


def test_submit_generic_resource_ignores_non_int_timestamps(aggregator, check):
    check.submit_generic_resource(
        type="argocd_application",
        key="k",
        fields=_valid_fields(),
        redact=NO_REDACT,
        seen_at=1700000000.9,
        expire_at=1700000000.5,
    )

    [payload] = aggregator.get_event_platform_events("genresources", parse_json=False)
    event = _decode(payload)
    assert event.resource.seen_at.seconds == 0
    assert event.resource.expire_at.seconds == 0
