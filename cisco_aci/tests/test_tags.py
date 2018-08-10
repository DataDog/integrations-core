# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import logging

from datadog_checks.utils.containers import hash_mutable
from datadog_checks.cisco_aci.tags import CiscoTags


log = logging.getLogger('test_cisco_aci')


def test_app_tags():
    tags = CiscoTags()
    assert tags._app_tags(None) == []
    assert tags._app_tags([]) == []
    assert tags._app_tags("aaa") == []
    assert tags._app_tags({}) == []

    assert tags._app_tags({"aaa": ""}) == []
    assert tags._app_tags({"aaa": "aaa"}) == []
    assert tags._app_tags({"aaa": []}) == []
    assert tags._app_tags({"aaa": {}}) == []

    assert tags._app_tags({"attributes": ""}) == []
    assert tags._app_tags({"attributes": []}) == []
    assert tags._app_tags({"attributes": ["aaa"]}) == []
    assert tags._app_tags({"attributes": {}}) == []

    assert tags._app_tags({"attributes": {"aaa": ""}}) == []

    assert tags._app_tags({"attributes": {"name": ""}}) == []
    assert tags._app_tags({"attributes": {"name": "app1"}}) == ["application:app1"]

    with pytest.raises(TypeError):
        tags._app_tags({"attributes": {"name": 1234}}) == ["application:1234"]

    assert tags._app_tags({"attributes": {"name": []}}) == []
    with pytest.raises(TypeError):
        assert tags._app_tags({"attributes": {"name": ["aaa"]}}) == []
    assert tags._app_tags({"attributes": {"name": {}}}) == []
    with pytest.raises(TypeError):
        assert tags._app_tags({"attributes": {"name": {"aaa": "aaa"}}}) == []

    assert tags._app_tags({"attributes": {"dn": ""}}) == []
    assert tags._app_tags({"attributes": {"dn": []}}) == []
    with pytest.raises(TypeError):
        assert tags._app_tags({"attributes": {"dn": ["aaa"]}}) == []
    assert tags._app_tags({"attributes": {"dn": {}}}) == []
    with pytest.raises(TypeError):
        assert tags._app_tags({"attributes": {"dn": {"aaa": "aaa"}}}) == []

    assert tags._app_tags({"attributes": {"dn": "test"}}) == []
    assert tags._app_tags({"attributes": {"dn": "1234"}}) == []
    assert tags._app_tags({"attributes": {"dn": "/tn-qwertyQWERTY1234567890-_/"}}) == [
        "tenant:qwertyQWERTY1234567890-_"]
    assert tags._app_tags({"attributes": {"dn": "/tn-aa!a/"}}) == ["tenant:aa!a"]
    assert tags._app_tags({"attributes": {"dn": "a/tn-aaa/a"}}) == ["tenant:aaa"]
    assert tags._app_tags({"attributes": {"dn": "a/tn-tn-/a"}}) == ["tenant:tn-"]
    assert tags._app_tags({"attributes": {"dn": "a/tn-aaa/tn-bbb/a"}}) == ["tenant:aaa"]

    assert tags._app_tags({"attributes": {"name": "app", "dn": "/tn-aaa/"}}) == ["application:app", "tenant:aaa"]


def test_edpt_tags_map():
    tags = CiscoTags()
    assert tags._edpt_tags_map(None) == {}
    assert tags._edpt_tags_map([]) == {}
    assert tags._edpt_tags_map("aaa") == {}
    assert tags._edpt_tags_map({}) == {}

    assert tags._edpt_tags_map({"aaa": ""}) == {}
    assert tags._edpt_tags_map({"aaa": "aaa"}) == {}
    assert tags._edpt_tags_map({"aaa": []}) == {}
    assert tags._edpt_tags_map({"aaa": {}}) == {}

    assert tags._edpt_tags_map({"attributes": ""}) == {}
    assert tags._edpt_tags_map({"attributes": []}) == {}
    assert tags._edpt_tags_map({"attributes": ["aaa"]}) == {}
    assert tags._edpt_tags_map({"attributes": {}}) == {}

    assert tags._edpt_tags_map({"attributes": {"aaa": ""}}) == {}

    assert tags._edpt_tags_map({"attributes": {"name": ""}}) == {}
    assert tags._edpt_tags_map({"attributes": {"name": "app1"}}) == {"endpoint_group": "app1"}
    with pytest.raises(TypeError):
        tags._edpt_tags_map({"attributes": {"name": 1234}}) == {}

    assert tags._edpt_tags_map({"attributes": {"name": []}}) == {}
    with pytest.raises(TypeError):
        tags._edpt_tags_map({"attributes": {"name": ["aaa"]}}) == {}
    assert tags._edpt_tags_map({"attributes": {"name": {}}}) == {}
    with pytest.raises(TypeError):
        tags._edpt_tags_map({"attributes": {"name": {"aaa": "aaa"}}}) == {}

    assert tags._edpt_tags_map({"attributes": {"dn": ""}}) == {}
    assert tags._edpt_tags_map({"attributes": {"dn": []}}) == {}
    with pytest.raises(TypeError):
        tags._edpt_tags_map({"attributes": {"dn": ["aaa"]}}) == {}
    assert tags._edpt_tags_map({"attributes": {"dn": {}}}) == {}
    with pytest.raises(TypeError):
        tags._edpt_tags_map({"attributes": {"dn": {"aaa": "aaa"}}}) == {}

    assert tags._edpt_tags_map({"attributes": {"dn": "test"}}) == {}

    with pytest.raises(TypeError):
        assert tags._edpt_tags_map({"attributes": {"dn": 1234}}) == {}

    assert tags._edpt_tags_map({"attributes": {"dn": "/tn-qwertyQWERTY1234567890-_/"}}) == {
        "tenant": "qwertyQWERTY1234567890-_"}

    assert tags._edpt_tags_map({"attributes": {"dn": "/tn-aa!a/"}}) == {"tenant": "aa!a"}
    assert tags._edpt_tags_map({"attributes": {"dn": "/tn-aaa/"}}) == {"tenant": "aaa"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/tn-aaa/a"}}) == {"tenant": "aaa"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/tn-tn-/a"}}) == {"tenant": "tn-"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/tn-aaa/tn-bbb/a"}}) == {"tenant": "aaa"}

    assert tags._edpt_tags_map({"attributes": {"dn": "a/ap-qwertyQWERTY1234567890-_/a"}}) == {
        "application": "qwertyQWERTY1234567890-_"}

    assert tags._edpt_tags_map({"attributes": {"dn": "/ap-aa!a/"}}) == {"application": "aa!a"}
    assert tags._edpt_tags_map({"attributes": {"dn": "/ap-aaa/"}}) == {"application": "aaa"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/ap-aaa/a"}}) == {"application": "aaa"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/ap-ap-/a"}}) == {"application": "ap-"}
    assert tags._edpt_tags_map({"attributes": {"dn": "a/ap-aaa/ap-bbb/a"}}) == {"application": "aaa"}

    assert tags._edpt_tags_map({"attributes": {"name": "aaa", "dn": "a/tn-bbb/ap-ccc/a"}}) == {"endpoint_group": "aaa",
                                                                                               "tenant": "bbb",
                                                                                               "application": "ccc"}


def test_epg_meta_tags_map():
    tags = CiscoTags()
    assert tags._epg_meta_tags_map(None) == {}
    assert tags._epg_meta_tags_map([]) == {}
    assert tags._epg_meta_tags_map("aaa") == {}
    assert tags._epg_meta_tags_map({}) == {}

    assert tags._epg_meta_tags_map({"aaa": ""}) == {}
    assert tags._epg_meta_tags_map({"aaa": "aaa"}) == {}
    assert tags._epg_meta_tags_map({"aaa": []}) == {}
    assert tags._epg_meta_tags_map({"aaa": {}}) == {}

    assert tags._epg_meta_tags_map({"attributes": ""}) == {}
    assert tags._epg_meta_tags_map({"attributes": []}) == {}
    assert tags._epg_meta_tags_map({"attributes": ["aaa"]}) == {}
    assert tags._epg_meta_tags_map({"attributes": {}}) == {}

    # ip
    assert tags._epg_meta_tags_map({"attributes": {"ip": ""}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"ip": "aaa"}}) == {"ip": "aaa"}

    # mac
    assert tags._epg_meta_tags_map({"attributes": {"mac": ""}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"mac": "aaa"}}) == {"mac": "aaa"}

    # encap
    assert tags._epg_meta_tags_map({"attributes": {"encap": ""}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"encap": "aaa"}}) == {"encap": "aaa"}

    # other
    assert tags._epg_meta_tags_map({"attributes": {"other": ""}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": "aaa"}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": 1234}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": []}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": ["aaa"]}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": {}}}) == {}
    assert tags._epg_meta_tags_map({"attributes": {"other": {"aaa": "aaa"}}}) == {}

    # all
    assert tags._epg_meta_tags_map({"attributes": {"other": "", "ip": "aaa", "mac": "bbb", "encap": "ccc"}}) == {
        "ip": "aaa", "mac": "bbb", "encap": "ccc"}


class ApiMock1:
    def __init__(self):
        pass

    def get_epg_meta(self, tenant, app, epg):
        return []

    def get_eth_list_for_epg(self, tenant, app, epg):
        return []


class ApiMock2:
    def __init__(self):
        pass

    def get_epg_meta(self, tenant, app, epg):
        return [{"fvCEp": {"attributes": {"other": "", "ip": "ddd", "mac": "eee", "encap": "fff"}}}]

    def get_eth_list_for_epg(self, tenant, app, epg):
        return []


class ApiMock3:
    def __init__(self):
        pass

    def get_epg_meta(self, tenant, app, epg):
        return [{"fvCEp": {"attributes": {"other": "", "ip": "ddd", "mac": "eee", "encap": "fff"}}}]

    def get_eth_list_for_epg(self, tenant, app, epg):
        return [{"fvRsCEpToPathEp": {"attributes": {"tDn": ""}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "aaa"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "/pathep-[bbb]/"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "a/pathep-[ccc]/a"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "a/pathep-[ddd]/pathep-[eee]/a"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "/paths-[fff]/"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "a/paths-[ggg]/a"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "a/paths-[hhh]/paths-[iii]/a"}}},
                {"fvRsCEpToPathEp": {"attributes": {"tDn": "a/paths-[jjj]/pathep-[kkk]/a"}}},
                ]


def test_tenant_mapper():
    tags = CiscoTags()
    api1 = ApiMock1()

    tags.api = api1
    assert tags._tenant_mapper(None) == []
    assert tags._tenant_mapper("") == []
    assert tags._tenant_mapper("aaa") == []
    assert tags._tenant_mapper([]) == []
    assert tags._tenant_mapper(["aaa"]) == []
    assert tags._tenant_mapper({}) == []
    assert tags._tenant_mapper({"aaa": "aaa"}) == []
    assert all([a == b for a, b in zip(sorted(tags._tenant_mapper({"attributes": {"name": "aaa",
                                                                                  "dn": "a/tn-bbb/ap-ccc/a"}})),
                                       sorted(['tenant:bbb', 'endpoint_group:aaa', 'application:ccc']))])

    api2 = ApiMock2()
    tags.api = api2
    assert all([a == b for a, b in zip(sorted(tags._tenant_mapper({"attributes": {"name": "aaa",
                                                                                  "dn": "a/tn-bbb/ap-ccc/a"}})),
                                       sorted(['tenant:bbb', 'application:ccc', 'endpoint_group:aaa',
                                               "ip:ddd", "mac:eee", "encap:fff"]))])

    context_hash = hash_mutable(['tenant:bbb', 'application:ccc', 'endpoint_group:aaa', "ip:ddd", "mac:eee",
                                 "encap:fff"])
    api3 = ApiMock3()
    tags.api = api3
    tags.tenant_tags = {context_hash: ["test:ggg"]}
    assert all([a == b for a, b in zip(sorted(tags._tenant_mapper({"attributes": {"name": "aaa",
                                                                                  "dn": "a/tn-bbb/ap-ccc/a"}})),
                                       sorted(['tenant:bbb', 'application:ccc', 'endpoint_group:aaa',
                                               "ip:ddd", "mac:eee", "encap:fff", "test:ggg"]))])
    assert tags.tenant_farbic_mapper == {}

    api3 = ApiMock3()
    tags.api = api3
    tags.tenant_tags = {}
    assert all([a == b for a, b in zip(sorted(tags._tenant_mapper({"attributes": {"name": "aaa",
                                                                                  "dn": "a/tn-bbb/ap-ccc/a"}})),
                                       sorted(['ip:ddd', 'mac:eee', 'encap:fff', 'endpoint_group:aaa',
                                               'application:ccc', 'tenant:bbb', 'port:bbb',
                                               'port:ccc', 'port:ddd', 'port:kkk', 'node_id:[jjj]']))])
    assert all([a == b for a, b in zip(sorted(tags.tenant_farbic_mapper.get('[jjj]:kkk', [])),
                                       sorted(['application:ccc', 'endpoint_group:aaa', 'tenant:bbb']))])
