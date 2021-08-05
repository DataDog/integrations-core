# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from datetime import datetime, timedelta

import mock
import pytest
from kubernetes.client.models.v1_lease import V1Lease
from kubernetes.client.models.v1_lease_spec import V1LeaseSpec
from kubernetes.config.dateutil import format_rfc3339
from six import iteritems, string_types

from datadog_checks.base import AgentCheck, KubeLeaderElectionBaseCheck
from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation, ElectionRecordLease

# Trigger lazy imports
try:
    KubeLeaderElectionBaseCheck().check({})
except Exception:
    pass


RAW_VALID_RECORD = (
    '{"holderIdentity":"dd-cluster-agent-568f458dd6-kj6vt",'
    '"leaseDurationSeconds":60,'
    '"acquireTime":"2018-12-17T11:53:07Z",'
    '"renewTime":"2018-12-18T12:32:22Z",'
    '"leaderTransitions":7}'
)

LEASE_OBJECT = V1Lease(
    api_version="coordination.k8s.io/v1",
    kind="Lease",
    spec=V1LeaseSpec(
        acquire_time=datetime(2021, 2, 4, 8, 23, 33),
        holder_identity="ip-172-20-76-27_fa8a18f2-9c8a-42e8-99ff-2e759d623d0e",
        lease_duration_seconds=15,
        lease_transitions=42,
        renew_time=datetime(2021, 2, 4, 15, 51, 10),
    ),
)

EP_INSTANCE = {
    "namespace": "base",
    "record_kind": "endpoints",
    "record_name": "thisrecord",
    "record_namespace": "myns",
    "tags": ["custom:tag"],
}

EP_TAGS = ["record_kind:endpoints", "record_name:thisrecord", "record_namespace:myns", "custom:tag"]

CM_INSTANCE = {
    "namespace": "base",
    "record_kind": "configmap",
    "record_name": "thisrecord",
    "record_namespace": "myns",
    "tags": ["custom:tag"],
}

CM_TAGS = ["record_kind:configmap", "record_name:thisrecord", "record_namespace:myns", "custom:tag"]


@pytest.fixture()
def mock_incluster():
    # Disable the kube config loader to avoid errors on check run
    with mock.patch('datadog_checks.base.checks.kube_leader.mixins.config.load_incluster_config'):
        yield


@pytest.fixture()
def mock_read_endpoints():
    # Allows to inject an arbitrary endpoints object
    with mock.patch('datadog_checks.base.checks.kube_leader.mixins.client.CoreV1Api.read_namespaced_endpoints') as m:
        yield m


@pytest.fixture()
def mock_read_configmap():
    # Allows to inject an arbitrary configmap object
    with mock.patch('datadog_checks.base.checks.kube_leader.mixins.client.CoreV1Api.read_namespaced_config_map') as m:
        yield m


def make_record(holder=None, duration=None, transitions=None, acquire=None, renew=None):
    def format_time(date_time):
        if isinstance(date_time, string_types):
            return date_time
        return format_rfc3339(date_time)

    record = {}
    if holder:
        record["holderIdentity"] = holder
    if duration:
        record["leaseDurationSeconds"] = duration
    if transitions:
        record["leaderTransitions"] = transitions
    if acquire:
        record["acquireTime"] = format_time(acquire)
    if renew:
        record["renewTime"] = format_time(renew)

    return json.dumps(record)


def make_fake_object(record=None):
    obj = type('', (), {})()
    obj.metadata = type('', (), {})()
    obj.metadata.annotations = {}

    if record:
        obj.metadata.annotations["control-plane.alpha.kubernetes.io/leader"] = record

    return obj


class TestElectionRecord:
    def test_parse_annotation(self):
        record = ElectionRecordAnnotation("endpoints", RAW_VALID_RECORD)

        valid, reason = record.validate()
        assert valid is True
        assert reason is None

        assert record.leader_name == "dd-cluster-agent-568f458dd6-kj6vt"
        assert record.lease_duration == 60
        assert record.transitions == 7
        assert record.renew_time > record.acquire_time
        assert record.seconds_until_renew < 0
        assert record.summary == (
            "Leader: dd-cluster-agent-568f458dd6-kj6vt "
            "since 2018-12-17 11:53:07+00:00, "
            "next renew 2018-12-18 12:32:22+00:00"
        )

    def test_parse_lease(self):
        record = ElectionRecordLease(LEASE_OBJECT)

        valid, reason = record.validate()
        assert valid is True
        assert reason is None

        assert record.leader_name == "ip-172-20-76-27_fa8a18f2-9c8a-42e8-99ff-2e759d623d0e"
        assert record.lease_duration == 15
        assert record.transitions == 42
        assert record.renew_time > record.acquire_time
        assert record.seconds_until_renew < 0
        assert record.summary == (
            "Leader: ip-172-20-76-27_fa8a18f2-9c8a-42e8-99ff-2e759d623d0e "
            "since 2021-02-04 08:23:33, "
            "next renew 2021-02-04 15:51:10"
        )

    def test_validation(self):
        cases = {
            make_record(): "Invalid record: no current leader recorded",
            make_record(holder="me"): "Invalid record: no lease duration set",
            make_record(holder="me", duration=30): "Invalid record: no renew time set",
            make_record(
                holder="me", duration=30, renew="2018-12-18T12:32:22Z"
            ): "Invalid record: no acquire time recorded",
            make_record(holder="me", duration=30, renew=datetime.utcnow(), acquire="2018-12-18T12:32:22Z"): None,
            make_record(
                holder="me", duration=30, renew="invalid", acquire="2018-12-18T12:32:22Z"
            ): "Invalid record: bad format for renewTime field",
            make_record(
                holder="me", duration=30, renew="2018-12-18T12:32:22Z", acquire="0000-12-18T12:32:22Z"
            ): "Invalid record: bad format for acquireTime field",
        }

        for raw, expected_reason in iteritems(cases):
            valid, reason = ElectionRecordAnnotation("endpoints", raw).validate()
            assert reason == expected_reason
            if expected_reason is None:
                assert valid is True
            else:
                assert valid is False

    def test_seconds_until_renew(self):
        raw = make_record(
            holder="me", duration=30, acquire="2018-12-18T12:32:22Z", renew=datetime.utcnow() + timedelta(seconds=20)
        )

        record = ElectionRecordAnnotation("endpoints", raw)
        assert record.seconds_until_renew > 19
        assert record.seconds_until_renew < 21

        raw = make_record(
            holder="me", duration=30, acquire="2018-12-18T12:32:22Z", renew=datetime.utcnow() - timedelta(seconds=5)
        )

        record = ElectionRecordAnnotation("endpoints", raw)
        assert record.seconds_until_renew > -6
        assert record.seconds_until_renew < -4


@mock.patch('datadog_checks.base.checks.kube_leader.mixins.config')
class TestClientConfig:
    def test_config_incluster(self, config):
        c = KubeLeaderElectionBaseCheck()
        c.check({})
        config.load_incluster_config.assert_called_once()

    @mock.patch('datadog_checks.base.checks.kube_leader.mixins.datadog_agent')
    def test_config_kubeconfig(self, datadog_agent, config):
        datadog_agent.get_config.return_value = "/file/path"
        c = KubeLeaderElectionBaseCheck()
        c.check({})
        datadog_agent.get_config.assert_called_once_with('kubernetes_kubeconfig_path')
        config.load_kube_config.assert_called_once_with(config_file="/file/path")


class TestBaseCheck:
    def test_valid_endpoints(self, aggregator, mock_read_endpoints, mock_incluster):
        mock_read_endpoints.return_value = make_fake_object(RAW_VALID_RECORD)
        c = KubeLeaderElectionBaseCheck()
        c.check(EP_INSTANCE)

        assert c.get_warnings() == []
        mock_read_endpoints.assert_called_once_with("thisrecord", "myns", _request_timeout=30)
        aggregator.assert_metric("base.leader_election.transitions", value=7, tags=EP_TAGS)
        aggregator.assert_metric("base.leader_election.lease_duration", value=60, tags=EP_TAGS)
        aggregator.assert_service_check("base.leader_election.status", status=AgentCheck.CRITICAL, tags=EP_TAGS)
        aggregator.assert_all_metrics_covered()

    def test_valid_configmap(self, aggregator, mock_read_configmap, mock_incluster):
        mock_read_configmap.return_value = make_fake_object(RAW_VALID_RECORD)
        c = KubeLeaderElectionBaseCheck()
        c.check(CM_INSTANCE)

        assert c.get_warnings() == []
        mock_read_configmap.assert_called_once_with("thisrecord", "myns", _request_timeout=30)
        aggregator.assert_metric("base.leader_election.transitions", value=7, tags=CM_TAGS)
        aggregator.assert_metric("base.leader_election.lease_duration", value=60, tags=CM_TAGS)
        aggregator.assert_service_check("base.leader_election.status", status=AgentCheck.CRITICAL, tags=CM_TAGS)
        aggregator.assert_all_metrics_covered()

    def test_empty_configmap(self, aggregator, mock_read_configmap, mock_incluster):
        mock_read_configmap.return_value = make_fake_object()
        c = KubeLeaderElectionBaseCheck()
        c.check(CM_INSTANCE)

        assert len(c.get_warnings()) == 1
        aggregator.assert_all_metrics_covered()

    def test_ok_configmap(self, aggregator, mock_read_configmap, mock_incluster):
        mock_read_configmap.return_value = make_fake_object(
            make_record(holder="me", duration=30, renew=datetime.utcnow(), acquire="2018-12-18T12:32:22Z")
        )
        c = KubeLeaderElectionBaseCheck()
        c.check(CM_INSTANCE)

        assert c.get_warnings() == []
        aggregator.assert_metric("base.leader_election.transitions", value=0, tags=CM_TAGS)
        aggregator.assert_metric("base.leader_election.lease_duration", value=30, tags=CM_TAGS)
        aggregator.assert_service_check("base.leader_election.status", status=AgentCheck.OK, tags=CM_TAGS)
        aggregator.assert_all_metrics_covered()

    def test_invalid_configmap(self, aggregator, mock_read_configmap, mock_incluster):
        mock_read_configmap.return_value = make_fake_object(make_record(holder="me"))
        c = KubeLeaderElectionBaseCheck()
        c.check(CM_INSTANCE)

        assert c.get_warnings() == []
        aggregator.assert_service_check("base.leader_election.status", status=AgentCheck.CRITICAL, tags=CM_TAGS)
        aggregator.assert_all_metrics_covered()
