# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

from datadog_checks.cisco_aci.helpers import (get_pod_from_dn, get_bd_from_dn, get_app_from_dn, get_cep_from_dn,
                                              get_epg_from_dn, get_ip_from_dn, get_node_from_dn, parse_capacity_tags,
                                              get_event_tags_from_dn, get_hostname_from_dn, get_attributes,
                                              check_metric_can_be_zero)


log = logging.getLogger('test_cisco_aci')


def test_get_pod_from_dn():
    assert get_pod_from_dn(None) is None
    assert get_pod_from_dn("") is None
    assert get_pod_from_dn("pod-") is None
    assert get_pod_from_dn("pod-aa") is None
    assert get_pod_from_dn("pod-1") == "1"
    assert get_pod_from_dn("pod-100") == "100"
    assert get_pod_from_dn("aapod-1") == "1"
    assert get_pod_from_dn("aapod-1aaa") == "1"
    assert get_pod_from_dn("pod-1pod-2") == "1"


def test_get_bd_from_dn():
    assert get_bd_from_dn(None) is None
    assert get_bd_from_dn("") is None
    assert get_bd_from_dn("BD-") is None
    assert get_bd_from_dn("BD-1a!") is None
    assert get_bd_from_dn("aaBD-1a!") is None
    assert get_bd_from_dn("/BD-1a!/") == "1a!"
    assert get_bd_from_dn("aa/BD-1a!/aa") == "1a!"
    assert get_bd_from_dn("aa/BD-/aa") is None
    assert get_bd_from_dn("/BD-1a!/BD-1b!/") == "1a!"


def test_get_app_from_dn():
    assert get_app_from_dn(None) is None
    assert get_app_from_dn("") is None
    assert get_app_from_dn("ap-") is None
    assert get_app_from_dn("ap-1a!") is None
    assert get_app_from_dn("aaap-1a!") is None
    assert get_app_from_dn("/ap-1a!/") == "1a!"
    assert get_app_from_dn("aa/ap-1a!/aa") == "1a!"
    assert get_app_from_dn("aa/ap-/aa") is None
    assert get_app_from_dn("/ap-1a!/ap-1b!/") == "1a!"


def test_get_cep_from_dn():
    assert get_cep_from_dn(None) is None
    assert get_cep_from_dn("") is None
    assert get_cep_from_dn("cep-") is None
    assert get_cep_from_dn("cep-1a!") is None
    assert get_cep_from_dn("aacep-1a!") is None
    assert get_cep_from_dn("/cep-1a!/") == "1a!"
    assert get_cep_from_dn("aa/cep-1a!/aa") == "1a!"
    assert get_cep_from_dn("aa/cep-/aa") is None
    assert get_cep_from_dn("/cep-1a!/cep-1b!/") == "1a!"


def test_get_epg_from_dn():
    assert get_epg_from_dn(None) is None
    assert get_epg_from_dn("") is None
    assert get_epg_from_dn("epg-") is None
    assert get_epg_from_dn("epg-1a!") is None
    assert get_epg_from_dn("aaepg-1a!") is None
    assert get_epg_from_dn("/epg-1a!/") == "1a!"
    assert get_epg_from_dn("aa/epg-1a!/aa") == "1a!"
    assert get_epg_from_dn("aa/epg-/aa") is None
    assert get_epg_from_dn("/epg-1a!/epg-1b!/") == "1a!"


def test_get_ip_from_dn():
    assert get_ip_from_dn(None) is None
    assert get_ip_from_dn("") is None
    assert get_ip_from_dn("ip-") is None
    assert get_ip_from_dn("ip-1a!") is None
    assert get_ip_from_dn("aaip-1a!") is None
    assert get_ip_from_dn("/ip-1a!/") == "1a!"
    assert get_ip_from_dn("aa/ip-1a!/aa") == "1a!"
    assert get_ip_from_dn("aa/ip-/aa") is None
    assert get_ip_from_dn("/ip-1a!/ip-1b!/") == "1a!"


def test_get_node_from_dn():
    assert get_node_from_dn(None) is None
    assert get_node_from_dn("") is None
    assert get_node_from_dn("node-") is None
    assert get_node_from_dn("node-aa") is None
    assert get_node_from_dn("node-1") == "1"
    assert get_node_from_dn("node-100") == "100"
    assert get_node_from_dn("aanode-1") == "1"
    assert get_node_from_dn("aanode-1aaa") == "1"
    assert get_node_from_dn("node-1node-2") == "1"


def test_parse_capacity_tags():
    assert parse_capacity_tags(None) == []
    assert parse_capacity_tags("") == []
    res = parse_capacity_tags("aa/pod-1/node-2/aa")
    assert all([a == b for a, b in zip(res, ['fabric_pod_id:1', 'node_id:2'])])
    res = parse_capacity_tags("aa/pod-/node-2/aa")
    assert all([a == b for a, b in zip(res, ['node_id:2'])])
    res = parse_capacity_tags("aa/pod-1/node-/aa")
    assert all([a == b for a, b in zip(res, ['fabric_pod_id:1'])])


def test_get_event_tags_from_dn():
    assert get_event_tags_from_dn(None) == []
    assert get_event_tags_from_dn("") == []
    res = get_event_tags_from_dn("aa/ap-AA/epg-BB/pod-1/node-2/ip-CC/cep-DD/BD-EE/aa")
    assert all([a == b for a, b in zip(res, ['node:2', 'app:AA', 'bd:EE', 'mac:DD', 'ip:CC', 'epg:BB', 'pod:1'])])


def test_get_hostname_from_dn():
    assert get_hostname_from_dn(None) is None
    assert get_hostname_from_dn("") is None
    assert get_hostname_from_dn("aa/pod-/node-/aa") is None
    assert get_hostname_from_dn("/pod-1/node-") is None
    assert get_hostname_from_dn("/pod-/node-2/") is None
    assert get_hostname_from_dn("/pod-1/node-2/") == "pod-1-node-2"


def test_get_attributes():
    assert get_attributes(None) == {}
    assert get_attributes("") == {}
    assert get_attributes("attr") == {}
    assert get_attributes({}) == {}
    assert get_attributes({"attr": "val"}) == {"attr": "val"}

    assert get_attributes({"attributes": ""}) == {"attributes": ""}
    assert get_attributes({"attributes": "attr"}) == {"attributes": "attr"}
    assert get_attributes({"attributes": {}}) == {}
    assert get_attributes({"attributes": {"attr": "val"}}) == {"attr": "val"}

    assert get_attributes({"obj1": {"b": ""}}) == {"obj1": {"b": ""}}
    assert get_attributes({"obj1": {"attributes": ""}}) == {"obj1": {"attributes": ""}}
    assert get_attributes({"obj1": {"attributes": "attr"}}) == {"obj1": {"attributes": "attr"}}
    assert get_attributes({"obj1": {"attributes": {}}}) == {}
    assert get_attributes({"obj1": {"attributes": {"attr": "val"}}}) == {"attr": "val"}


def test_check_metric_can_be_zero():
    assert check_metric_can_be_zero("metric_name_last", None, None) is True
    assert check_metric_can_be_zero("metric_name_Last", None, None) is True
    assert check_metric_can_be_zero("metric_name_last", 1, None) is True
    assert check_metric_can_be_zero("metric_name_Last", 1, None) is True
    assert check_metric_can_be_zero("metric_name_last", 0, None) is True
    assert check_metric_can_be_zero("metric_name_Last", 0, None) is True
    assert check_metric_can_be_zero("metric_name", None, {}) is False
    assert check_metric_can_be_zero("metric_name", 1, None) is True
    assert check_metric_can_be_zero("metric_name", 1, {}) is True
    assert check_metric_can_be_zero("metric_name", 1.0, {}) is True
    assert check_metric_can_be_zero("metric_name", "1", None) is True
    assert check_metric_can_be_zero("metric_name", "1", {}) is True
    assert check_metric_can_be_zero("metric_name", "1.0", {}) is True
    assert check_metric_can_be_zero("metric_name", 0, None) is False
    assert check_metric_can_be_zero("metric_name", 0, {}) is False
    assert check_metric_can_be_zero("metric_name", 0.0, {}) is False
    assert check_metric_can_be_zero("metric_name", "0", {}) is False
    assert check_metric_can_be_zero("metric_name", "0.0", {}) is False
    assert check_metric_can_be_zero("metric_name", "aaa", {}) is False
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": 0}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": 0.0}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": "0"}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": "0.0"}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": "aaa"}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": 1}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": 1.0}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": "1"}) is True
    assert check_metric_can_be_zero("metric_name", 1, {"cnt": "1.0"}) is True
