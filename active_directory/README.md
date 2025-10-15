# Active Directory Integration

## Overview

Get metrics from Microsoft Active Directory to visualize and monitor its performances.

**Minimum Agent version:** 6.0.0

## Setup

### Installation

The Agent's Active Directory check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

If installing the Datadog Agent on a domain environment, see [the installation requirements for the Agent][2]

### Configuration

#### Metric collection

1. Edit the `active_directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Active Directory performance data. The default setup should already collect metrics for the localhost. See the [sample active_directory.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

**Note**: Use version 4.4.0 or later of this check to collect the latest metrics.

#### Service checks
Datadog recommends enabling the [Windows Services][10] integration to also monitor the state of the Active Directory services.

Example configuration:
```yaml
instances:
  - services:
    - ntds
    - netlogon
    - dhcp
    - dfsr
    - adws
    - kdc
```

**Note:** The Datadog Agent might not have access to all the services (e.g. NTDS). See [Service permissions][11] for more information to grant access.

### Validation

[Run the Agent's status subcommand][7] and look for `active_directory` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

The integration collects metrics from the following Windows performance objects:

- **NTDS**: Core Active Directory metrics including replication, LDAP operations, and directory service threads
- **Netlogon**: Authentication performance metrics including semaphore statistics for monitoring authentication bottlenecks
- **Security System-Wide Statistics**: Authentication protocol usage metrics (NTLM vs Kerberos)
- **DHCP Server**: DHCP failover and binding update metrics (when DHCP Server role is installed)
- **DFS Replicated Folders**: DFS replication health, conflicts, and staging metrics (when DFSR role is installed)
  - Note: Metrics are tagged with `instance` containing the DFS replication group name

#### Netlogon Metrics

The Netlogon metrics help monitor authentication performance and identify bottlenecks in domain controller authentication processing:

- `active_directory.netlogon.semaphore_waiters`: Number of threads waiting for the authentication semaphore
- `active_directory.netlogon.semaphore_holders`: Number of threads currently holding the semaphore
- `active_directory.netlogon.semaphore_acquires`: Total number of semaphore acquisitions
- `active_directory.netlogon.semaphore_timeouts`: Number of timeouts waiting for the semaphore
- `active_directory.netlogon.semaphore_hold_time`: Average time (in seconds) the semaphore is held

These metrics are particularly useful for monitoring authentication load from network access control (NAC) devices, Wi-Fi authentication, and other authentication-heavy scenarios.

##### Use Cases

The Netlogon and Security metrics help address several monitoring scenarios:

- **Monitor authentication bottlenecks**: Identify when authentication requests are queuing up, particularly from Cisco ISE NAC devices or high-volume Wi-Fi authentication
- **Track authentication processing times**: Use `semaphore_hold_time` to determine if authentication is taking too long
- **Identify MaxConcurrentApi tuning needs**: High `semaphore_waiters` values indicate the need to adjust the MaxConcurrentApi registry setting
- **Monitor authentication protocol usage**: Track the ratio of NTLM vs Kerberos authentications to ensure proper protocol usage
- **Detect authentication timeouts and failures**: Rising `semaphore_timeouts` indicate authentication infrastructure issues

### Events

The Active Directory check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: /account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/faq/windows-agent-ddagent-user/#installation-in-a-domain-environment
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/active_directory/datadog_checks/active_directory/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/integrations/windows-service/
[11]: https://docs.datadoghq.com/integrations/windows-service/#service-permissions