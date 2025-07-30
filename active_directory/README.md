# Active Directory Integration

## Overview

Get metrics from Microsoft Active Directory to visualize and monitor its performances.

## Setup

### Installation

The Agent's Active Directory check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

If installing the Datadog Agent on a domain environment, see [the installation requirements for the Agent][2]

### Configuration

#### Metric collection

1. Edit the `active_directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Active Directory performance data. The default setup should already collect metrics for the localhost. See the [sample active_directory.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

**Note**: Versions 1.13.0 or later of this check use a new implementation for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][10].

### Validation

[Run the Agent's status subcommand][7] and look for `active_directory` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

The integration collects metrics from the following Windows Performance Objects:

- **NTDS**: Core Active Directory metrics including replication, LDAP operations, and directory service threads ([Microsoft Learn][11])
  - LDAP metrics include `ldap.writes_persec` (tracks directory modifications) and `ldap.active_threads` (monitors LDAP subsystem load)
  - Directory service metrics include `ds.client_binds_persec` (all bind attempts including successful and failed)
- **Netlogon**: Authentication performance metrics including semaphore statistics for monitoring authentication bottlenecks ([MaxConcurrentApi tuning][12])
- **Security System-Wide Statistics**: Authentication protocol usage metrics (NTLM vs Kerberos) ([Authentication monitoring][13])
- **DHCP Server**: DHCP failover and binding update metrics (when DHCP Server role is installed) ([DHCP Failover Events][14])
- **DFS Replicated Folders**: DFS replication health, conflicts, and staging metrics (when DFSR role is installed) ([DFSR Performance Objects][15])
  - Note: Metrics are tagged with `replication_group` containing the DFS replication group name

#### Netlogon Metrics

The Netlogon metrics help monitor authentication performance and identify bottlenecks in domain controller authentication processing:

- `active_directory.netlogon.semaphore_waiters`: Number of threads waiting for the authentication semaphore
- `active_directory.netlogon.semaphore_holders`: Number of threads currently holding the semaphore
- `active_directory.netlogon.semaphore_acquires`: Total number of semaphore acquisitions
- `active_directory.netlogon.semaphore_timeouts`: Number of timeouts waiting for the semaphore
- `active_directory.netlogon.semaphore_hold_time`: Average time (in seconds) the semaphore is held
- `active_directory.netlogon.last_authentication_time`: Time since last authentication

These metrics are particularly useful for monitoring authentication load from network access control (NAC) devices, WiFi authentication, and other authentication-heavy scenarios.

#### Service-Aware Metric Collection

The integration automatically detects which Windows services are running and only collects metrics for available services. This prevents errors when optional roles like DHCP Server or DFS Replication are not installed. You can control this behavior with:

- `service_check_enabled`: Enable/disable service detection (default: true)
- `force_all_metrics`: Force collection of all metrics regardless of service state (default: false)
- `emit_service_status`: Emit service checks for monitoring service availability (default: false)

### Events

The Active Directory check does not include any events.

### Service Checks

The Active Directory check does not include any service checks.

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
[10]: https://github.com/DataDog/integrations-core/blob/7.33.x/active_directory/datadog_checks/active_directory/data/conf.yaml.example
[11]: https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/ldap-client-performance-counters
[12]: https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/performance-tuning-ntlm-authentication-maxconcurrentapi
[13]: https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/ldap-client-performance-counters
[14]: https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/dn338988(v=ws.11)
[15]: https://social.technet.microsoft.com/wiki/contents/articles/414.dfsr-performance-objects-their-counters-corresponding-wmi-classes-and-using-wmic-or-vbscript-to-view-them.aspx
[16]: https://learn.microsoft.com/en-us/windows-server/administration/performance-tuning/role/active-directory-server/capacity-planning-for-active-directory-domain-services
[17]: https://learn.microsoft.com/en-us/windows-server/administration/performance-tuning/role/active-directory-server/
