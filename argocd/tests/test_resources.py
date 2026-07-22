# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from unittest.mock import patch

import pytest

from datadog_checks.argocd.resources_constants import (
    APPLICATION_INCLUDE,
    CLUSTER_INCLUDE,
    GENRESOURCES_API_UP_METRIC,
    REPOSITORY_INCLUDE,
)
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev.http import MockResponse

from . import common

pytestmark = pytest.mark.unit

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


def _items_response(items: list[dict], status_code: int = 200) -> MockResponse:
    return MockResponse(json_data={"items": items}, status_code=status_code)


def build_check(**overrides):
    # These tests drive the REST/polling path; disable streaming so collect() never spawns a listener thread.
    overrides.setdefault("genresources_stream_applications_enabled", False)
    return common.build_check(**overrides)


def test_collect_emits_applications_clusters_and_repositories(aggregator, mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([_cluster("https://cluster-a.example")])],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    by_type = {call.kwargs["type"]: call.kwargs for call in submit.call_args_list}
    assert by_type["argocd_application"]["key"] == "argocd.example.com|argocd|checkout"
    assert by_type["argocd_cluster"]["key"] == "argocd.example.com|https://cluster-a.example"
    assert by_type["argocd_repository"]["key"] == "argocd.example.com|https://github.com/team/repo"
    for spec_type in ("argocd_application", "argocd_cluster", "argocd_repository"):
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


def test_application_include_adds_pilot_metadata_and_state_fields():
    assert {
        "metadata.uid",
        "metadata.creationTimestamp",
        "status.health.lastTransitionTime",
        "status.operationState.retryCount",
    } <= set(APPLICATION_INCLUDE["paths"])


def test_application_include_contains_deployment_history_and_operation_fields():
    assert {
        "status.operationState.message",
        "status.summary.externalURLs[*]",
        "status.history[*].source.repoURL",
        "status.history[*].source.path",
        "status.history[*].sources[*].repoURL",
        "status.history[*].revisions[*]",
    } <= set(APPLICATION_INCLUDE["paths"])


def test_collect_scrubs_credentials_from_operation_state_message(mock_http_response_per_endpoint):
    app = _application("broken")
    app["status"]["operationState"] = {
        "phase": "Failed",
        "message": "sync failed: https://oauth2:t0ken@github.com/org/repo: auth required",
    }
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    app_call = next(c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application")
    message = app_call.kwargs["fields"]["status"]["operationState"]["message"]
    assert "t0ken" not in message
    assert "https://github.com/org/repo" in message


def test_collect_strips_credentials_from_external_urls(mock_http_response_per_endpoint):
    app = _application("web")
    app["status"]["summary"] = {"externalURLs": ["https://user:t0ken@app.example.com"]}
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    app_call = next(c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application")
    assert app_call.kwargs["fields"]["status"]["summary"]["externalURLs"] == ["https://app.example.com"]


def test_real_helper_ships_multisource_history_and_scrubs_its_repo_urls(aggregator, mock_http_response_per_endpoint):
    # Runs the real helper: proves nested [*] (history[*].sources[*]) projects AND history repoURLs are scrubbed.
    app = _application("checkout")
    app["status"]["history"] = [
        {
            "id": 1,
            "source": {"repoURL": "https://oauth2:t0ken@github.com/org/repo", "path": "guestbook"},
            "sources": [{"repoURL": "https://oauth2:t0ken@github.com/org/multi", "path": "base"}],
        }
    ]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check()

    check._resource_collector.collect()

    payloads = aggregator.get_event_platform_events("genresources", parse_json=False)
    blob = b"".join(p if isinstance(p, bytes) else p.encode() for p in payloads)
    assert b"guestbook" in blob  # single-source history field projected
    assert b"base" in blob  # multi-source history field projected (nested [*] works)
    assert b"t0ken" not in blob  # both history repoURLs scrubbed before ship


def test_cluster_include_contains_connection_and_shard_fields():
    assert {
        "connectionState.attemptedAt",
        "info.connectionState.status",
        "shard",
    } <= set(CLUSTER_INCLUDE["paths"])


def test_repository_include_contains_connection_and_capability_flags():
    assert {
        "connectionState.attemptedAt",
        "insecure",
        "enableLfs",
        "enableOCI",
        "forceHttpBasicAuth",
    } <= set(REPOSITORY_INCLUDE["paths"])


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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    keys = {c.kwargs["key"] for c in submit.call_args_list if c.kwargs["type"] == "argocd_application"}
    assert keys == {"argocd.example.com|team-a|web", "argocd.example.com|team-b|web"}


def test_collect_appends_extra_include_paths_to_every_type(mock_http_response_per_endpoint):
    extra = ["metadata.generation"]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([_cluster("https://cluster-a.example")])],
            REPOSITORIES_URL: [_items_response([_repository("https://github.com/team/repo")])],
        }
    )
    check = build_check(genresources_extra_include_paths=extra)

    with patch.object(check, "submit_generic_resource") as submit:
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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
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
    check = build_check(genresources_max_resources_per_cycle=3)

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    application_emits = [c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application"]
    assert len(application_emits) == 3
    warning_messages = [rec.message for rec in caplog.records if "volume cap hit" in rec.message]
    assert warning_messages, "expected a volume-cap warning"
    warning = warning_messages[0]
    assert "type=argocd_application" in warning
    assert "fetched 7" in warning
    assert "capped at 3" in warning


def test_collect_logs_submit_failures_distinctly_from_malformed(mock_http_response_per_endpoint, caplog):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check()

    with patch.object(check, "submit_generic_resource", side_effect=RuntimeError("helper boom")):
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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    by_type = {c.kwargs["type"]: c.kwargs for c in submit.call_args_list}
    assert by_type["argocd_application"]["fields"]["spec"]["source"]["repoURL"] == "https://github.com/org/repo"
    assert by_type["argocd_repository"]["fields"]["repo"] == "https://github.com/org/repo"
    assert by_type["argocd_repository"]["key"] == "argocd.example.com|https://github.com/org/repo"


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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    app_call = next(c for c in submit.call_args_list if c.kwargs["type"] == "argocd_application")
    conditions = app_call.kwargs["fields"]["status"]["conditions"]
    assert conditions[0]["type"] == "ComparisonError"
    assert "t0ken" not in conditions[0]["message"]
    assert "https://github.com/org/repo" in conditions[0]["message"]


def test_collect_scrubs_credentials_from_cluster_connection_state(mock_http_response_per_endpoint):
    cluster = _cluster("https://cluster-a.example")
    cluster["connectionState"] = {
        "status": "Failed",
        "message": "dial https://oauth2:t0ken@cluster-a.example: connection refused",
    }
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([])],
            CLUSTERS_URL: [_items_response([cluster])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    cluster_call = next(c for c in submit.call_args_list if c.kwargs["type"] == "argocd_cluster")
    connection = cluster_call.kwargs["fields"]["connectionState"]
    assert connection["status"] == "Failed"
    assert "t0ken" not in connection["message"]
    assert "https://cluster-a.example" in connection["message"]


def test_collect_emits_api_up_zero_when_endpoint_missing(aggregator, mock_http_response_per_endpoint, caplog):
    captured = mock_http_response_per_endpoint({})
    check = build_check(genresources_endpoint=None)

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    assert submit.call_count == 0
    assert captured.call_count == 0  # no HTTP calls attempted when the endpoint is unset
    for resource_type in ("argocd_application", "argocd_cluster", "argocd_repository"):
        aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=0, tags=[f"resource_type:{resource_type}"])
    assert any(
        "collect_genresources is enabled but genresources_endpoint is not set" in rec.message for rec in caplog.records
    )


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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector._last_app_poll = 0.0  # simulate the application poll interval elapsing
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
    check = build_check()

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector._last_app_poll = 0.0  # simulate the application poll interval elapsing
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
    check = build_check()
    collector = check._resource_collector

    with patch.object(check, "submit_generic_resource") as submit:
        collector.collect()
        after_first = submit.call_count
        collector._last_app_full = 0.0  # force the next cycle to be a full TTL-refresh scrape
        collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 2  # the full scrape re-submits even unchanged resources to refresh their TTL


def test_collect_respects_application_poll_interval(mock_http_response_per_endpoint):
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
    check = build_check()  # streaming off; default 120s application poll, 600s full scrape

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()
        after_first = submit.call_count
        check._resource_collector.collect()
        after_second = submit.call_count

    assert after_first == 1
    assert after_second == 1  # second call is within both intervals -> app not re-fetched, changed v2 never seen


def _application_include(submit) -> dict:
    return next(c.kwargs["include"] for c in submit.call_args_list if c.kwargs["type"] == "argocd_application")


def test_collect_excludes_listed_leaf_path_from_allow_list(mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check(genresources_exclude_paths=["status.conditions[*].message"])

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    paths = _application_include(submit)["paths"]
    assert "status.conditions[*].message" not in paths
    assert "status.conditions[*].type" in paths  # sibling leaf is untouched


def test_collect_exclude_drops_whole_subtree_given_parent_path(mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check(genresources_exclude_paths=["status.history"])

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    paths = _application_include(submit)["paths"]
    assert not any(p.startswith("status.history") for p in paths)
    assert "status.sync.status" in paths  # unrelated path is retained


def test_collect_exclude_removes_map_path(mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check(genresources_exclude_paths=["metadata.labels"])

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    assert _application_include(submit)["map_paths"] == []


def test_collect_exclude_overrides_extra_include_path(mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([_application("checkout")])],
            CLUSTERS_URL: [_items_response([])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check(
        genresources_extra_include_paths=["metadata.generation"],
        genresources_exclude_paths=["metadata.generation"],
    )

    with patch.object(check, "submit_generic_resource") as submit:
        check._resource_collector.collect()

    assert "metadata.generation" not in _application_include(submit)["paths"]


def test_real_helper_strips_secrets_and_excluded_fields(aggregator, mock_http_response_per_endpoint):
    # Exercises the real submit_generic_resource (unmocked): proves the allow-list projection strips
    # secrets and that genresources_exclude_paths actually removes a field from the shipped payload.
    cluster = _cluster("https://k8s.example", name="prod")
    cluster["config"] = {"bearerToken": "SUPERSECRETTOKEN"}  # config is not in CLUSTER_INCLUDE
    cluster["annotations"] = {  # how GitOps stores it: the whole manifest, token and all
        "kubectl.kubernetes.io/last-applied-configuration": '{"config":{"bearerToken":"SUPERSECRETTOKEN"}}'
    }
    cluster["connectionState"] = {"status": "Successful", "message": ""}
    app = _application("checkout")
    app["status"]["conditions"] = [{"type": "ComparisonError", "message": "EXCLUDEDMARKER"}]
    mock_http_response_per_endpoint(
        {
            APPLICATIONS_URL: [_items_response([app])],
            CLUSTERS_URL: [_items_response([cluster])],
            REPOSITORIES_URL: [_items_response([])],
        }
    )
    check = build_check(genresources_exclude_paths=["status.conditions"])

    check._resource_collector.collect()

    blob = b"".join(
        p if isinstance(p, bytes) else p.encode()
        for p in aggregator.get_event_platform_events("genresources", parse_json=False)
    )
    assert b"checkout" in blob  # the application shipped
    assert b"https://k8s.example" in blob  # the cluster shipped
    assert b"SUPERSECRETTOKEN" not in blob  # allow-list dropped config + the last-applied-config annotation
    assert b"EXCLUDEDMARKER" not in blob  # genresources_exclude_paths dropped status.conditions


def test_collector_warns_when_exclude_empties_a_type(caplog):
    nuke = list(CLUSTER_INCLUDE["paths"]) + list(CLUSTER_INCLUDE["map_paths"])
    build_check(genresources_exclude_paths=nuke)
    assert any("emptied the allow-list for argocd_cluster" in rec.message for rec in caplog.records)


def test_collector_warns_when_ttl_shorter_than_longest_scrape_interval(caplog):
    build_check(genresources_ttl_seconds=100, genresources_application_full_scrape_interval_seconds=600)
    assert any("shorter than the longest scrape interval" in rec.message for rec in caplog.records)


def test_fetch_adds_bearer_via_extra_headers_so_configured_auth_is_preserved():
    check = build_check(genresources_auth_token="tok")
    with patch.object(RequestsWrapper, "get", return_value=MockResponse(json_data={"items": []})) as get:
        check._resource_collector._fetch("/api/v1/applications")

    kwargs = get.call_args.kwargs
    assert kwargs.get("extra_headers") == {"Authorization": "Bearer tok"}  # merged into configured headers
    assert "headers" not in kwargs  # never pass `headers`; it would shadow the HTTP client's configured auth


def test_fetch_inherits_http_client_auth_when_no_genresources_token():
    check = build_check(genresources_auth_token=None)  # rely on the instance's HTTP auth (headers / auth_token)
    with patch.object(RequestsWrapper, "get", return_value=MockResponse(json_data={"items": []})) as get:
        check._resource_collector._fetch("/api/v1/applications")

    kwargs = get.call_args.kwargs
    assert "headers" not in kwargs  # must not clobber the HTTP client's configured headers
    assert (
        "extra_headers" not in kwargs
    )  # omit entirely -- even empty extra_headers would drop the inherited auth_token
