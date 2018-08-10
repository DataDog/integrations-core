# Openstack Integration

![OpenStack default dashboard][10]

## Overview

Get metrics from OpenStack service in real time to:

* Visualize and monitor OpenStack states
* Be notified about OpenStack failovers and events.

## Setup
### Installation

To capture OpenStack metrics you need to [install the Agent][1] on your hosts running hypervisors.

**Note**: Installing the OpenStack Integration could increase the number of VMs that Datadog monitors. For more information on how this may affect your billing, please visit our Billing FAQ.

### Configuration

1. First configure a Datadog role and user with your identity server

    ```
    openstack role create datadog_monitoring
    openstack user create datadog \
        --password my_password \
        --project my_project_name
    openstack role add datadog_monitoring \
        --project my_project_name \
        --user datadog
    ```

2. Update your policy.json files to grant the needed permissions.
```role:datadog_monitoring``` requires access to the following operations:

**Nova**

```
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

```
{
    "get_network": "rule:admin_or_owner or rule:shared or rule:external or rule:context_is_advsvc or role:datadog_monitoring"
}
```

**Keystone**

```
{
    "identity:get_project": "rule:admin_required or project_id:%(target.project.id)s or role:datadog_monitoring",
    "identity:list_projects": "rule:admin_required or role:datadog_monitoring"
}
```

You may need to restart your Keystone, Neutron and Nova API services to ensure that the policy changes take.

3. Configure the Datadog Agent to connect to your Keystone server, and specify individual projects to monitor. Edit the `openstack.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][11]. See the [sample openstack.d/conf.yaml][2] for all available configuration options.

4. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `openstack` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The OpenStack check does not include any events at this time.

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

Returns `UNKNOWN` if the Agent is unable to get the Network state, `CRITICAL` if the Network is down. Returns `OK` otherwise.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading
To get a better idea of how (or why) to integrate your Nova OpenStack compute module with Datadog, check out our [series of blog posts][7] about it.

See also our blog posts:

* [Install OpenStack in two commands for dev and test][8]
* [OpenStack: host aggregates, flavors, and availability zones][9]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/openstack/datadog_checks/openstack/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/openstack/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/openstack-monitoring-nova/
[8]: https://www.datadoghq.com/blog/install-openstack-in-two-commands/
[9]: https://www.datadoghq.com/blog/openstack-host-aggregates-flavors-availability-zones/
[10]: https://raw.githubusercontent.com/DataDog/integrations-core/master/openstack/images/openstack_dashboard.png
[11]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
