# Ceph Integration

![Ceph dashboard][1]

## Overview

Enable the Datadog-Ceph integration to:

- Track disk usage across storage pools
- Receive service checks in case of issues
- Monitor I/O performance metrics

## Setup

### Installation

The Ceph check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Ceph servers.

### Configuration

Edit the file `ceph.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][3].
See the [sample ceph.d/conf.yaml][4] for all available configuration options:

```yaml
init_config:

instances:
  - ceph_cmd: /path/to/your/ceph # default is /usr/bin/ceph
    use_sudo: true # only if the ceph binary needs sudo on your nodes
```

If you enabled `use_sudo`, add a line like the following to your `sudoers` file:

```text
dd-agent ALL=(ALL) NOPASSWD:/path/to/your/ceph
```

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `ceph.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your Ceph log files.

   ```yaml
   logs:
     - type: file
       path: /var/log/ceph/*.log
       source: ceph
       service: "<APPLICATION_NAME>"
   ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ceph` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

**Note**: If you are running Ceph luminous or later, the `ceph.osd.pct_used` metric is not included.

### Events

The Ceph check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Monitor Ceph: From node status to cluster-wide performance][10]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ceph/images/ceph_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/ceph/datadog_checks/ceph/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ceph/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/monitor-ceph-datadog
