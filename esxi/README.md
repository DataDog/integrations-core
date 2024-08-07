# Agent Check: ESXi

## Overview

This check monitors your vSphere [ESXi][1] hosts and the virtual machines running on them in a distributed manner. To monitor your entire vSphere deployment in a centralized way through your vCenter, see the [vSphere integration][11].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The ESXi check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `esxi.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ESXi performance data. See the [sample esxi.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `esxi` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.


#### Collecting per-instance metrics

**Note**: The ESXi integration has the ability to collect both per-resource metrics (such as those related to CPUs), and per-instance metrics (such as those related to CPU cores). As such, there are metrics that are only per-resource, per-instance, or both.
A resource represents a physical or virtual representation of a machine. This can be represented by vm, host, datastore, cluster in vSphere.
An instance represents individual entities found within a resource. More information on vSphere resources can be found in the [VMWare Infrastructure Architecture Overview white paper][10].

By default, the ESXi integration only collects per-resource metrics, which causes some metrics that are per-instance to be ignored. These can be configured using the `collect_per_instance_filters` option. See below for an example:

```
collect_per_instance_filters:
  host:
    - 'disk\.totalLatency\.avg'
    - 'disk\.deviceReadLatency\.avg'
```

`disk` metrics are specific for each disk on the host, therefore these metrics need to be enabled using `collect_per_instance_filters` to be collected.


### Events

The ESXi integration does not include any events.

### Service Checks

The ESXi integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.vmware.com/products/esxi-and-esx.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/esxi/datadog_checks/esxi/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/esxi/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/esxi/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.vmware.com/pdf/vi_architecture_wp.pdf
[11]: https://docs.datadoghq.com/integrations/vsphere/
