# Agent Check: Openstack Controller

## Overview

**Note**: This integration only applies to OpenStack v13+ (containerized OpenStack). If you are looking to collect metrics from OpenStack v12 and below (non-containerized OpenStack), use the [OpenStack integration][1].

This check monitors [OpenStack][2] from the controller node.

## Setup

### Installation

The OpenStack Controller check is included in the [Datadog Agent][3] package, so you do not need to install anything else on your server.

### Configuration

The OpenStack Controller integration is designed to collect information from all compute nodes and the servers running it. The integration should be run from a single Agent to monitor your OpenStack environment, and can be deployed on your controller node or an adjacent server that has access to the Keystone, Nova, Neutron, Ironic and Octavia endpoints.

#### Prepare OpenStack

Create a `datadog` user that is used in your `openstack_controller.d/conf.yaml` file. This user requires admin read-only permissions across your environment so that it can be run from a single node and read high level system information about all nodes and servers.

#### Agent configuration

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your OpenStack Controller performance data. See the [sample openstack_controller.d/conf.yaml][4] for all available configuration options:

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

2. [Restart the Agent][5]

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, you can enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `openstack_controller.d/conf.yaml` file to start collecting your Openstack logs:

   ```yaml
   logs:
     - type: file
       path: "<LOG_FILE_PATH>"
       source: openstack
   ```

    Change the `path` parameter value and configure them for your environment. See the [sample openstack_controller.d/conf.yaml][4] for all available configuration options.
   

### Validation

[Run the Agent's `status` subcommand][6] and look for `openstack_controller` under the Checks section.

## Metrics

### Nova

#### Limits
In Nova OpenStack, limits are a way to enforce quotas on the usage of resources by individual users or projects. Limits are enforced to ensure that resources are fairly distributed among all users and to prevent any single user or project from consuming too many resources.

| Datadog Metric      | Openstack Metric | Description                                           |
|-----------------------|----------------|-------------------------------------------------------|
| openstack.nova.limits.max_server_group_members |maxServerGroupMembers| The number of allowed members for each server group.|  
|openstack.nova.limits.max_server_groups|maxServerGroups| The number of allowed server groups for each tenant. | 
|openstack.nova.limits.max_server_meta|maxServerMeta| The number of allowed metadata items for each server. |
|openstack.nova.limits.max_total_cores|maxTotalCores| The number of allowed server cores for each tenant.   |
|openstack.nova.limits.max_total_instances|maxTotalInstances| The number of allowed servers for each tenant.   |     
|openstack.nova.limits.max_total_keypairs|maxTotalKeypairs|The number of allowed key pairs for each user.|
|openstack.nova.limits.max_total_ram_size|maxTotalRAMSize|The amount of allowed server RAM, in MiB, for each tenant.|
|openstack.nova.limits.total_cores_used|totalCoresUsed|The number of used server cores in each tenant.|
|openstack.nova.limits.total_instances_used|totalInstancesUsed|The number of servers in each tenant.|
|openstack.nova.limits.total_ram_used|totalRAMUsed|The amount of used server RAM in each tenant.|
|openstack.nova.limits.total_server_groups_used|totalServerGroupsUsed|The number of used server groups in each tenant.|
|openstack.nova.limits.max_security_group_rules|maxSecurityGroupRules|The number of allowed rules for each security group. **Available until version 2.35**
|openstack.nova.limits.max_security_groups|maxSecurityGroups|The number of allowed security groups for each tenant. **Available until version 2.35**
|openstack.nova.limits.max_total_floating_ips|maxTotalFloatingIps|The number of allowed floating IP addresses for each tenant. **Available until version 2.35**
|openstack.nova.limits.total_floating_ips_used|totalFloatingIpsUsed|The number of used floating IP addresses in each tenant. **Available until version 2.35**
|openstack.nova.limits.total_security_groups_used|totalSecurityGroupsUsed|The number of used security groups in each tenant. **Available until version 2.35**
|openstack.nova.limits.max_image_meta|maxImageMeta|The number of allowed metadata items for each image. **Available until version 2.38**
|openstack.nova.limits.max_personality|maxPersonality|The number of allowed injected files for each tenant. **Available until version 2.56**
|openstack.nova.limits.max_personality_size|maxPersonalitySize|The number of allowed bytes of content for each injected file. **Available until version 2.56**



See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

OpenStack Controller does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://docs.datadoghq.com/integrations/openstack/
[2]: https://www.openstack.org
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
