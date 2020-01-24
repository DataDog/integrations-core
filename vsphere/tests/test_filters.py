# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import pytest
from pyVmomi import vim
from tests.mocked_api import MockedAPI

from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.utils import (
    is_metric_excluded_by_filters,
    is_resource_excluded_by_filters,
    make_inventory_path,
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
def test_is_realtime_resource_excluded_by_filters(realtime_instance):
    realtime_instance['resource_filters'] = [
        {'resource': 'vm', 'property': 'name', 'patterns': [r'^\$VM5$', r'^VM4-2\d$']},
        {'resource': 'vm', 'property': 'inventory_path', 'patterns': [r'\/Dätacenter\/vm\/m.*']},
        {'resource': 'vm', 'property': 'hostname', 'patterns': [r'10\.0\.0\.103']},
        {'resource': 'vm', 'property': 'guest_hostname', 'patterns': [r'ubuntu-test']},
    ]

    excluded_resources = [
        'VM1-4',
        'VM2-1',
        'VM1-3',
        'VM2-2',
        'VM1-5',
        'VM1-2',
        'VM-0',
        u'VM1-1ä',
        'VM4-2',
        'VM4-4',
        'VM4-14',
        'VM4-9',
        'VM4-15',
        'VM4-5',
        'VM4-3',
        'VM4-12',
        'VM4-11',
        'VM4-6',
        'VM4-13',
        'VM4-1',
        'VM4-19',
        'VM4-18',
        'VM4-7',
        'VM4-17',
        'VM4-10',
        'VM4-16',
        'VM4-8',
    ]

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    formatted_filters = check.config.resource_filters

    infra = MockedAPI(realtime_instance).get_infrastructure()
    resources = [m for m in infra if m.__class__ in (vim.VirtualMachine, vim.HostSystem)]

    for resource in resources:
        is_excluded = infra.get(resource).get('name') in excluded_resources
        if not is_resource_excluded_by_filters(resource, infra, formatted_filters) == is_excluded:
            assert is_resource_excluded_by_filters(resource, infra, formatted_filters)
