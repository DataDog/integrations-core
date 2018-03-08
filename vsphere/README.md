# Agent Check: VMWare vSphere
{{< img src="integrations/vmware/vsphere_graph.png" alt="vsphere graph" responsive="true" popup="true">}}
## Overview

This check collects resource usage metrics from your vSphere cluster—CPU, disk, memory, and network usage. It also watches your vCenter server for events and emits them to Datadog.

## Setup
### Installation

The vSphere check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your vCenter server.

If you need the newest version of the vSphere check, install the `dd-check-vsphere` package; this package's check overrides the one packaged with the Agent. See the [Installing Core & Extra Integrations documentation page](https://docs.datadoghq.com/agent/faq/install-core-extra/) for more details.

### Configuration

In the Administration section of vCenter, add a read-only user called datadog-readonly.

Then, create a file `vsphere.yaml` in the Datadog Agent's `conf.d` directory. See the [sample vsphere.yaml](https://github.com/DataDog/integrations-core/blob/master/vsphere/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - name: main-vcenter # how metrics will be tagged, i.e. 'vcenter_server:main-vcenter'
    host: <VCENTER_HOSTNAME>          # e.g. myvcenter.example.com
    username: <USER_YOU_JUST_CREATED> # e.g. datadog-readonly@vsphere.local
    password: <PASSWORD>
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending vSphere metrics and events to Datadog.

#### Configuration Options

* `ssl_verify` (Optional) - Set to false to disable SSL verification, when connecting to vCenter
* `ssl_capath` (Optional) - Set to the absolute file path of a directory containing CA certificates in PEM format
* `host_include_only_regex` (Optional) - Use a regex like this if you want only the check to fetch metrics for these ESXi hosts and the VMs running on it
* `vm_include_only_regex` (Optional) - Use a regex to include only the VMs that are matching this pattern.
* `include_only_marked` (Optional) - Set to true if you'd like to only collect metrics on vSphere VMs which are marked by a custom field with the value 'DatadogMonitored'. To set this custom field with PowerCLI, use the follow command: `Get-VM <MyVMName> | Set-CustomField -Name "DatadogMonitored" -Value "DatadogMonitored"`
* `all_metrics` (Optional) - When set to true, this will collect EVERY metric from vCenter, which means a LOT of metrics you probably do not care about. We have selected a set of metrics that are interesting to monitor for you if false.
* `event_config` (Optional) - Event config is a dictionary. For now the only switch you can flip is collect_vcenter_alarms which will send as events the alarms set in vCenter.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `vsphere` under the Checks section:

```
  Checks
  ======
    [...]

    vsphere
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The vsphere check is compatible with all Windows platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/vsphere/metadata.csv) for a list of metrics provided by this check.

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

* [Can I limit the number of VMs that are pulled in via the VMWare integration?](https://docs.datadoghq.com/integrations/faq/can-i-limit-the-number-of-vms-that-are-pulled-in-via-the-vmware-integration)

## Further Reading
See our [blog post](https://www.datadoghq.com/blog/unified-vsphere-app-monitoring-datadog/#auto-discovery-across-vm-and-app-layers) on monitoring vSphere environments with Datadog.
