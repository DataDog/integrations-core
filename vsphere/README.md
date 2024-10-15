# Agent Check: VMWare vSphere

![Vsphere Graph][1]

## Overview

This check collects resource usage metrics from your vSphere cluster-CPU, disk, memory, and network usage. It also watches your vCenter server for events and emits them to Datadog.

## Setup

### Installation

The vSphere check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your vCenter server.

### Configuration

In the **Administration** section of vCenter, add a read-only user called `datadog-readonly` and apply the read-only user permissions to the resources that need monitoring. To monitor all child objects in the resource hierarchy, select the "Propagate to children" option. 

Then, edit the `vsphere.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample vsphere.d/conf.yaml][4] for all available configuration options.

[Restart the Agent][5] to start sending vSphere metrics and events to Datadog.

**Note**: The Datadog Agent doesn't need to be on the same server as the vSphere appliance software. An Agent with the vSphere check enabled can be set up to point to a vSphere appliance server. Update your `<HOSTNAME>` for each instance accordingly.

### Compatibility

Starting with v5.0.0 of the check, shipped in Agent v6.18.0/7.18.0, a new implementation was introduced which required changes to the configuration file. To preserve backwards compatibility, a configuration parameter called `use_legacy_check_version` was temporarily introduced.
If you are upgrading from an older version of the integration, this parameter is unset in the config and forces the Agent to use the older implementation.
If you are configuring the integration for the first time or if you want to benefit from the new features (like tag collection and advanced filtering options), see the [sample vsphere.d/conf.yaml][4] configuration file. In particular, make sure to set `use_legacy_check_version: false`.

### Validation

Run the [Agent's status subcommand][6] and look for `vsphere` under the Checks section.

## Data Collected

Depending of the `collection_level` value you set in your check configuration, not all metrics below are collected. See [Data Collection Levels][9] to display metrics collected for a given collection.

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

#### Collecting per-instance metrics

**Note**: The vSphere integration has the ability to collect both per-resource metrics (such as those related to CPUs), and per-instance metrics (such as those related to CPU cores). As such, there are metrics that are only per-resource, per-instance, or both. 
A resource represents a physical or virtual representation of a machine. This can be represented by vm, host, datastore, cluster in vSphere.
An instance represents individual entities found within a resource. More information on vSphere resources can be found in the [VMWare Infrastructure Architecture Overview white paper][11].

By default, the vSphere integration only collects per-resource metrics, which causes some metrics that are per-instance to be ignored. These can be configured using the `collect_per_instance_filters` option. See below for an example:

```
collect_per_instance_filters:
  host:
    - 'disk\.totalLatency\.avg'
    - 'disk\.deviceReadLatency\.avg'
```

`disk` metrics are specific for each disk on the host, therefore these metrics need to be enabled using `collect_per_instance_filters` to be collected.

#### Collecting property metrics

The vSphere integration can also collect property-based metrics. These are configuration properties, such as if a host is in maintenance mode or a cluster is configured with DRS.

To enable property metrics, configure the following option:
```
collect_property_metrics: true
```

Property metrics are prefixed by the resource name. For example, host property metrics metrics are prefixed with `vsphere.host.*`, and VM property metrics are prefixed with `vsphere.vm.*`. View all the possible property metrics in the [metadata.csv][10].


### Events

This check watches vCenter's Event Manager for events and emits them to Datadog. The check defaults to emit the following event types:

- AlarmStatusChangedEvent
- VmBeingHotMigratedEvent
- VmReconfiguredEvent
- VmPoweredOnEvent
- VmMigratedEvent
- TaskEvent
- VmMessageEvent
- VmSuspendedEvent
- VmPoweredOffEvent

Use the `include_events` parameter section in the [sample vsphere.d/conf.yaml][4] to collect additional events from the `vim.event` class .

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

- [Troubleshooting duplicated hosts with vSphere][8]

### Limiting VMs

You can limit the number of VMs pulled in with the VMWare integration using the `vsphere.d/conf.yaml` file. See the `resource_filters` parameter section in the [sample vsphere.d/conf.yaml][4].

### Monitoring vSphere Tanzu Kubernetes Grid (TKG)

The Datadog vSphere integration collects metrics and events from your [TKG][13] VMs and control plane VMs automatically. To collect more granular information about your TKG cluster, including container-, pod-, and node-level metrics, you can install the [Datadog Agent][14] on your cluster. See the [distribution documentation][15] for example configuration files specific to TKG.

## Further Reading

- [Monitor vSphere with Datadog][16]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/vsphere/images/vsphere_graph.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/vsphere/datadog_checks/vsphere/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/integrations/faq/troubleshooting-duplicated-hosts-with-vsphere/
[9]: https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.monitoring.doc/GUID-25800DE4-68E5-41CC-82D9-8811E27924BC.html
[10]: https://github.com/DataDog/integrations-core/blob/master/vsphere/metadata.csv
[11]: https://www.vmware.com/pdf/vi_architecture_wp.pdf
[12]: https://github.com/DataDog/integrations-core/blob/master/vsphere/assets/service_checks.json
[13]: https://tanzu.vmware.com/kubernetes-grid
[14]: https://docs.datadoghq.com/containers/kubernetes/installation/?tab=operator
[15]: https://docs.datadoghq.com/containers/kubernetes/distributions/?tab=operator#TKG
[16]: https://www.datadoghq.com/blog/unified-vsphere-app-monitoring-datadog/#auto-discovery-across-vm-and-app-layers
