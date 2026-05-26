# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# TODO: once the helper PR is released and the ``datadog-checks-base`` pin in
# ``pyproject.toml`` resolves to a version that ships ``submit_generic_resource``,
# drop ``create=True`` on the ``patch.object`` calls below and add at least one
# end-to-end test that lets the real helper run and asserts on the captured
# event-platform payload via
# ``aggregator.get_event_platform_events("genresources", parse_json=False)``.
# That catches ``redact=`` signature drift, redaction-contract regressions, and
# proto serialization failures that the current mocks cannot see.

from __future__ import annotations

from unittest.mock import patch

from datadog_checks.argocd import ArgocdCheck
from datadog_checks.argocd.resources import (
    APPLICATION_REDACTION_PATHS,
    CLUSTER_REDACTION_PATHS,
    GENRESOURCES_API_UP_METRIC,
    REPOSITORY_REDACTION_PATHS,
)
from datadog_checks.dev.http import MockResponse

ARGOCD_ENDPOINT = "https://argocd.example.com"
APPLICATIONS_URL = f"{ARGOCD_ENDPOINT}/api/v1/applications"
CLUSTERS_URL = f"{ARGOCD_ENDPOINT}/api/v1/clusters"
REPOSITORIES_URL = f"{ARGOCD_ENDPOINT}/api/v1/repositories"


def _application(name: str, *, namespace: str = "argocd", cluster: str = "https://kubernetes.default.svc") -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"destination": {"server": cluster, "namespace": namespace}, "source": {}},
        "status": {"sync": {"status": "Synced"}},
    }


def _cluster(server: str, *, name: str = "prod", username: str = "", password: str = "") -> dict:
    return {
        "server": server,
        "name": name,
        "config": {"username": username, "password": password},
    }


def _repository(repo: str, *, username: str = "", password: str = "", ssh_key: str = "") -> dict:
    return {"repo": repo, "username": username, "password": password, "sshPrivateKey": ssh_key, "type": "git"}


def _instance(**overrides) -> dict:
    instance = {
        "app_controller_endpoint": "http://app_controller:8082",
        "collect_genresources": True,
        "generic_resources_endpoint": ARGOCD_ENDPOINT,
        "generic_resources_auth_token": "test-token",
    }
    instance.update(overrides)
    return instance


def _items_response(items: list[dict], status_code: int = 200) -> MockResponse:
    return MockResponse(json_data={"items": items}, status_code=status_code)


def test_collect_emits_applications_clusters_and_repositories(aggregator, mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([_cluster("https://cluster-a.example")])],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    by_type = {call.kwargs["type"]: call.kwargs for call in submit.call_args_list}
    assert by_type["argocd_application"]["key"] == "https://kubernetes.default.svc:argocd:checkout"
    assert by_type["argocd_cluster"]["key"] == "https://cluster-a.example"
    assert by_type["argocd_repository"]["key"] == "https://github.com/team/repo"
    for spec_type, redact_paths in (
        ("argocd_application", APPLICATION_REDACTION_PATHS),
        ("argocd_cluster", CLUSTER_REDACTION_PATHS),
        ("argocd_repository", REPOSITORY_REDACTION_PATHS),
    ):
        assert by_type[spec_type]["redact"]["paths"][: len(redact_paths)] == list(redact_paths)
        aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=1, tags=[f"resource_type:{spec_type}"])


def test_collect_appends_extra_redaction_paths_to_every_type(mock_http_response_per_endpoint):
    extra = ["spec.source.helm.fileParameters[*].value"]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([_cluster("https://cluster-a.example")])],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance(extra_redaction_paths=extra)])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    for call in submit.call_args_list:
        assert call.kwargs["redact"]["paths"][-1] == extra[0]


def test_collect_isolates_per_endpoint_failures(aggregator, mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([], status_code=403)],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    emitted_types = {call.kwargs["type"] for call in submit.call_args_list}
    assert emitted_types == {"argocd_application", "argocd_repository"}
    aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=1, tags=["resource_type:argocd_application"])
    aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=0, tags=["resource_type:argocd_cluster"])
    aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=1, tags=["resource_type:argocd_repository"])


def test_collect_skips_malformed_items_without_poisoning_cycle(mock_http_response_per_endpoint, caplog):
    malformed = {"spec": {}}
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout"), malformed, _application("payments")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    application_emits = [c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application"]
    assert len(application_emits) == 2
    assert any("skipping malformed argocd_application" in rec.message for rec in caplog.records)


def test_collect_caps_per_type_with_warning(mock_http_response_per_endpoint, caplog):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application(f"app-{i}") for i in range(7)])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance(max_resources_per_cycle=3)])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    application_emits = [c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application"]
    assert len(application_emits) == 3
    assert any("volume cap hit" in rec.message and "argocd_application" in rec.message for rec in caplog.records)
