# Agent Check: VMWare vSphere

![Vsphere Graph][1]

## Overview

This check collects resource usage metrics from your vSphere cluster-CPU, disk, memory, and network usage. It also watches your vCenter server for events and emits them to Datadog.

## Setup

### Installation

The vSphere check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your vCenter server.

### Configuration

In the **Administration** section of vCenter, add a read-only user called `datadog-readonly`.

Then, edit the `vsphere.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample vsphere.d/conf.yaml][4] for all available configuration options.

[Restart the Agent][5] to start sending vSphere metrics and events to Datadog.

**Note**: The Datadog Agent doesn't need to be on the same server as the vSphere appliance software. An Agent with the vSphere check enabled can be set up - no matter what OS it's running on - to point to a vSphere appliance server. Update your `<HOSTNAME>` for each instance accordingly.

### Compatibility

Starting with version 5.0.0 of the check, shipped in Agent version 6.18.0/7.18.0, a new implementation of the integration was introduced which required changes to the configuration file. To preserve backwards compatibility, a configuration parameter called `use_legacy_implementation` was temporarily introduced,
If you are upgrading from an older version of the integration, this parameter is unset in the config and forces the agent to use the older implementation.
If you are configuring the integration from the first time or if you want to benefit from the new features (like tag collection and advanced filtering options), refer to the [sample vsphere.d/conf.yaml][4] configuration file. In particular, make sure to set `use_legacy_implementation: false`.

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
Returns `CRITICAL` if the Agent cannot connect to vCenter to collect metrics, otherwise `OK`.

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
