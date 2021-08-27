# Ceph Integration

![Ceph dashboard][1]

## Overview

Enable the Datadog-Ceph integration to:

- Track disk usage across storage pools
- Receive service checks in case of issues
- Monitor I/O performance metrics

## Setup

### Installation

The Ceph check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Ceph servers.

### Configuration

Edit the file `ceph.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][4].
See the [sample ceph.d/conf.yaml][5] for all available configuration options:

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

{{< site-region region="us3" >}}
**Log collection is not supported for this site.**
{{< /site-region >}}

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

3. [Restart the Agent][10].

### Validation

[Run the Agent's status subcommand][6] and look for `ceph` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

**Note**: If you are running ceph luminous or later, you will not see the metric `ceph.osd.pct_used`.

### Events

The Ceph check does not include any events.

### Service Checks

See [service_checks.json][11] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

- [Monitor Ceph: From node status to cluster-wide performance][9]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ceph/images/ceph_dashboard.png
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/ceph/datadog_checks/ceph/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/monitor-ceph-datadog
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[11]: https://github.com/DataDog/integrations-core/blob/master/ceph/assets/service_checks.json
