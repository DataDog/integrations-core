# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging

import pytest
from mock import MagicMock
from pyVmomi import vim, vmodl

from datadog_checks.esxi import EsxiCheck


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, caplog):
    check = EsxiCheck('esxi', {}, [instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    aggregator.assert_metric('esxi.host.can_connect', value=0, tags=["esxi_url:localhost"])
    assert "Cannot connect to ESXi host" in caplog.text


@pytest.mark.usefixtures("service_instance")
def test_none_properties_data(vcsim_instance, dd_run_check, aggregator, service_instance, caplog):
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=None)
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    assert "No resources found; halting check execution" in caplog.text

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("service_instance")
def test_esxi_no_properties(vcsim_instance, dd_run_check, aggregator, service_instance, caplog):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host"),
                propSet=[],
            )
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    assert "No resources found; halting check execution" in caplog.text

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("service_instance")
def test_esxi_no_hostname(vcsim_instance, dd_run_check, aggregator, service_instance, caplog):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='test',
                        val='c1',
                    ),
                ],
            )
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    assert "No host name found for 'vim.HostSystem:host'; skipping" in caplog.text


@pytest.mark.usefixtures("service_instance")
def test_hostname_multiple_props(vcsim_instance, dd_run_check, aggregator, service_instance, caplog):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='test',
                        val='test',
                    ),
                    vmodl.DynamicProperty(
                        name='name',
                        val='hostname',
                    ),
                ],
            )
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)

    aggregator.assert_metric("esxi.cpu.usage.avg", hostname="hostname")


@pytest.mark.usefixtures("service_instance")
def test_esxi_perf_metrics(vcsim_instance, dd_run_check, aggregator, caplog):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.cpu.usage.avg", value=26, tags=base_tags, hostname="localhost.localdomain")
    aggregator.assert_metric("esxi.mem.granted.avg", value=80, tags=base_tags, hostname="localhost.localdomain")
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)

    assert "Skipping metric net.droppedRx.sum for localhost.localdomain, because the value "
    "returned by the host is negative (i.e. the metric is not yet available). values: [-1]" in caplog.text

    assert (
        "Skipping metric net.droppedRx.sum for localhost.localdomain because no value was returned by the host"
    ) in caplog.text


@pytest.mark.usefixtures("service_instance")
def test_vm_perf_metrics(vcsim_instance, dd_run_check, aggregator):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.cpu.usage.avg", value=18, tags=base_tags, hostname="vm1")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=19, tags=base_tags, hostname="vm2")
    aggregator.assert_metric("esxi.net.droppedRx.sum", value=28, tags=base_tags, hostname="vm1")


@pytest.mark.usefixtures("service_instance")
def test_external_host_tags(vcsim_instance, datadog_agent, dd_run_check):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)
    datadog_agent.assert_external_tags(
        'localhost.localdomain',
        {
            'esxi': [
                'esxi_datacenter:dc2',
                'esxi_folder:folder_1',
                'esxi_type:host',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm1',
        {
            'esxi': [
                'esxi_datacenter:dc2',
                'esxi_folder:folder_1',
                'esxi_type:vm',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm2',
        {'esxi': ['esxi_cluster:c1', 'esxi_compute:c1', 'esxi_type:vm', 'esxi_url:127.0.0.1:8989']},
    )


@pytest.mark.usefixtures("service_instance")
def test_external_host_tags_all_resources(vcsim_instance, datadog_agent, dd_run_check, service_instance):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host"),
                    ),
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.StoragePod(moId="pod1"),
                    ),
                    vmodl.DynamicProperty(
                        name='name',
                        val='hostname',
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.StoragePod(moId="pod1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='pod1',
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Datastore(moId="ds1"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.Datastore(moId="ds1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='ds1',
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.ClusterComputeResource(moId="c1"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.ClusterComputeResource(moId="c1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='c1',
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.HostServiceSystem(moId="hss"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.HostServiceSystem(moId="hss"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='hss',
                    )
                ],
            ),
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)

    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)
    datadog_agent.assert_external_tags(
        'hostname',
        {
            'esxi': [
                'esxi_cluster:c1',
                'esxi_compute:c1',
                'esxi_datastore:ds1',
                'esxi_datastore_cluster:pod1',
                'esxi_type:host',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm1',
        {
            'esxi': [
                'esxi_type:vm',
                'esxi_cluster:c1',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )


@pytest.mark.usefixtures("service_instance")
def test_use_guest_hostname(vcsim_instance, dd_run_check, aggregator):
    vcsim_instance = copy.deepcopy(vcsim_instance)
    vcsim_instance['use_guest_hostname'] = True
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)

    aggregator.assert_metric("esxi.cpu.usage.avg", value=18, hostname="testing-vm")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=19, hostname="test-vm-2")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=26, hostname="localhost.localdomain")


@pytest.mark.parametrize(
    'excluded_tags',
    [
        pytest.param([], id="No excluded tags"),
        pytest.param(['esxi_type'], id="type"),
        pytest.param(['test'], id="unknown tag"),
        pytest.param(['esxi_type', 'esxi_cluster'], id="multiple tags"),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_excluded_host_tags(vcsim_instance, dd_run_check, datadog_agent, aggregator, excluded_tags):
    vcsim_instance = copy.deepcopy(vcsim_instance)
    vcsim_instance['excluded_host_tags'] = excluded_tags
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)

    host_external_tags = ['esxi_datacenter:dc2', 'esxi_folder:folder_1', 'esxi_type:host', 'esxi_url:127.0.0.1:8989']
    vm_1_external_tags = ['esxi_datacenter:dc2', 'esxi_folder:folder_1', 'esxi_type:vm', 'esxi_url:127.0.0.1:8989']
    vm_2_external_tags = ['esxi_cluster:c1', 'esxi_compute:c1', 'esxi_type:vm', 'esxi_url:127.0.0.1:8989']

    def all_tags_for_metrics(external_tags):
        # any external tags that are filtered, including esxi_url
        return [tag for tag in external_tags if any(excluded in tag for excluded in excluded_tags) or "esxi_url" in tag]

    aggregator.assert_metric("esxi.cpu.usage.avg", value=18, tags=all_tags_for_metrics(vm_1_external_tags), hostname="vm1")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=19, tags=all_tags_for_metrics(vm_2_external_tags), hostname="vm2")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=26, tags=all_tags_for_metrics(host_external_tags), hostname="localhost.localdomain")

    def all_external_tags(external_tags):
        # all external tags that are not excluded
        return [tag for tag in external_tags if not any(excluded in tag for excluded in excluded_tags)]

    datadog_agent.assert_external_tags(
        'localhost.localdomain',
        {
            'esxi': all_external_tags(host_external_tags)
        }
     )
    datadog_agent.assert_external_tags(
        'vm1',
        {
            'esxi': all_external_tags(vm_1_external_tags)
        }
     )
    datadog_agent.assert_external_tags(
        'vm2',
        {
            'esxi': all_external_tags(vm_2_external_tags)
        }
     )