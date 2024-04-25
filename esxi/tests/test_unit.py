# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import ssl

import pytest
from mock import MagicMock, patch
from pyVmomi import vim, vmodl

from datadog_checks.esxi import EsxiCheck


@pytest.mark.usefixtures("service_instance")
def test_esxi_metric_up(instance, dd_run_check, aggregator, caplog):
    check = EsxiCheck('esxi', {}, [instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    aggregator.assert_metric('esxi.host.can_connect', 1, count=1, tags=["esxi_url:localhost"])
    assert "Connected to ESXi host localhost: VMware ESXi 6.5.0 build-123456789" in caplog.text


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, caplog, instance):
    check = EsxiCheck('esxi', {}, [instance])
    caplog.set_level(logging.WARNING)
    with pytest.raises(Exception, match="Connection refused"):
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
                'esxi_host:localhost.localdomain',
                'esxi_url:127.0.0.1:8989',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        'vm2',
        {
            'esxi': [
                'esxi_cluster:c1',
                'esxi_compute:c1',
                'esxi_type:vm',
                'esxi_url:127.0.0.1:8989',
                'esxi_host:unknown',
            ]
        },
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
                'esxi_host:hostname',
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


@pytest.mark.usefixtures("service_instance")
def test_report_vm_instance_metrics(aggregator, dd_run_check, vcsim_instance, service_instance):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                ],
            ),
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)

    service_instance.content.perfManager.QueryPerf = MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 52],
                            id=vim.PerformanceManager.MetricId(counterId=1, instance='test1'),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[30, 11],
                            id=vim.PerformanceManager.MetricId(counterId=1, instance='test2'),
                        )
                    ],
                ),
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[47, 60],
                            id=vim.PerformanceManager.MetricId(counterId=1),
                        )
                    ],
                ),
            ],
            [],
        ]
    )
    instance = copy.deepcopy(vcsim_instance)

    instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['cpu.usage.avg'],
            }
        }
    )
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)

    base_tags = ['esxi_url:127.0.0.1:8989']
    aggregator.assert_metric(
        'esxi.cpu.usage.avg',
        value=52,
        count=1,
        hostname='vm1',
        tags=base_tags + ['cpu_core:test1'],
    )
    aggregator.assert_metric(
        'esxi.cpu.usage.avg',
        value=11,
        count=1,
        hostname='vm1',
        tags=base_tags + ['cpu_core:test2'],
    )
    aggregator.assert_metric(
        'esxi.cpu.usage.avg',
        value=60,
        count=0,
        hostname='vm1',
        tags=base_tags,
    )


@pytest.mark.usefixtures("service_instance")
def test_report_instance_metrics_unknown_key(aggregator, dd_run_check, vcsim_instance, service_instance):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                ],
            ),
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)

    service_instance.content.perfManager.QueryPerf = MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[3, 10],
                            id=vim.PerformanceManager.MetricId(counterId=65541, instance='test1'),
                        )
                    ],
                ),
            ],
        ]
    )
    instance = copy.deepcopy(vcsim_instance)

    instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['mem.granted.avg'],
            }
        }
    )
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)

    base_tags = ['esxi_url:127.0.0.1:8989']
    aggregator.assert_metric(
        'esxi.mem.granted.avg',
        value=10,
        count=1,
        hostname='vm1',
        tags=base_tags + ['instance:test1'],
    )


@pytest.mark.usefixtures("service_instance")
def test_report_instance_metrics_invalid_counter_id(aggregator, dd_run_check, vcsim_instance, service_instance, caplog):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                ],
            ),
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)

    service_instance.content.perfManager.QueryPerf = MagicMock(
        side_effect=[
            [
                vim.PerformanceManager.EntityMetric(
                    entity=vim.VirtualMachine(moId="vm1"),
                    value=[
                        vim.PerformanceManager.IntSeries(
                            value=[3, 10],
                            id=vim.PerformanceManager.MetricId(counterId=500, instance='test1'),
                        )
                    ],
                ),
            ],
        ]
    )
    instance = copy.deepcopy(vcsim_instance)

    instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['cpu.usage.avg'],
            }
        }
    )
    check = EsxiCheck('esxi', {}, [instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    assert "Skipping value for counter 500, because the integration doesn't have metadata about it" in caplog.text

    aggregator.assert_metric("esxi.vm.count")
    aggregator.assert_metric("esxi.host.can_connect")
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("service_instance")
def test_report_instance_metrics_invalid_metric_name_still_collect_metrics(aggregator, dd_run_check, vcsim_instance):
    instance = copy.deepcopy(vcsim_instance)

    instance.update(
        {
            'collect_per_instance_filters': {
                'vm': ['metric.name'],
            }
        }
    )
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)
    base_tags = ["esxi_url:127.0.0.1:8989"]
    aggregator.assert_metric("esxi.cpu.usage.avg", value=26, tags=base_tags, hostname="localhost.localdomain")
    aggregator.assert_metric("esxi.mem.granted.avg", value=80, tags=base_tags, hostname="localhost.localdomain")
    aggregator.assert_metric("esxi.host.can_connect", 1, count=1, tags=base_tags)


@pytest.mark.usefixtures("service_instance")
def test_invalid_instance_filters(dd_run_check, vcsim_instance, caplog):
    instance = copy.deepcopy(vcsim_instance)

    instance.update(
        {
            'collect_per_instance_filters': {
                'cluster': ['cpu.usage.avg'],
            }
        }
    )
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)
    assert "Ignoring metric_filter for resource 'cluster'. It should be one of 'host, vm'" in caplog.text


@pytest.mark.parametrize(
    'excluded_tags, expected_warning',
    [
        pytest.param([], None, id="No excluded tags"),
        pytest.param(['esxi_type'], None, id="type"),
        pytest.param(
            ['test'],
            "Unknown host tag `test` cannot be excluded. Available host tags are: `esxi_url`, `esxi_type`, "
            "`esxi_host`, `esxi_folder`, `esxi_cluster` `esxi_compute`, `esxi_datacenter`, and `esxi_datastore`",
            id="unknown tag",
        ),
        pytest.param(
            ['esxi_type', 'esxi_cluster', 'hello'],
            "Unknown host tag `hello` cannot be excluded. Available host tags are: `esxi_url`, `esxi_type`, "
            "`esxi_host`, `esxi_folder`, `esxi_cluster` `esxi_compute`, `esxi_datacenter`, and `esxi_datastore`",
            id="known and unknown tags together",
        ),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_excluded_host_tags(
    vcsim_instance, dd_run_check, datadog_agent, aggregator, excluded_tags, expected_warning, caplog
):
    vcsim_instance = copy.deepcopy(vcsim_instance)
    vcsim_instance['excluded_host_tags'] = excluded_tags
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    if expected_warning is not None:
        assert expected_warning in caplog.text

    host_external_tags = ['esxi_datacenter:dc2', 'esxi_folder:folder_1', 'esxi_type:host', 'esxi_url:127.0.0.1:8989']
    vm_1_external_tags = [
        'esxi_datacenter:dc2',
        'esxi_folder:folder_1',
        'esxi_type:vm',
        'esxi_url:127.0.0.1:8989',
        'esxi_host:localhost.localdomain',
    ]
    vm_2_external_tags = [
        'esxi_cluster:c1',
        'esxi_compute:c1',
        'esxi_type:vm',
        'esxi_url:127.0.0.1:8989',
        'esxi_host:unknown',
    ]

    def all_tags_for_metrics(external_tags):
        # any external tags that are filtered, including esxi_url
        return [tag for tag in external_tags if any(excluded in tag for excluded in excluded_tags) or "esxi_url" in tag]

    aggregator.assert_metric(
        "esxi.cpu.usage.avg", value=18, tags=all_tags_for_metrics(vm_1_external_tags), hostname="vm1"
    )
    aggregator.assert_metric(
        "esxi.cpu.usage.avg", value=19, tags=all_tags_for_metrics(vm_2_external_tags), hostname="vm2"
    )
    aggregator.assert_metric(
        "esxi.cpu.usage.avg", value=26, tags=all_tags_for_metrics(host_external_tags), hostname="localhost.localdomain"
    )

    def all_external_tags(external_tags):
        # all external tags that are not excluded
        return [tag for tag in external_tags if not any(excluded in tag for excluded in excluded_tags)]

    datadog_agent.assert_external_tags('localhost.localdomain', {'esxi': all_external_tags(host_external_tags)})
    datadog_agent.assert_external_tags('vm1', {'esxi': all_external_tags(vm_1_external_tags)})
    datadog_agent.assert_external_tags('vm2', {'esxi': all_external_tags(vm_2_external_tags)})


@pytest.mark.usefixtures("service_instance")
def test_version_metadata(vcsim_instance, dd_run_check, datadog_agent):
    check = EsxiCheck('esxi', {}, [vcsim_instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '6',
        'version.minor': '5',
        'version.patch': '0',
        'version.build': '123456789',
        'version.raw': '6.5.0+123456789',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures("service_instance")
def test_invalid_api_type(vcsim_instance, dd_run_check, aggregator, service_instance):
    service_instance.content.about.apiType = "VirtualCenter"
    check = EsxiCheck('esxi', {}, [vcsim_instance])

    with pytest.raises(
        Exception,
        match="127.0.0.1:8989 is not an ESXi host; please set the `host` config option to an ESXi host "
        "or use the vSphere integration to collect data from the vCenter",
    ):
        dd_run_check(check)

    aggregator.assert_metric("esxi.host.can_connect", 0, tags=['esxi_url:127.0.0.1:8989'])
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("service_instance")
def test_runtime_host_not_found(vcsim_instance, dd_run_check, caplog, service_instance):
    retrieve_result = vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val='test',
                    ),
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                ],
            )
        ]
    )
    service_instance.content.propertyCollector.RetrievePropertiesEx = MagicMock(return_value=retrieve_result)
    caplog.set_level(logging.DEBUG)
    check = EsxiCheck('esxi', {}, [vcsim_instance])

    dd_run_check(check)
    assert "Missing runtime.host details for VM vm1" in caplog.text


@pytest.mark.usefixtures("service_instance")
def test_ssl_default(vcsim_instance, dd_run_check, service_instance):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = False

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations, patch('ssl.SSLContext.load_default_certs') as load_default_certs:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_NONE
        assert not context.check_hostname
        load_default_certs.assert_called_with(ssl.Purpose.SERVER_AUTH)
        load_verify_locations.assert_not_called()


@pytest.mark.usefixtures("service_instance")
def test_ssl_enabled(vcsim_instance, dd_run_check):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_default_certs'
    ) as load_default_certs, patch('ssl.SSLContext.load_verify_locations') as load_verify_locations:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        load_default_certs.assert_called_with(ssl.Purpose.SERVER_AUTH)
        load_verify_locations.assert_not_called()


@pytest.mark.usefixtures("service_instance")
def test_ssl_enabled_capath(vcsim_instance, dd_run_check):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True
    instance['ssl_capath'] = '/test/path'

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_default_certs'
    ) as load_default_certs, patch('ssl.SSLContext.load_verify_locations') as load_verify_locations:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        load_verify_locations.assert_called_with(cafile=None, capath='/test/path', cadata=None)
        load_default_certs.assert_not_called()


@pytest.mark.usefixtures("service_instance")
def test_ssl_enabled_cafile(vcsim_instance, dd_run_check):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True
    instance['ssl_cafile'] = '/test/path/file.pem'

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_default_certs'
    ) as load_default_certs, patch('ssl.SSLContext.load_verify_locations') as load_verify_locations:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        load_verify_locations.assert_called_with(cafile='/test/path/file.pem', capath=None, cadata=None)
        load_default_certs.assert_not_called()


@pytest.mark.usefixtures("service_instance")
def test_ssl_enabled_cafile_ssl_capath(vcsim_instance, dd_run_check):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = True
    instance['ssl_cafile'] = '/test/path/file.pem'
    instance['ssl_capath'] = '/test/path'

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations, patch('ssl.SSLContext.load_default_certs') as load_default_certs:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        load_verify_locations.assert_called_with(cafile=None, capath='/test/path', cadata=None)
        load_default_certs.assert_not_called()


@pytest.mark.usefixtures("service_instance")
def test_ssl_disabled_cafile_ssl_capath(vcsim_instance, dd_run_check):
    instance = copy.deepcopy(vcsim_instance)
    instance['ssl_verify'] = False
    instance['ssl_cafile'] = '/test/path/file.pem'
    instance['ssl_capath'] = '/test/path'

    with patch("pyVim.connect.SmartConnect") as smart_connect, patch(
        'ssl.SSLContext.load_verify_locations'
    ) as load_verify_locations, patch('ssl.SSLContext.load_default_certs') as load_default_certs:
        smart_connect.return_value.content.about.apiType = 'HostAgent'
        check = EsxiCheck('esxi', {}, [instance])
        dd_run_check(check)
        context = smart_connect.call_args.kwargs['sslContext']
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_NONE
        assert not context.check_hostname
        load_verify_locations.assert_called_with(cafile=None, capath='/test/path', cadata=None)
        load_default_certs.assert_not_called()


@pytest.mark.parametrize(
    "resource_filters, expected_vms",
    [
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            ["vm1"],
            id="include list- name",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            ["vm2"],
            id="exclude list- name",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'vm.*',
                    ],
                }
            ],
            [],
            id="all excluded- name",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'test.*',
                    ],
                }
            ],
            ["vm1", "vm2"],
            id="none excluded- name",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'test.*',
                    ],
                },
            ],
            [],
            id="unrecognized pattern- name",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'localhost.*',
                    ],
                }
            ],
            ["vm1"],
            id="include on hostname",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'localhost.*',
                    ],
                }
            ],
            ["vm2"],
            id="exclude on hostname",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'hostname.*',
                    ],
                }
            ],
            ["vm1", "vm2"],
            id="hostname not valid",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'guest_hostname',
                    'patterns': [
                        'testing.*',
                    ],
                }
            ],
            ["vm2"],
            id="exclude on guest_hostname",
        ),
        pytest.param(
            [
                {
                    'resource': 'vm',
                    'property': 'guest_hostname',
                    'patterns': [
                        'hey.*',
                    ],
                }
            ],
            [],
            id="include on guest_hostname",
        ),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_resource_filters_vm(vcsim_instance, dd_run_check, resource_filters, expected_vms, aggregator):
    instance = copy.deepcopy(vcsim_instance)
    instance['resource_filters'] = resource_filters
    all_vms = ["vm1", "vm2"]
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)

    for vm in all_vms:
        expected_count = 1 if vm in expected_vms else 0
        aggregator.assert_metric("esxi.cpu.usage.avg", count=expected_count, hostname=vm)


@pytest.mark.parametrize(
    "resource_filters, expected_host",
    [
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            0,
            id="include list invalid",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        '.*',
                    ],
                }
            ],
            1,
            id="include list valid",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        '.*',
                    ],
                }
            ],
            0,
            id="exclude list valid",
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        '.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        '.*',
                    ],
                },
            ],
            0,
            id="exclude and include list",
        ),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_resource_filters_host(vcsim_instance, dd_run_check, resource_filters, expected_host, aggregator):
    instance = copy.deepcopy(vcsim_instance)
    instance['resource_filters'] = resource_filters
    check = EsxiCheck('esxi', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("esxi.cpu.usage.avg", count=expected_host, hostname="localhost.localdomain")


@pytest.mark.parametrize(
    "resource_filters, expected_error",
    [
        pytest.param(
            [
                {
                    'type': 'include',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'property': 'name', 'patterns': ['vm1.*']} "
            "because it doesn't contain a resource field.",
            id="no resource",
        ),
        pytest.param(
            [{}],
            "Ignoring filter {'type': 'include', 'property': 'name'} because it doesn't contain a resource field.",
            id="empty filter",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'cluster',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'resource': 'cluster', 'property': 'name', 'patterns': ['vm1.*']} "
            "because resource cluster is not a supported resource",
            id="invalid resource",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'host',
                    'property': 'hostname',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'resource': 'host', 'property': 'hostname', 'patterns': ['vm1.*']} "
            "because property 'hostname' is not valid for resource type host. Should be one of ['name'].",
            id="invalid property",
        ),
        pytest.param(
            [
                {
                    'type': 'included',
                    'resource': 'host',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'included', 'resource': 'host', 'property': 'name', 'patterns': ['vm1.*']} "
            "because type 'included' is not valid. Should be one of ['include', 'exclude'].",
            id="invalid type",
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'vm1.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'name',
                    'patterns': [
                        'vm.*',
                    ],
                },
            ],
            "Ignoring filter {'type': 'include', 'resource': 'vm', 'property': 'name', 'patterns': ['vm.*']} "
            "because you already have a `include` filter for resource type vm and property name.",
            id="duplicate filters",
        ),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_resource_filters_invalid(vcsim_instance, dd_run_check, resource_filters, expected_error, caplog):
    caplog.set_level(logging.WARNING)
    instance = copy.deepcopy(vcsim_instance)
    instance['resource_filters'] = resource_filters
    check = EsxiCheck('esxi', {}, [instance])

    dd_run_check(check)
    assert expected_error in caplog.text


@pytest.mark.parametrize(
    "metric_filters, expected_metrics",
    [
        pytest.param(
            {},
            [
                ('esxi.cpu.usage.avg', 'vm1'),
                ('esxi.cpu.usage.avg', 'vm2'),
                ('esxi.cpu.usage.avg', 'localhost.localdomain'),
                ('esxi.mem.granted.avg', 'localhost.localdomain'),
                ('esxi.net.droppedRx.sum', 'vm1'),
            ],
            id="no filters",
        ),
        pytest.param(
            {'vm': ['net.droppedRx.sum']},
            [
                ('esxi.cpu.usage.avg', 'vm1'),
                ('esxi.cpu.usage.avg', 'vm2'),
                ('esxi.net.droppedRx.sum', 'vm1'),
                ('esxi.mem.granted.avg', 'localhost.localdomain'),
                ('esxi.cpu.usage.avg', 'localhost.localdomain'),
            ],
            id="vm filters",
        ),
        pytest.param(
            {'host': ['cpu.usage.avg']},
            [
                ('esxi.cpu.usage.avg', 'vm1'),
                ('esxi.cpu.usage.avg', 'vm2'),
                ('esxi.net.droppedRx.sum', 'vm1'),
                ('esxi.cpu.usage.avg', 'localhost.localdomain'),
            ],
            id="host filters",
        ),
        pytest.param(
            {'host': ['test']},
            [
                ('esxi.cpu.usage.avg', 'vm1'),
                ('esxi.cpu.usage.avg', 'vm2'),
                ('esxi.net.droppedRx.sum', 'vm1'),
                ('esxi.cpu.usage.avg', 'localhost.localdomain'),
            ],
            id="host no matching filters",
        ),
        pytest.param(
            {'host': ['mem.granted.avg', 'test'], 'vm': ['test']},
            [
                ('esxi.cpu.usage.avg', 'vm1'),
                ('esxi.cpu.usage.avg', 'vm2'),
                ('esxi.cpu.usage.avg', 'localhost.localdomain'),
                ('esxi.mem.granted.avg', 'localhost.localdomain'),
            ],
            id="both filters",
        ),
    ],
)
@pytest.mark.usefixtures("service_instance")
def test_vm_metrics_filters(vcsim_instance, dd_run_check, metric_filters, expected_metrics, aggregator):
    instance = copy.deepcopy(vcsim_instance)
    instance['metric_filters'] = metric_filters
    check = EsxiCheck('esxi', {}, [instance])

    dd_run_check(check)

    for metric_name, hostname in expected_metrics:
        aggregator.assert_metric(metric_name, hostname=hostname, count=1)

    aggregator.assert_metric('esxi.host.can_connect')
    aggregator.assert_metric('esxi.host.count')
    aggregator.assert_metric('esxi.vm.count')
    aggregator.assert_all_metrics_covered()
