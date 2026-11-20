# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError

from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import HDFS_NAMENODE_CONFIG, INSTANCE_INTEGRATION

pytestmark = pytest.mark.unit


def test_check_raises_without_jmx_uri(check):
    hdfs_namenode = check({})

    with pytest.raises(Exception, match="The JMX URL must be specified"):
        hdfs_namenode.check({})


def test_check_processes_all_three_bean_groups(aggregator, dd_run_check, mocked_request, datadog_agent):
    instance = HDFS_NAMENODE_CONFIG["instances"][0]
    hdfs_namenode = HDFSNameNode("hdfs_namenode", {}, [instance])
    hdfs_namenode.check_id = "test:unit"

    dd_run_check(hdfs_namenode)

    aggregator.assert_metric("hdfs.namenode.capacity_total", count=1)
    aggregator.assert_metric("hdfs.namenode.missing_blocks", count=1)
    datadog_agent.assert_metadata_count(6)


def test_http_config_remapper():
    assert HDFSNameNode.HTTP_CONFIG_REMAPPER["disable_ssl_validation"] == {
        "name": "tls_verify",
        "default": False,
        "invert": True,
    }


def test_hdfs_namenode_metrics_raises_on_unequal_bean_name(check):
    class AlwaysUnequal:
        def __eq__(self, other):
            return False

        def __ne__(self, other):
            return True

    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {"name": AlwaysUnequal()}

    with pytest.raises(Exception, match="Unexpected bean name"):
        hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])


def test_hdfs_namenode_metrics_requires_both_capacity_keys(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {"name": "foo", "CapacityUsed": 100}

    hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])

    aggregator.assert_metric("hdfs.namenode.capacity_in_use", count=0)


def test_hdfs_namenode_metrics_capacity_total_default_is_zero(aggregator, check):
    class BeanWithFakeCapacityTotal(dict):
        def __contains__(self, key):
            if key == "CapacityTotal":
                return True
            return super().__contains__(key)

    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = BeanWithFakeCapacityTotal({"name": "foo", "CapacityUsed": 100})

    hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])

    aggregator.assert_metric("hdfs.namenode.capacity_in_use", value=0, tags=[], count=1)


def test_hdfs_namenode_metrics_emits_from_metrics_mapping(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {"name": "foo", "SomeRawMetric": 42}
    metrics = {"SomeRawMetric": ("hdfs.namenode.some_metric", HDFSNameNode.GAUGE)}

    hdfs_namenode._hdfs_namenode_metrics([bean], metrics, [])

    aggregator.assert_metric("hdfs.namenode.some_metric", value=42, count=1)


def test_rest_request_to_json_builds_query_string_only_when_present(check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    captured_urls = []

    def fake_get(session, url, **kwargs):
        captured_urls.append(url)
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        return response

    with mock.patch("requests.Session.get", fake_get):
        hdfs_namenode._rest_request_to_json("http://example.com/", None, {"qry": "Foo", "a": "b"})

    assert captured_urls == ["http://example.com/?qry=Foo&a=b"]


def test_collect_metadata_sets_version_when_present(check, datadog_agent):
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    hdfs_namenode.check_id = "test:unit"

    hdfs_namenode._collect_metadata([{"Version": "3.1.3, rba631c436b806728f8ec2f54ab1e289526c90579"}])

    datadog_agent.assert_metadata(
        "test:unit",
        {"version.scheme": "semver", "version.major": "3", "version.minor": "1", "version.patch": "3"},
    )


def test_set_metric_rejects_lexically_smaller_type(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    hdfs_namenode._set_metric("hdfs.namenode.test_metric", "aauge", 1, tags=[])

    aggregator.assert_metric("hdfs.namenode.test_metric", count=0)


def test_set_metric_rejects_lexically_larger_type(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    hdfs_namenode._set_metric("hdfs.namenode.test_metric", "zauge", 1, tags=[])

    aggregator.assert_metric("hdfs.namenode.test_metric", count=0)


def test_set_metric_accepts_equal_but_distinct_gauge_string(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    metric_type = "".join(["g", "a", "u", "g", "e"])

    hdfs_namenode._set_metric("hdfs.namenode.test_metric", metric_type, 1, tags=[])

    aggregator.assert_metric("hdfs.namenode.test_metric", value=1, count=1)


def test_rest_request_to_json_reports_critical_on_timeout(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch("requests.Session.get", side_effect=Timeout("boom")):
        with pytest.raises(Timeout):
            hdfs_namenode._rest_request_to_json("http://example.com/", None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="Request timeout", count=1
    )


@pytest.mark.parametrize("raised_exception", [HTTPError, InvalidURL, ConnectionError])
def test_rest_request_to_json_reports_critical_on_request_errors(aggregator, check, raised_exception):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch("requests.Session.get", side_effect=raised_exception("boom")):
        with pytest.raises(raised_exception):
            hdfs_namenode._rest_request_to_json("http://example.com/", None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="Request failed", count=1
    )


def test_rest_request_to_json_reports_critical_on_json_decode_error(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch("requests.Session.get", side_effect=JSONDecodeError("bad json", "doc", 0)):
        with pytest.raises(JSONDecodeError):
            hdfs_namenode._rest_request_to_json("http://example.com/", None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="JSON Parse failed", count=1
    )


def test_rest_request_to_json_reports_critical_on_value_error(aggregator, check):
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch("requests.Session.get", side_effect=ValueError("boom")):
        with pytest.raises(ValueError):
            hdfs_namenode._rest_request_to_json("http://example.com/", None, {})

    aggregator.assert_service_check(HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="boom", count=1)


def test_join_url_dir_is_classmethod():
    result = HDFSNameNode._join_url_dir("http://example.com/", "jmx", "path")

    assert result == "http://example.com/jmx/path"
