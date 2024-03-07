# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

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
def test_esxi_no_hostname_data(vcsim_instance, dd_run_check, aggregator, service_instance, caplog):
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

    assert "No host name found" in caplog.text

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)
    aggregator.assert_all_metrics_covered()


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
    "returned by the Host is negative (i.e. the metric is not yet available). values: [-1]" in caplog.text

    assert (
        "Skipping metric net.droppedRx.sum for localhost.localdomain because no value was returned by the Host"
        in caplog.text
    )


@pytest.mark.usefixtures("service_instance")
def test_vm_perf_metrics(vcsim_instance, dd_run_check, aggregator, caplog):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.cpu.usage.avg", value=18, tags=base_tags, hostname="vm1")
    aggregator.assert_metric("esxi.cpu.usage.avg", value=19, tags=base_tags, hostname="vm2")
    aggregator.assert_metric("esxi.net.droppedRx.sum", value=28, tags=base_tags, hostname="vm1")
