# NTP check

## Overview

The Network Time Protocol (NTP) integration is enabled by default and reports the time offset from an ntp server every 15 minutes. When the local agent's time is more than 15 seconds off from the Datadog service and the other hosts that you are monitoring, you may experience:

* Incorrect alert triggers
* Metric delays
* Gaps in graphs of metrics

Default NTP servers reached:

* `0.datadog.pool.ntp.org`
* `1.datadog.pool.ntp.org`
* `2.datadog.pool.ntp.org`
* `3.datadog.pool.ntp.org`

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying these instructions.

### Installation

The NTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

The Agent enables the NTP check by default, but if you want to configure the check yourself, edit the file `ntp.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample ntp.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  - offset_threshold: 60 # seconds difference between local clock and NTP server when ntp.in_sync service check becomes CRITICAL; default is 60
#   host: pool.ntp.org # set to use an NTP server of your choosing
#   port: 1234         # set along with host
#   version: 3         # to use a specific NTP version
#   timeout: 5         # seconds to wait for a response from the NTP server; default is 1
#   use_local_defined_servers: false # Use the NTP servers defined in the localhost; default is false
```

Configuration Options:

* `host` (Optional) - Host name of alternate ntp server, for example `pool.ntp.org`
* `port` (Optional) - What port to use
* `version` (Optional) - ntp version
* `timeout` (Optional) - Response timeout
* `use_local_defined_servers` (Optional) - True to use NTP servers defined in the localhost. For Unix system, the servers defined in /etc/ntp.conf and etc/xntp.conf are used. For Windows system, the servers defined in registry key HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Parameters\NtpServer are used. **Caveat**: Enabling this option will make the NTP check unable to detect issues if the clock of the target NTP server of the system is skewed

[Restart the Agent][4] to effect any configuration changes.

### Validation

[Run the Agent's `status` subcommand][5] and look for `ntp` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The NTP check does not include any events.

### Service Checks

`ntp.in_sync`:

Returns CRITICAL if the NTP offset is greater than the threshold specified in `ntp.yaml`, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/ntp/datadog_checks/ntp/data/conf.yaml.default
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ntp/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://docs.datadoghq.com/agent/autodiscovery/integrations
