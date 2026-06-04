# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# TODO: once the helper PR is released and the ``datadog-checks-base`` pin in
# ``pyproject.toml`` resolves to a version that ships ``submit_generic_resource``,
# drop ``create=True`` on the ``patch.object`` calls below and add at least one
# end-to-end test that lets the real helper run and asserts on the captured
# event-platform payload via
# ``aggregator.get_event_platform_events("genresources", parse_json=False)``.
# That catches ``include=`` signature drift, allow-list projection regressions,
# and proto serialization failures that the current mocks cannot see.

from __future__ import annotations

from unittest.mock import patch

from datadog_checks.argocd import ArgocdCheck
from datadog_checks.argocd.resources import (
    APPLICATION_INCLUDE,
    CLUSTER_INCLUDE,
    GENRESOURCES_API_UP_METRIC,
    REPOSITORY_INCLUDE,
)
from datadog_checks.dev.http import MockResponse

ARGOCD_ENDPOINT = "https://argocd.example.com"
APPLICATIONS_URL = f"{ARGOCD_ENDPOINT}/api/v1/applications"
CLUSTERS_URL = f"{ARGOCD_ENDPOINT}/api/v1/clusters"
REPOSITORIES_URL = f"{ARGOCD_ENDPOINT}/api/v1/repositories"


def _application(
    name: str,
    *,
    namespace: str = "argocd",
    cluster: str = "https://kubernetes.default.svc",
    dest_namespace: str | None = None,
) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"destination": {"server": cluster, "namespace": dest_namespace or namespace}, "source": {}},
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
    assert by_type["argocd_application"]["key"] == "argocd.example.com:argocd:checkout"
    assert by_type["argocd_cluster"]["key"] == "argocd.example.com:https://cluster-a.example"
    assert by_type["argocd_repository"]["key"] == "argocd.example.com:https://github.com/team/repo"
    for spec_type, include in (
        ("argocd_application", APPLICATION_INCLUDE),
        ("argocd_cluster", CLUSTER_INCLUDE),
        ("argocd_repository", REPOSITORY_INCLUDE),
    ):
        forwarded = by_type[spec_type]["include"]
        assert forwarded["paths"] == list(include["paths"])
        assert forwarded["map_paths"] == list(include["map_paths"])
        assert forwarded["annotation_keys"] == list(include["annotation_keys"])
        aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=1, tags=[f"resource_type:{spec_type}"])


def test_application_include_contains_prd_fields_required_for_idp_catalog():
    assert {
        "spec.sources[*].chart",
        "status.conditions[*].lastTransitionTime",
        "status.history[*].id",
        "status.history[*].revision",
        "status.history[*].deployedAt",
        "status.history[*].deployStartedAt",
        "status.history[*].initiatedBy.username",
        "status.history[*].initiatedBy.automated",
        "status.operationState.startedAt",
        "status.operationState.finishedAt",
        "status.summary.images[*]",
    } <= set(APPLICATION_INCLUDE["paths"])


def test_application_include_contains_kubernetes_resource_identity_for_automatic_mapping():
    assert {
        "status.resources[*].group",
        "status.resources[*].version",
        "status.resources[*].requiresPruning",
    } <= set(APPLICATION_INCLUDE["paths"])


def test_application_key_uses_app_identity_not_destination(mock_http_response_per_endpoint):
    apps = [
        _application("web", namespace="team-a", cluster="https://remote", dest_namespace="prod"),
        _application("web", namespace="team-b", cluster="https://remote", dest_namespace="prod"),
    ]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response(apps)],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    keys = {c.kwargs["key"] for c in submit.call_args_list if c.kwargs["type"] == "argocd_application"}
    assert keys == {"argocd.example.com:team-a:web", "argocd.example.com:team-b:web"}


def test_collect_appends_extra_include_paths_to_every_type(mock_http_response_per_endpoint):
    extra = ["metadata.generation"]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([_cluster("https://cluster-a.example")])],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance(extra_include_paths=extra)])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    for call in submit.call_args_list:
        assert call.kwargs["include"]["paths"][-1] == extra[0]


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


def test_collect_logs_submit_failures_distinctly_from_malformed(mock_http_response_per_endpoint, caplog):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True, side_effect=RuntimeError("helper boom")):
        check._resource_collector.collect()

    assert any("failed to submit argocd_application" in rec.message for rec in caplog.records)
    assert not any("skipping malformed" in rec.message for rec in caplog.records)


def test_collect_strips_credentials_from_repo_urls(mock_http_response_per_endpoint):
    app = _application("web")
    app["spec"]["source"] = {"repoURL": "https://user:t0ken@github.com/org/repo"}
    repo = {"repo": "https://user:t0ken@github.com/org/repo", "type": "git"}
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([repo])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    by_type = {c.kwargs["type"]: c.kwargs for c in submit.call_args_list}
    assert by_type["argocd_application"]["fields"]["spec"]["source"]["repoURL"] == "https://github.com/org/repo"
    assert by_type["argocd_repository"]["fields"]["repo"] == "https://github.com/org/repo"
    assert by_type["argocd_repository"]["key"] == "argocd.example.com:https://github.com/org/repo"


def test_collect_scrubs_credentials_from_condition_messages(mock_http_response_per_endpoint):
    app = _application("broken")
    app["status"]["conditions"] = [
        {
            "type": "ComparisonError",
            "message": "failed to fetch https://oauth2:t0ken@github.com/org/repo: auth required",
        }
    ]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()

    app_call = next(c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application")
    conditions = app_call.kwargs["fields"]["status"]["conditions"]
    assert conditions[0]["type"] == "ComparisonError"
    assert "t0ken" not in conditions[0]["message"]
    assert "https://github.com/org/repo" in conditions[0]["message"]


def test_collect_skips_unchanged_resources_on_second_cycle(mock_http_response_per_endpoint):
    app = _application("checkout")
    app["metadata"]["resourceVersion"] = "100"
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector._last_collect = 0.0  # simulate the collection interval elapsing
        check._resource_collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 1  # unchanged app is not re-submitted on the next cycle


def test_collect_resubmits_application_when_resource_version_changes(mock_http_response_per_endpoint):
    app_v1 = _application("checkout")
    app_v1["metadata"]["resourceVersion"] = "100"
    app_v2 = _application("checkout")
    app_v2["metadata"]["resourceVersion"] = "200"
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app_v1]), _items_response([app_v2])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector._last_collect = 0.0  # simulate the collection interval elapsing
        check._resource_collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 2  # resourceVersion changed, so the app is re-submitted


def test_collect_resubmits_unchanged_resources_on_ttl_sweep(mock_http_response_per_endpoint):
    app = _application("checkout")
    app["metadata"]["resourceVersion"] = "100"
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])
    collector = check._resource_collector

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        collector.collect()
        after_first = submit.call_count
        collector._last_full_submit = 0.0  # force the next cycle to be a full TTL-refresh sweep
        collector._last_collect = 0.0
        collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 2  # the sweep re-submits even unchanged resources to refresh their TTL


def test_collect_respects_collection_interval(mock_http_response_per_endpoint):
    app_v1 = _application("checkout")
    app_v1["metadata"]["resourceVersion"] = "100"
    app_v2 = _application("checkout")
    app_v2["metadata"]["resourceVersion"] = "200"
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app_v1]), _items_response([app_v2])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = ArgocdCheck("argocd", {}, [_instance()])  # default 120s collection interval

    with patch.object(check, "submit_generic_resource", create=True) as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 1  # second call is within the interval -> skipped, the changed v2 is never fetched
