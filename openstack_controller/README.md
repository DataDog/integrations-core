# Agent Check: Openstack Controller

<div class="alert alert-warning">
*Important Note*: This integration only applies to OpenStack versions 13 and above (containerized OpenStack). If you are looking to collect metrics from OpenStack v12 and below (non-containerized OpenStack) please use the <a href="https://docs.datadoghq.com/integrations/openstack/">OpenStack integration.</a>
</div>

## Overview

This check monitors [OpenStack][1] from the controller node.

## Setup

### Installation

The OpenStack Controller check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

The OpenStack Controller integration is designed to collect information from all compute nodes and the servers running it. The integration should be run from a single Agent to monitor your OpenStack environment, and can be deployed on your controller node or an adjacent server that has access to the Keystone and Nova endpoints.

#### Prepare OpenStack

Create a `datadog` user that is used in your `openstack_controller.d/conf.yaml` file. This user requires admin read-only permissions across your environment so that it can be run from a single node and read high level system information about all nodes and servers.

#### Agent Configuration

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your OpenStack Controller performance data. See the [sample openstack_controller.d/conf.yaml][2] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param name - string - required
     ## Unique identifier for this instance.
     #
     - name: "<INSTANCE_NAME>"

       ## @param user - object - required
       ## Password authentication is the only auth method supported
       ## User expects username, password, and user domain id
       ## `user` should resolve to a structure like
       ## {'password': '<PASSWORD>', 'name': '<USER_NAME>', 'domain': {'id': '<DOMAIN_ID>'}}
       ## The check uses the Unscoped token method to collect information about
       ## all available projects to the user.
       #
       user:
         password: "<PASSWORD>"
         name: "<USER_NAME>"
         domain:
           id: "<DOMAIN_ID>"
   ```

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `openstack_controller` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

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

OpenStack Controller does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.openstack.org
[2]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/metadata.csv
[6]: https://docs.datadoghq.com/help
