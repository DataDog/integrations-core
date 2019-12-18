# Agent Check: Openstack_controller

## Overview

This check monitors [Openstack][1] from the controller node.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying these instructions.

### Installation

The Openstack_controller check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

#### Prepare OpenStack

Create a `datadog` user that is used in your `openstack_controller.d/conf.yaml` file. This user requires admin read only permissions across your environment so that it can be run from a single node and read high level system information about all compute nodes and servers.

#### Deployment Strategy

The openstack_controller integration is designed to collect information from all compute nodes and the servers running on them. This integration is designed to be run from a single Agent to monitor your openstack environment. This can be deployed on your controller node or an adjacent server that has access to the Keystone and Nova endpoints.

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your openstack_controller performance data.
   See the [sample openstack_controller.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `openstack_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks
**openstack.neutron.api.up**

Returns `CRITICAL` if the Agent is unable to query the Neutron API, `UNKNOWN` if there is an issue with the Keystone API. Returns `OK` otherwise.

**openstack.nova.api.up**

Returns `CRITICAL` if the Agent is unable to query the Nova API, `UNKNOWN` if there is an issue with the Keystone API. Returns `OK` otherwise.

**openstack.keystone.api.up**

Returns `CRITICAL` if the Agent is unable to query the Keystone API. Returns `OK` otherwise.

**openstack.nova.hypervisor.up**

Returns `UNKNOWN` if the Agent is unable to get the Hypervisor state, `CRITICAL` if the Hypervisor is down. Returns `OK` otherwise.

**openstack.neutron.network.up**

Returns `CRITICAL` if the Network is down. Returns `OK` otherwise.


### Events

Openstack_controller does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.openstack.org
[2]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help
[6]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/metadata.csv
[7]: https://docs.datadoghq.com/agent/autodiscovery/integrations
