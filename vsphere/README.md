# Agent Check: VMWare vSphere

![Vsphere Graph][8]

## Overview

This check collects resource usage metrics from your vSphere cluster-CPU, disk, memory, and network usage. It also watches your vCenter server for events and emits them to Datadog.

## Setup
### Installation

The vSphere check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your vCenter server.

### Configuration

In the Administration section of vCenter, add a read-only user called datadog-readonly.

Then, edit the `vsphere.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][9]. See the [sample vsphere.d/conf.yaml][2] for all available configuration options:

```
init_config:

instances:
  - name: main-vcenter # how metrics will be tagged, i.e. 'vcenter_server:main-vcenter'
    host: <VCENTER_HOSTNAME>          # e.g. myvcenter.example.com
    username: <USER_YOU_JUST_CREATED> # e.g. datadog-readonly@vsphere.local
    password: <PASSWORD>
```

[Restart the Agent][3] to start sending vSphere metrics and events to Datadog.

**Note**: The Datadog Agent doesn't need to be on the same server as the vSphere appliance software. An Agent with the vSphere check enabled can be set up -no matter what OS it's running on- to point to a vSphere appliance server. You will have to update your `<VCENTER_HOSTNAME>` accordingly.

#### Configuration Options

* `ssl_verify` (Optional) - Set to false to disable SSL verification, when connecting to vCenter
* `ssl_capath` (Optional) - Set to the absolute file path of a directory containing CA certificates in PEM format
* `host_include_only_regex` (Optional) - Use a regex like this if you want only the check to fetch metrics for these ESXi hosts and the VMs running on it
* `vm_include_only_regex` (Optional) - Use a regex to include only the VMs that are matching this pattern.
* `include_only_marked` (Optional) - Set to true if you'd like to only collect metrics on vSphere VMs which are marked by a custom field with the value 'DatadogMonitored'. To set this custom field with PowerCLI, use the follow command: `Get-VM <MyVMName> | Set-CustomField -Name "DatadogMonitored" -Value "DatadogMonitored"`
* `all_metrics` (Optional) - When set to true, this will collect EVERY metric from vCenter, which means a LOT of metrics you probably do not care about. We have selected a set of metrics that are interesting to monitor for you if false.
* `event_config` (Optional) - Event config is a dictionary. For now the only switch you can flip is collect_vcenter_alarms which will send as events the alarms set in vCenter.

### Validation

[Run the Agent's `status` subcommand][4] and look for `vsphere` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events

This check watches vCenter's Event Manager for events and emits them to Datadog. It does NOT emit the following event types:

* AlarmStatusChangedEvent:Gray
* VmBeingHotMigratedEvent
* VmResumedEvent
* VmReconfiguredEvent
* VmPoweredOnEvent
* VmMigratedEvent
* TaskEvent:Initialize powering On
* TaskEvent:Power Off virtual machine
* TaskEvent:Power On virtual machine
* TaskEvent:Reconfigure virtual machine
* TaskEvent:Relocate virtual machine
* TaskEvent:Suspend virtual machine
* TaskEvent:Migrate virtual machine
* VmMessageEvent
* VmSuspendedEvent
* VmPoweredOffEvent

### Service Checks

`vcenter.can_connect`:

Returns CRITICAL if the Agent cannot connect to vCenter to collect metrics, otherwise OK.

## Troubleshooting

* [Can I limit the number of VMs that are pulled in via the VMWare integration?][6]

## Further Reading
See our [blog post][7] on monitoring vSphere environments with Datadog.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/vsphere/datadog_checks/vsphere/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/vsphere/metadata.csv
[6]: https://docs.datadoghq.com/integrations/faq/can-i-limit-the-number-of-vms-that-are-pulled-in-via-the-vmware-integration
[7]: https://www.datadoghq.com/blog/unified-vsphere-app-monitoring-datadog/#auto-discovery-across-vm-and-app-layers
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/vsphere/images/vsphere_graph.png
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
