# Agent Check: Openstack_controller

## Overview

This check monitors [Openstack][1] from the controller node.

## Setup
### Installation

The Openstack_controller check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

The openstack_controller integration is designed to collect information from all compute nodes and the servers running on them. This integration is designed to be run from a single Agent to monitor your openstack environment. This can be deployed on your controller node or an adjacent server that has access to the Keystone and Nova endpoints.

#### Prepare OpenStack

Create a `datadog` user that is used in your `openstack_controller.d/conf.yaml` file. This user requires admin read only permissions across your environment so that it can be run from a single node and read high level system information about all compute nodes and servers.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your openstack_controller performance data.
   See the [sample openstack_controller.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                                                                                                       |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `openstack_controller`                                                                                                                                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                                                                                               |
| `<INSTANCE_CONFIG>`  | `"name": "<INSTANCE_NAME>", "keystone_server_url": "https://<KEYSTONE_SERVER_ENDPOINT>:<PORT>/" "user":{"password": "<PASSWORD>", "name": "<USER_NAME>", "domain": {"id": "<DOMAINE_ID>"}}` |

### Validation

[Run the Agent's `status` subcommand][5] and look for `openstack_controller` under the Checks section.

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

Need help? Contact [Datadog support][7].

[1]: https://www.openstack.org
[2]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/autodiscovery/integrations/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/metadata.csv
[7]: https://docs.datadoghq.com/help
