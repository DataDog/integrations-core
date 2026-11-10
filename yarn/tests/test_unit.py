# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pytest
from mock import patch
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, SSLError, Timeout

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dev.http import MockResponse
from datadog_checks.yarn import YarnCheck
from datadog_checks.yarn.yarn import (
    APPLICATION_STATUS_SERVICE_CHECK,
    DEFAULT_COLLECT_APP_METRICS,
    DEFAULT_COLLECT_NODE_METRICS,
    DEFAULT_SPLIT_YARN_APPLICATION_TAGS,
    DEFAULT_TIMEOUT,
    GAUGE,
    INCREMENT,
    MAX_DETAILED_QUEUES,
    SERVICE_CHECK_NAME,
    YARN_APPS_PATH,
    YARN_CLUSTER_METRICS_PATH,
    YARN_NODES_PATH,
    YARN_SCHEDULER_PATH,
)

from .common import YARN_CONFIG

pytestmark = pytest.mark.unit


def non_interned(value):
    """Build a string equal in content to `value` but not the same (possibly interned) object."""
    return (value + "x")[:-1]


def stub_get(responses):
    def get(session, url, *args, **kwargs):
        for path, payload in responses.items():
            if url.endswith(path):
                return MockResponse(json_data=payload)
        raise AssertionError("Unexpected URL requested: {}".format(url))

    return get


def responses_for(cluster=None, apps=None, nodes=None, scheduler=None):
    return {
        YARN_CLUSTER_METRICS_PATH: cluster if cluster is not None else {},
        YARN_APPS_PATH: apps if apps is not None else {},
        YARN_NODES_PATH: nodes if nodes is not None else {},
        YARN_SCHEDULER_PATH: scheduler if scheduler is not None else {},
    }


def run_check(instance, responses, init_config=None):
    yarn = YarnCheck("yarn", init_config or {}, [instance])
    with patch("requests.Session.get", new=stub_get(responses)):
        yarn.check(instance)
    return yarn


@pytest.mark.parametrize(
    "tags, expected_tags",
    [
        pytest.param("test:example", ["app_test:example"], id="tag_key_value"),
        pytest.param("test:example,,test", ["app_test:example", "app_", "app_test"], id="test_empty_tag"),
        pytest.param("test:example,:,test", ["app_test:example", "app_:", "app_test"], id="test_empty_kv_tag"),
        pytest.param(
            "test:example,test::test", ["app_test:example", "job_tag:test:example,test::test"], id="test_failure"
        ),
        pytest.param(
            "test:example1,test:example2", ["app_test:example1", "app_test:example2"], id="multiple_tag_key_value"
        ),
        pytest.param("test1,testtag2,test2", ["app_test1", "app_testtag2", "app_test2"], id="multiple_tag_value_only"),
        pytest.param(
            "script_name:test_script,value_only_tag,user_email:test_email",
            ["app_script_name:test_script", "app_value_only_tag", "app_user_email:test_email"],
            id="both_tag_key_and_value_only",
        ),
        pytest.param(
            "script_name:test_script,value_only_tag1,user_email:test_email,value_only_tag2,test:env",
            [
                "app_script_name:test_script",
                "app_value_only_tag1",
                "app_user_email:test_email",
                "app_value_only_tag2",
                "app_test:env",
            ],
            id="both_tag_key_and_value_only",
        ),
    ],
)
def test_split_application_tag(tags, expected_tags):
    instance = YARN_CONFIG["instances"][0]

    # Instantiate YarnCheck
    yarn = YarnCheck("yarn", {}, [instance])

    split_tags = yarn._split_yarn_application_tags(tags, "job_tag")
    assert split_tags == expected_tags


def test_default_timeout_is_5():
    assert DEFAULT_TIMEOUT == 5


def test_default_collect_app_metrics_is_true():
    assert DEFAULT_COLLECT_APP_METRICS is True


def test_default_collect_node_metrics_is_true():
    assert DEFAULT_COLLECT_NODE_METRICS is True


def test_max_detailed_queues_is_100():
    assert MAX_DETAILED_QUEUES == 100


def test_default_split_yarn_application_tags_is_false():
    assert DEFAULT_SPLIT_YARN_APPLICATION_TAGS is False


def test_init_raises_configuration_error_on_invalid_status_mapping():
    instance = {"cluster_name": "test", "application_status_mapping": {"RUNNING": "not_a_real_agentcheck_status"}}
    with pytest.raises(ConfigurationError):
        YarnCheck("yarn", {}, [instance])


def test_check_resets_non_dict_application_tags(aggregator):
    instance = {"cluster_name": "test", "application_tags": ["not", "a", "dict"]}
    run_check(instance, responses_for())
    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=YarnCheck.OK, count=4)


def test_check_filters_disallowed_application_tags(aggregator):
    instance = {"cluster_name": "test", "application_tags": {"app_custom_id": "id", "app_queue": "queue"}}
    apps_payload = {"apps": {"app": [{"id": "app_1", "queue": "default", "name": "myapp", "state": "RUNNING"}]}}
    run_check(instance, responses_for(apps=apps_payload))
    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        tags=["app_queue:default", "app_name:myapp", "yarn_cluster:test", "cluster_name:test", "state:RUNNING"],
        count=1,
    )


def test_check_defaults_cluster_name_when_unset(aggregator):
    instance = {}
    run_check(instance, responses_for())
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        tags=["url:http://localhost:8088", "yarn_cluster:default_cluster", "cluster_name:default_cluster"],
        count=4,
    )


def test_check_includes_legacy_cluster_tag_by_default(aggregator):
    instance = {"cluster_name": "test"}
    run_check(instance, responses_for())
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        tags=["url:http://localhost:8088", "yarn_cluster:test", "cluster_name:test"],
        count=4,
    )


def test_check_disable_legacy_cluster_tag_omits_legacy_tag(aggregator):
    instance = {"cluster_name": "test", "disable_legacy_cluster_tag": True}
    run_check(instance, responses_for())
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        tags=["url:http://localhost:8088", "yarn_cluster:test"],
        count=4,
    )


def test_check_collect_app_metrics_false_skips_app_metrics(aggregator):
    instance = {"cluster_name": "test", "collect_app_metrics": False}
    apps_payload = {"apps": {"app": [{"id": "a1", "queue": "default", "name": "myapp", "state": "RUNNING"}]}}
    run_check(instance, responses_for(apps=apps_payload))
    aggregator.assert_service_check(APPLICATION_STATUS_SERVICE_CHECK, count=0)


def test_check_collect_node_metrics_false_skips_node_metrics(aggregator):
    instance = {"cluster_name": "test", "collect_node_metrics": False}
    nodes_payload = {"nodes": {"node": [{"id": "node1", "numContainers": 5}]}}
    run_check(instance, responses_for(nodes=nodes_payload))
    aggregator.assert_metric("yarn.node.num_containers", count=0)


def test_yarn_cluster_metrics_emitted_when_response_present(aggregator):
    instance = {"cluster_name": "test"}
    run_check(instance, responses_for(cluster={"clusterMetrics": {"appsSubmitted": 3}}))
    aggregator.assert_metric("yarn.metrics.apps_submitted", value=3, count=1)


def test_check_app_metrics_all_states_defaults_to_false(aggregator):
    instance = {"cluster_name": "test"}
    apps_payload = {
        "apps": {"app": [{"id": "a1", "queue": "default", "name": "newapp", "state": "NEW", "progress": 42}]}
    }
    run_check(instance, responses_for(apps=apps_payload))
    aggregator.assert_metric("yarn.apps.progress_gauge", count=0)


def test_check_logs_warning_when_all_states_and_states_list_both_configured(caplog):
    caplog.set_level(logging.WARNING)
    instance = {"cluster_name": "test", "collect_apps_all_states": True}
    run_check(instance, responses_for())
    assert "overriding collect_apps_states" in caplog.text


def test_yarn_app_metrics_skips_safely_when_apps_data_absent(aggregator):
    instance = {"cluster_name": "test"}
    run_check(instance, responses_for(apps={"unrelated": True}))
    aggregator.assert_service_check(APPLICATION_STATUS_SERVICE_CHECK, count=0)


def test_yarn_app_metrics_processes_every_running_app(aggregator):
    instance = {"cluster_name": "test"}
    apps_payload = {
        "apps": {"app": [{"id": "a1", "queue": "default", "name": "myapp", "state": "RUNNING", "progress": 50}]}
    }
    run_check(instance, responses_for(apps=apps_payload))
    aggregator.assert_metric("yarn.apps.progress_gauge", value=50, count=1)
    aggregator.assert_service_check(APPLICATION_STATUS_SERVICE_CHECK, count=1)


def test_get_app_tags_iterates_every_configured_tag():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    tags = yarn._get_app_tags({"queue": "default", "name": "myapp"}, {"app_queue": "queue", "app_name": "name"})
    assert sorted(tags) == sorted(["app_queue:default", "app_name:myapp"])


def test_get_app_tags_skips_falsy_values():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    tags = yarn._get_app_tags({"queue": ""}, {"app_queue": "queue"})
    assert tags == []


def test_get_app_tags_splits_only_exact_application_tags_key():
    instance = {"cluster_name": "test", "split_yarn_application_tags": True}
    yarn = YarnCheck("yarn", {}, [instance])
    app_json = {"applicationTags": "key1:val1", "AAAlowkey": "loval", "zzzhighkey": "hival"}
    app_tags = {
        "app_tag": non_interned("applicationTags"),
        "app_lo": "AAAlowkey",
        "app_hi": "zzzhighkey",
    }
    tags = yarn._get_app_tags(app_json, app_tags)
    assert "app_key1:val1" in tags
    assert "app_lo:loval" in tags
    assert "app_hi:hival" in tags


def test_get_app_tags_logs_and_continues_on_missing_key():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    tags = yarn._get_app_tags({"name": "myapp"}, {"app_missing": "nonexistent", "app_name": "name"})
    assert tags == ["app_name:myapp"]


def test_yarn_node_metrics_sets_version_from_first_node_only(aggregator, datadog_agent):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    yarn.check_id = "test:node"
    nodes_payload = {
        "nodes": {
            "node": [
                {"id": "node1", "numContainers": 2, "version": "3.1.1"},
                {"id": "node2", "numContainers": 4, "version": "3.1.2"},
            ]
        }
    }
    with patch("requests.Session.get", new=stub_get(responses_for(nodes=nodes_payload))):
        yarn.check(instance)

    aggregator.assert_metric("yarn.node.num_containers", value=2, count=1)
    aggregator.assert_metric("yarn.node.num_containers", value=4, count=1)
    datadog_agent.assert_metadata("test:node", {"version.raw": "3.1.1"})


def test_yarn_node_metrics_skips_safely_when_nodes_data_absent(aggregator):
    instance = {"cluster_name": "test"}
    run_check(instance, responses_for(nodes={"unrelated": True}))
    aggregator.assert_metric("yarn.node.num_containers", count=0)


def test_yarn_scheduler_metrics_requires_exact_capacity_scheduler_type(aggregator):
    for scheduler_type, expected_count in (
        (non_interned("capacityScheduler"), 1),
        ("aaaScheduler", 0),
        ("zzzScheduler", 0),
    ):
        aggregator.reset()
        instance = {"cluster_name": "test"}
        scheduler_payload = {
            "scheduler": {"schedulerInfo": {"type": scheduler_type, "queueName": "root", "maxCapacity": 100}}
        }
        run_check(instance, responses_for(scheduler=scheduler_payload))
        aggregator.assert_metric("yarn.queue.root.max_capacity", value=100, count=expected_count)


def test_yarn_scheduler_metrics_swallows_missing_scheduler_info(aggregator):
    instance = {"cluster_name": "test"}
    run_check(instance, responses_for(scheduler={"unexpected": True}))
    aggregator.assert_service_check(SERVICE_CHECK_NAME, count=4)


def test_capacity_scheduler_metrics_skips_safely_when_queues_key_absent():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    yarn._yarn_capacity_scheduler_metrics({"queueName": "root"}, [], [])


def test_capacity_scheduler_metrics_skips_safely_when_queue_list_absent():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    yarn._yarn_capacity_scheduler_metrics({"queueName": "root", "queues": {"other": 1}}, [], [])


def test_capacity_scheduler_metrics_blacklists_and_descends_into_subqueues(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    metrics_json = {
        "queueName": "root",
        "queues": {
            "queue": [
                {"queueName": "blacklisted_queue", "numApplications": 111},
                {
                    "queueName": "clientqueue",
                    "numApplications": 3,
                    "queues": {
                        "queue": [
                            {"queueName": "blacklisted_subqueue", "numApplications": 999},
                            {"queueName": "test_subqueue", "numApplications": 5},
                        ]
                    },
                },
                {"queueName": "no_subqueue_list", "numApplications": 7, "queues": {"other": 1}},
            ]
        },
    }
    queue_blacklist = ["blacklisted_queue", "blacklisted_subqueue"]

    yarn._yarn_capacity_scheduler_metrics(metrics_json, ["tag:1"], queue_blacklist)

    aggregator.assert_metric("yarn.queue.num_applications", value=3, count=1)
    aggregator.assert_metric("yarn.queue.num_applications", value=5, count=1)
    aggregator.assert_metric("yarn.queue.num_applications", value=7, count=1)
    aggregator.assert_metric("yarn.queue.num_applications", value=111, count=0)
    aggregator.assert_metric("yarn.queue.num_applications", value=999, count=0)


def test_capacity_scheduler_metrics_caps_queues_at_max_detailed_queues(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    queues = [{"queueName": "q{}".format(i), "numApplications": i} for i in range(1, 103)]
    metrics_json = {"queueName": "root", "queues": {"queue": queues}}

    yarn._yarn_capacity_scheduler_metrics(metrics_json, [], [])

    aggregator.assert_metric("yarn.queue.num_applications", count=100)
    aggregator.assert_metric("yarn.queue.num_applications", value=100, count=1)
    aggregator.assert_metric("yarn.queue.num_applications", value=101, count=0)
    assert len(yarn.get_warnings()) == 1


def test_capacity_scheduler_metrics_caps_subqueues_at_max_detailed_queues(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    sub_queues = [{"queueName": "sub{}".format(i), "numApplications": i} for i in range(1, 103)]
    metrics_json = {
        "queueName": "root",
        "queues": {"queue": [{"queueName": "parent", "numApplications": 0, "queues": {"queue": sub_queues}}]},
    }

    yarn._yarn_capacity_scheduler_metrics(metrics_json, [], [])

    aggregator.assert_metric("yarn.queue.num_applications", count=100)
    aggregator.assert_metric("yarn.queue.num_applications", value=99, count=1)
    aggregator.assert_metric("yarn.queue.num_applications", value=100, count=0)
    assert len(yarn.get_warnings()) == 1


def test_set_yarn_metrics_from_json_emits_configured_metrics(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    yarn._set_yarn_metrics_from_json(
        ["tag:1"], {"present": 5}, {"present": ("yarn.test.present", GAUGE), "absent": ("yarn.test.absent", GAUGE)}
    )
    aggregator.assert_metric("yarn.test.present", value=5, tags=["tag:1"], count=1)
    aggregator.assert_metric("yarn.test.absent", count=0)


def test_get_value_from_json_walks_nested_keys():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    metrics_json = {"a": {"b": 42}}
    assert yarn._get_value_from_json("a.b", metrics_json) == 42
    assert yarn._get_value_from_json("a.missing", metrics_json) is None


def test_set_metric_dispatches_by_type(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])

    yarn._set_metric("yarn.test.gauge", non_interned(GAUGE), 1, tags=["a:1"])
    yarn._set_metric("yarn.test.increment", non_interned(INCREMENT), 2, tags=["a:1"])
    yarn._set_metric("yarn.test.unknown_low", "aaa", 3, tags=["a:1"])
    yarn._set_metric("yarn.test.unknown_high", "zzz", 4, tags=["a:1"])

    aggregator.assert_metric("yarn.test.gauge", metric_type=aggregator.GAUGE, value=1, count=1)
    aggregator.assert_metric("yarn.test.increment", metric_type=aggregator.COUNTER, value=2, count=1)
    aggregator.assert_metric("yarn.test.unknown_low", count=0)
    aggregator.assert_metric("yarn.test.unknown_high", count=0)


def test_rest_request_to_json_builds_url_and_service_check_tags(aggregator):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    captured = {}

    def fake_get(session, url, *args, **kwargs):
        captured["url"] = url
        return MockResponse(json_data={"ok": True})

    with patch("requests.Session.get", new=fake_get):
        result = yarn._rest_request_to_json(
            "http://localhost:8088", "/ws/v1/cluster/apps", ["tag:1"], "extra", state="RUNNING"
        )

    assert result == {"ok": True}
    assert captured["url"] == "http://localhost:8088/ws/v1/cluster/apps/extra?state=RUNNING"
    aggregator.assert_service_check(SERVICE_CHECK_NAME, tags=["url:http://localhost:8088", "tag:1"], count=1)


@pytest.mark.parametrize(
    "raised_exception",
    [
        Timeout("timeout"),
        HTTPError("http error"),
        InvalidURL("bad url"),
        ConnectionError("conn error"),
        SSLError("ssl error"),
        ValueError("bad json"),
    ],
)
def test_rest_request_to_json_reraises_after_reporting_critical(aggregator, raised_exception):
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])

    def fake_get(session, url, *args, **kwargs):
        raise raised_exception

    with patch("requests.Session.get", new=fake_get):
        with pytest.raises(type(raised_exception)):
            yarn._rest_request_to_json("http://localhost:8088", None, [])

    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=YarnCheck.CRITICAL, count=1)


def test_join_url_dir_appends_every_path_segment():
    instance = {"cluster_name": "test"}
    yarn = YarnCheck("yarn", {}, [instance])
    url = yarn._join_url_dir("http://localhost:8088", "a", "b")
    assert url == "http://localhost:8088/a/b"
