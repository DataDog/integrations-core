# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import pytest
from pyVmomi import vim
from tests.mocked_api import MockedAPI

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.resource_filters import make_inventory_path
from datadog_checks.vsphere.utils import (
    is_metric_excluded_by_filters,
    is_resource_collected_by_filters,
    match_any_regex,
)

regexes = [re.compile(r) for r in (r'foo\d', r'bar\s\d')]


def test_match_any_regex():
    assert match_any_regex('foo1', regexes)
    assert match_any_regex('foo0', regexes)
    assert match_any_regex('bar 0', regexes)
    assert not match_any_regex('foo', regexes)


def test_is_metric_excluded_by_filters():
    metric_filters = {'vm': regexes}

    assert not is_metric_excluded_by_filters('foo1', vim.VirtualMachine, metric_filters)
    assert not is_metric_excluded_by_filters('foo0', vim.VirtualMachine, metric_filters)
    assert not is_metric_excluded_by_filters('bar 0', vim.VirtualMachine, metric_filters)
    assert is_metric_excluded_by_filters('foo', vim.VirtualMachine, metric_filters)


def test_is_reference_excluded():
    metric_filters = {'vm': [re.compile(r'^((?!cpu.usage.avg).)*$')]}
    assert not is_metric_excluded_by_filters('cpu.usage.avg', vim.VirtualMachine, metric_filters)


def test_make_inventory_path():
    root, child1, child2, grandchild1 = [object() for _ in range(4)]

    infrastructure_data = {
        root: {'name': 'root'},
        child1: {'name': 'child1', 'parent': root},
        child2: {'name': 'child2', 'parent': root},
        grandchild1: {'name': 'grandchild1', 'parent': child1},
        object(): {'name': 'grandchild2', 'parent': child1},
        object(): {'name': 'grandchild3', 'parent': child2},
    }

    assert make_inventory_path(root, infrastructure_data) == ''
    assert make_inventory_path(child1, infrastructure_data) == '/child1'
    assert make_inventory_path(child2, infrastructure_data) == '/child2'
    assert make_inventory_path(grandchild1, infrastructure_data) == '/child1/grandchild1'


@pytest.mark.usefixtures("mock_type")
def test_is_realtime_resource_collected_by_filters(realtime_instance):
    realtime_instance['resource_filters'] = [
        {'resource': 'vm', 'property': 'name', 'patterns': [r'^\$VM5$', r'^VM4-2\d$']},
        {'resource': 'vm', 'property': 'inventory_path', 'patterns': [u'\\/D\xe4tacenter\\/vm\\/m.*']},
        {'resource': 'vm', 'property': 'hostname', 'patterns': [r'10\.0\.0\.103']},
        {'resource': 'vm', 'property': 'guest_hostname', 'patterns': [r'ubuntu-test']},
        {'resource': 'vm', 'property': 'tag', 'patterns': [r'env:production']},
        {'resource': 'host', 'property': 'name', 'patterns': [r'10\.0\.0\.103'], 'type': 'blacklist'},
    ]
    realtime_instance['collect_tags'] = True

    collected_resources = [
        'VM2-1',
        '$VM3-2',
        '$VM5',
        '10.0.0.101',
        '10.0.0.102',
        '10.0.0.104',
        u'VM1-6ê',
        'VM3-1',
        'VM4-20',
        'migrationTest',
    ]

    check = VSphereCheck('vsphere', {}, [realtime_instance])

    formatted_filters = check.config.resource_filters

    infra = MockedAPI(realtime_instance).get_infrastructure()
    resources = [m for m in infra if m.__class__ in (vim.VirtualMachine, vim.HostSystem)]
    VM2_1 = next(r for r in resources if infra.get(r).get('name') == 'VM2-1')
    check.infrastructure_cache.set_all_tags({vim.VirtualMachine: {VM2_1._moId: ['env:production', 'tag:2']}})
    for resource in resources:
        is_collected = infra.get(resource).get('name') in collected_resources
        assert (
            is_resource_collected_by_filters(
                resource, infra, formatted_filters, check.infrastructure_cache.get_mor_tags(resource)
            )
            == is_collected
        )
