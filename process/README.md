# Process Check

## Overview

The Process Check lets you:

- Collect resource usage metrics for specific running processes on any host: CPU, memory, I/O, number of threads, etc.
- Use [Process Monitors][1]: configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

## Setup

### Installation

The Process Check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

Unlike many checks, the Process Check doesn't monitor anything useful by default. You must configure which processes you want to monitor, and how.


1. While there's no standard default check configuration, here's an example `process.d/conf.yaml` that monitors SSH/SSHD processes. See the [sample process.d/conf.yaml][3] for all available configuration options:

```yaml
  init_config:

  instances:

  ## @param name - string - required
  ## Used to uniquely identify your metrics as they are tagged with this name in Datadog.
  #
        - name: ssh

  ## @param search_string - list of strings - optional
  ## If one of the elements in the list matches, it returns the count of
  ## all the processes that match the string exactly by default. Change this behavior with the
  ## parameter `exact_match: false`.
  ##
  ## Note: Exactly one of search_string, pid or pid_file must be specified per instance.
  #
          search_string:
            - ssh
            - sshd
```

    Some process metrics require either running the Datadog collector as the same user as the monitored process or privileged access to be retrieved. Where the former option is not desired, and to avoid running the Datadog collector as `root`, the `try_sudo` option lets the Process Check try using `sudo` to collect this metric. As of now, only the `open_file_descriptors` metric on Unix platforms is taking advantage of this setting. Note: the appropriate sudoers rules have to be configured for this to work:

   ```text
   dd-agent ALL=NOPASSWD: /bin/ls /proc/*/fd/
   ```

2. [Restart the Agent][4].

### Validation

Run the [Agent's status subcommand][5] and look for `process` under the Checks section.

### Metrics notes

**Note**: Some metrics are not available on Linux or OSX:

- Process I/O metrics are **not** available on Linux or OSX since the files that the Agent reads (`/proc//io`) are only readable by the process's owner. For more information, [read the Agent FAQ][6]
- `system.cpu.iowait` is not available on Windows.

All metrics are per `instance` configured in process.yaml, and are tagged `process_name:<instance_name>`.

The `system.processes.cpu.pct` metric sent by this check is only accurate for processes that live for more 
than 30 seconds. Do not expect its value to be accurate for shorter-lived processes.

For the full list of metrics, see the [Metrics section](#metrics).

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Process Check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

To get a better idea of how (or why) to monitor process resource consumption with Datadog, check out this [series of blog posts][10] about it.

[1]: https://docs.datadoghq.com/monitors/create/types/process_check/?tab=checkalert
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/process/datadog_checks/process/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/agent/faq/why-don-t-i-see-the-system-processes-open-file-descriptors-metric/
[7]: https://github.com/DataDog/integrations-core/blob/master/process/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/process/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/process-check-monitoring
