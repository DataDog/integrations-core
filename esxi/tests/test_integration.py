# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging

import pytest

from datadog_checks.esxi import EsxiCheck

from .common import (
    ALL_VCSIM_HOST_METRICS_WITH_VALS,
    ALL_VCSIM_VM_METRICS_WITH_VALS,
    FLAKEY_HOST_METRICS,
    FLAKEY_VM_METRICS,
    VCSIM_HOST_METRICS,
    VCSIM_VM_METRICS,
)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_esxi_metric_up(vcsim_instance, dd_run_check, aggregator):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)
    aggregator.assert_metric('esxi.host.can_connect', 1, count=1, tags=["esxi_url:127.0.0.1:8989"])


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_esxi_perf_metrics(vcsim_instance, dd_run_check, aggregator, caplog):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)

    base_tags = ["esxi_url:127.0.0.1:8989"]
    all_expected_host_metrics = set(ALL_VCSIM_HOST_METRICS_WITH_VALS) - set(FLAKEY_HOST_METRICS)
    for metric_name in all_expected_host_metrics:
        aggregator.assert_metric(f"esxi.{metric_name}", tags=base_tags, hostname="localhost.localdomain")

    # some metrics are flakey in the VCSIM env
    for metric_name in FLAKEY_HOST_METRICS:
        aggregator.assert_metric(f"esxi.{metric_name}", at_least=0, tags=base_tags, hostname="localhost.localdomain")

    # assert that the missing metrics are skipped due to missing values
    host_metrics_without_vals = (
        set(VCSIM_HOST_METRICS) - set(ALL_VCSIM_HOST_METRICS_WITH_VALS) - set(FLAKEY_HOST_METRICS)
    )
    for metric_name in host_metrics_without_vals:
        log_line = f"Skipping metric {metric_name} for localhost.localdomain because no value was returned by the host"
        assert log_line in caplog.text

    all_expected_vm_metrics = set(ALL_VCSIM_VM_METRICS_WITH_VALS) - set(FLAKEY_VM_METRICS)

    for metric_name in all_expected_vm_metrics:
        aggregator.assert_metric(f"esxi.{metric_name}", at_least=1, tags=base_tags, hostname="ha-host_VM0")
        aggregator.assert_metric(f"esxi.{metric_name}", at_least=1, tags=base_tags, hostname="ha-host_VM1")

    vm_metrics_without_vals = set(VCSIM_VM_METRICS) - set(ALL_VCSIM_VM_METRICS_WITH_VALS) - set(FLAKEY_VM_METRICS)
    for metric_name in vm_metrics_without_vals:
        log_line_vm0 = f"Skipping metric {metric_name} for ha-host_VM0 because no value was returned by the vm"
        log_line_vm1 = f"Skipping metric {metric_name} for ha-host_VM1 because no value was returned by the vm"
        assert log_line_vm0 in caplog.text
        assert log_line_vm1 in caplog.text

    # some metrics are flakey in the VCSIM env
    for metric_name in FLAKEY_VM_METRICS:
        aggregator.assert_metric(f"esxi.{metric_name}", at_least=0, tags=base_tags, hostname="ha-host_VM0")
        aggregator.assert_metric(f"esxi.{metric_name}", at_least=0, tags=base_tags, hostname="ha-host_VM1")

    aggregator.assert_metric("esxi.host.count")
    aggregator.assert_metric("esxi.vm.count")
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_vcsim_external_host_tags(vcsim_instance, datadog_agent, dd_run_check):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)
    datadog_agent.assert_external_tags(
        'localhost.localdomain',
        {
            'esxi': [
                'esxi_compute:localhost.localdomain',
                'esxi_datacenter:ha-datacenter',
                'esxi_folder:ha-folder-root',
                'esxi_folder:host',
                'esxi_type:host',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'ha-host_VM0',
        {
            'esxi': [
                'esxi_datacenter:ha-datacenter',
                'esxi_folder:ha-folder-root',
                'esxi_folder:vm',
                'esxi_type:vm',
                'esxi_host:localhost.localdomain',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'ha-host_VM1',
        {
            'esxi': [
                'esxi_datacenter:ha-datacenter',
                'esxi_folder:ha-folder-root',
                'esxi_folder:vm',
                'esxi_type:vm',
                'esxi_host:localhost.localdomain',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_esxi_resource_count_metrics(vcsim_instance, dd_run_check, aggregator):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    dd_run_check(check)

    host_tags = [
        'esxi_compute:localhost.localdomain',
        'esxi_datacenter:ha-datacenter',
        'esxi_folder:ha-folder-root',
        'esxi_folder:host',
        'esxi_type:host',
        'esxi_url:127.0.0.1:8989',
    ]
    vm_tags = [
        'esxi_datacenter:ha-datacenter',
        'esxi_folder:ha-folder-root',
        'esxi_folder:vm',
        'esxi_type:vm',
        'esxi_host:localhost.localdomain',
        'esxi_url:127.0.0.1:8989',
    ]

    aggregator.assert_metric("esxi.host.count", 1, tags=host_tags, hostname=None)
    aggregator.assert_metric("esxi.vm.count", 2, tags=vm_tags, hostname=None)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_ssl_verify(vcsim_instance, dd_run_check, aggregator):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True
    check = EsxiCheck('esxi', {}, [instance])
    with pytest.raises(
        Exception,
        match=r"\[SSL: CERTIFICATE_VERIFY_FAILED\] certificate verify failed",
    ):
        dd_run_check(check)

    aggregator.assert_metric('esxi.host.can_connect', 0, count=1, tags=["esxi_url:127.0.0.1:8989"])


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_ssl_verify_cafile(vcsim_instance, dd_run_check, aggregator):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True
    instance['ssl_cafile'] = '/test/path/file.pem'
    check = EsxiCheck('esxi', {}, [instance])
    with pytest.raises(Exception, match=r"FileNotFoundError: \[Errno 2\] No such file or directory"):
        dd_run_check(check)
    aggregator.assert_metric('esxi.host.can_connect', 0, count=1, tags=["esxi_url:127.0.0.1:8989"])
