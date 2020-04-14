# Openstack Integration

![OpenStack default dashboard][1]

## Overview

Get metrics from OpenStack service in real time to:

- Visualize and monitor OpenStack states.
- Be notified about OpenStack failovers and events.

## Setup

<!-- xxx tabs xxx -->  
<!-- xxx tab "OpenStack v13 and Above" --> 
### Installation

OpenStack versions v13+ are covered by the OpenStack Controller check. This check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

The OpenStack Controller check is designed to collect information from all compute nodes and the servers running it. The integration should be run from a single Agent to monitor your OpenStack environment, and can be deployed on your controller node or an adjacent server that has access to the Keystone and Nova endpoints.

<div class="alert alert-warning">
In order to fully populate the Host Map, it is recommended to configure the OpenStack Controller check on each hypervisor. 
</div>

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
<!-- xxz tab xxx -->
<!-- xxx tab "OpenStack v12 and Below" xxx -->
### Installation

To capture your OpenStack metrics, [install the Agent][2] on your hosts running hypervisors.

### Configuration

#### Prepare OpenStack

Configure a Datadog role and user with your identity server:

```console
openstack role create datadog_monitoring
openstack user create datadog \
    --password my_password \
    --project my_project_name
openstack role add datadog_monitoring \
    --project my_project_name \
    --user datadog
```

Then, update your `policy.json` files to grant the needed permissions. `role:datadog_monitoring` requires access to the following operations:

**Nova**

```json
{
  "compute_extension": "aggregates",
  "compute_extension": "hypervisors",
  "compute_extension": "server_diagnostics",
  "compute_extension": "v3:os-hypervisors",
  "compute_extension": "v3:os-server-diagnostics",
  "compute_extension": "availability_zone:detail",
  "compute_extension": "v3:availability_zone:detail",
  "compute_extension": "used_limits_for_admin",
  "os_compute_api:os-aggregates:index": "rule:admin_api or role:datadog_monitoring",
  "os_compute_api:os-aggregates:show": "rule:admin_api or role:datadog_monitoring",
  "os_compute_api:os-hypervisors": "rule:admin_api or role:datadog_monitoring",
  "os_compute_api:os-server-diagnostics": "rule:admin_api or role:datadog_monitoring",
  "os_compute_api:os-used-limits": "rule:admin_api or role:datadog_monitoring"
}
```

**Neutron**

```json
{
  "get_network": "rule:admin_or_owner or rule:shared or rule:external or rule:context_is_advsvc or role:datadog_monitoring"
}
```

**Keystone**

```json
{
  "identity:get_project": "rule:admin_required or project_id:%(target.project.id)s or role:datadog_monitoring",
  "identity:list_projects": "rule:admin_required or role:datadog_monitoring"
}
```

You may need to restart your Keystone, Neutron, and Nova API services to ensure that the policy changes take.

**Note**: Installing the OpenStack integration could increase the number of VMs that Datadog monitors. For more information on how this may affect your billing, visit the Billing FAQ.

#### Agent Configuration

1. Configure the Datadog Agent to connect to your Keystone server, and specify individual projects to monitor. Edit the `openstack.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3] with the configuration below. See the [sample openstack.d/conf.yaml][4] for all available configuration options:

   ```yaml
   init_config:
     ## @param keystone_server_url - string - required
     ## Where your identity server lives.
     ## Note that the server must support Identity API v3
     #
     keystone_server_url: "https://<KEYSTONE_SERVER_ENDPOINT>:<PORT>/"

   instances:
     ## @param name - string - required
     ## Unique identifier for this instance.
     #
     - name: "<INSTANCE_NAME>"

       ## @param user - object - required
       ## User credentials
       ## Password authentication is the only auth method supported.
       ## `user` object expects the parameter `username`, `password`,
       ## and `user.domain.id`.
       ##
       ## `user` should resolve to a structure like:
       ##
       ##  {'password': '<PASSWORD>', 'name': '<USERNAME>', 'domain': {'id': '<DOMAINE_ID>'}}
       #
       user:
         password: "<PASSWORD>"
         name: datadog
         domain:
           id: "<DOMAINE_ID>"
   ```

2. [Restart the Agent][5].

### Validation

[Run the Agent's `status` subcommand][6] and look for `openstack` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The OpenStack check does not include any events.

### Service Checks

**openstack.neutron.api.up**:

Returns `CRITICAL` if the Agent is unable to query the Neutron API, `UNKNOWN` if there is an issue with the Keystone API. Returns `OK` otherwise.

**openstack.nova.api.up**:

Returns `CRITICAL` if the Agent is unable to query the Nova API, `UNKNOWN` if there is an issue with the Keystone API. Returns `OK` otherwise.

**openstack.keystone.api.up**:

Returns `CRITICAL` if the Agent is unable to query the Keystone API. Returns `OK` otherwise.

**openstack.nova.hypervisor.up**:

Returns `UNKNOWN` if the Agent is unable to get the Hypervisor state, `CRITICAL` if the Hypervisor is down. Returns `OK` otherwise.

**openstack.neutron.network.up**:

Returns `UNKNOWN` if the Agent is unable to get the Network state, `CRITICAL` if the Network is down. Returns `OK` otherwise.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

To get a better idea of how (or why) to integrate your Nova OpenStack compute module with Datadog, check out Datadog's [series of blog posts][9] about it.

See also these other Datadog blog posts:

- [Install OpenStack in two commands for dev and test][10]
- [OpenStack: host aggregates, flavors, and availability zones][11]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/openstack/images/openstack_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/openstack/datadog_checks/openstack/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/openstack/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/openstack-monitoring-nova
[10]: https://www.datadoghq.com/blog/install-openstack-in-two-commands
[11]: https://www.datadoghq.com/blog/openstack-host-aggregates-flavors-availability-zones
<!-- xxz tab xxx -->
<!-- xxz tabs xxx --> 