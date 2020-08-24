# Agent Check: VMWare vSphere

![Vsphere Graph][1]

## Overview

This check collects resource usage metrics from your vSphere cluster-CPU, disk, memory, and network usage. It also watches your vCenter server for events and emits them to Datadog.

## Setup

### Installation

The vSphere check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your vCenter server.

### Configuration

In the **Administration** section of vCenter, add a read-only user called `datadog-readonly`.

Then, edit the `vsphere.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample vsphere.d/conf.yaml][4] for all available configuration options:

```YAML
init_config:

instances:
  - name: main-vcenter
    host: "<VCENTER_HOSTNAME>"
    username: "<USER_YOU_JUST_CREATED>"
    password: "<PASSWORD>"
```

[Restart the Agent][5] to start sending vSphere metrics and events to Datadog.

**Note**: The Datadog Agent doesn't need to be on the same server as the vSphere appliance software. An Agent with the vSphere check enabled can be set up -no matter what OS it's running on- to point to a vSphere appliance server. Update your `<VCENTER_HOSTNAME>` accordingly.

### Compatibility

Starting with version 3.3.0 of the check, shipped in Agent version 6.5.0/5.27.0, a new optional parameter `collection_level` is available to select which metrics to collect from vCenter, and the optional parameter `all_metrics` was deprecated. Along with this change, the names of the metrics sent to Datadog by the integration have changed, with the addition of a suffix specifying the rollup type of the metric exposed by vCenter (`.avg`, `.sum`, etc.).

By default, starting with version 3.3.0, the `collection_level` is set to 1 and the new metric names with the additional suffix are sent by the integration.

The following scenarios are possible when using the vSphere integration:

1. You never used the integration before, and you just installed an Agent with version 6.5.0+ / 5.27.0+. There is nothing specific in this case. Use the integration, configure the `collection_level`, and view your metrics in Datadog.

2. You used the integration with an Agent older than 6.5.0/5.27.0, and upgraded to a newer version/

   - If your configuration specifically set the `all_metrics` parameter to either `true` or `false`, nothing changes (the same metrics are sent to Datadog). You should then update your dashboards and monitors to use the new metric names before switching to the new `collection_level` parameter, since `all_metrics` is deprecated and will eventually be removed.
   - If your configuration did not specify the `all_metrics` parameter, upon upgrade the integration defaults to the `collection_level` parameter set to 1 and sends the metrics with the new name to Datadog.
     **Warning**: this breaks your dashboard graphs and monitors scoped on the deprecated metrics, which stop being sent. To prevent this, you should explicitly set `all_metrics: false` in your configuration to continue reporting the same metrics, then update your dashboards and monitors to use the new metrics before switching back to using `collection_level`.

#### Configuration Options

| Options                   | Required | Description                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ssl_verify`              | No       | Set to false to disable SSL verification, when connecting to vCenter.                                                                                                                                                                                                                                                                                            |
| `ssl_capath`              | No       | Set to the absolute file path of a directory containing CA certificates in PEM format.                                                                                                                                                                                                                                                                            |
| `resource_filters`        | No       | Set parameters (`resource`, `property`, `type` `patterns`) to apply a filter to a VM, host, datastore, datacenter or a compute cluster. **Requires Datadog Agent v6, v7.18+.**                                                                                                                                                                                         |
| `collection_level`        | No       | A number between 1 and 4 to specify how many metrics are sent, 1 meaning only important monitoring metrics and 4 meaning every metric available. Data collection levels are documented by VMware [on their site][12].                                                                                                                                                                                                                |

### Validation

[Run the Agent's status subcommand][7] and look for `vsphere` under the Checks section.

## Data Collected

Depending of the `collection_level` value you set in your check configuration, not all metrics below are collected. See the [Vsphere Data Collection Levels documentation][8] to discover for a given collection level which metrics are collected.

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

This check watches vCenter's Event Manager for events and emits them to Datadog. It emits the following event types:

- AlarmStatusChangedEvent:Gray
- VmBeingHotMigratedEvent
- VmReconfiguredEvent
- VmPoweredOnEvent
- VmMigratedEvent
- TaskEvent:Initialize powering On
- TaskEvent:Power Off virtual machine
- TaskEvent:Power On virtual machine
- TaskEvent:Reconfigure virtual machine
- TaskEvent:Relocate virtual machine
- TaskEvent:Suspend virtual machine
- TaskEvent:Migrate virtual machine
- VmMessageEvent
- VmSuspendedEvent
- VmPoweredOffEvent

### Service Checks

**vcenter.can_connect**:<br>
Returns CRITICAL if the Agent cannot connect to vCenter to collect metrics, otherwise OK.

## Troubleshooting

- [Can I limit the number of VMs that are pulled in via the VMWare integration?][10]

## Further Reading

See our [blog post][11] on monitoring vSphere environments with Datadog.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/vsphere/images/vsphere_graph.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/vsphere/datadog_checks/vsphere/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://pubs.vmware.com/vsphere-51/index.jsp?topic=%2Fcom.vmware.powercli.cmdletref.doc%2FSet-CustomField.html
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.monitoring.doc/GUID-25800DE4-68E5-41CC-82D9-8811E27924BC.html
[9]: https://github.com/DataDog/integrations-core/blob/master/vsphere/metadata.csv
[10]: https://docs.datadoghq.com/integrations/faq/can-i-limit-the-number-of-vms-that-are-pulled-in-via-the-vmware-integration/
[11]: https://www.datadoghq.com/blog/unified-vsphere-app-monitoring-datadog/#auto-discovery-across-vm-and-app-layers
[12]: https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.monitoring.doc/GUID-25800DE4-68E5-41CC-82D9-8811E27924BC.html
