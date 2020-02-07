# Process Check

## Overview

The Process Check lets you:

- Collect resource usage metrics for specific running processes on any host: CPU, memory, I/O, number of threads, etc.
- Use [Process Monitors][1]: configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

## Setup

### Installation

The Process Check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

Unlike many checks, the Process Check doesn't monitor anything useful by default. You must configure which processes you want to monitor, and how.

1. While there's no standard default check configuration, here's an example `process.d/conf.yaml` that monitors SSH/SSHD processes. See the [sample process.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param name - string - required
     ## Used to uniquely identify your metrics
     ## as they are tagged with this name in Datadog.
     #
     - name: ssh

       ## @param search_string - list of strings - required
       ## If one of the elements in the list matches, it return the count of
       ## all the processes that match the string exactly by default.
       ## Change this behavior with the parameter `exact_match: false`.
       #
       search_string: ["ssh", "sshd"]
   ```

    Some process metrics require either running the Datadog collector as the same user as the monitored process or privileged access to be retrieved. Where the former option is not desired, and to avoid running the Datadog collector as `root`, the `try_sudo` option lets the Process Check try using `sudo` to collect this metric. As of now, only the `open_file_descriptors` metric on Unix platforms is taking advantage of this setting. Note: the appropriate sudoers rules have to be configured for this to work:

   ```text
   dd-agent ALL=NOPASSWD: /bin/ls /proc/*/fd/
   ```

2. [Restart the Agent][7].

### Validation

[Run the Agent's `status` subcommand][8] and look for `process` under the Checks section.

## Data Collected

### Metrics

**Note**: Some metrics are not available on Linux or OSX:

- Process I/O metrics are **not** available on Linux or OSX since the files that the Agent reads (`/proc//io`) are only readable by the process's owner. For more information, [read the Agent FAQ][9]
- `system.cpu.iowait` is not available on Windows.

See [metadata.csv][10] for a list of metrics provided by this check.

All metrics are per `instance` configured in process.yaml, and are tagged `process_name:<instance_name>`.

### Events

The Process Check does not include any events.

### Service Checks

**process.up**:

The Agent submits this service check for each instance in `process.yaml`, tagging each with `process:<name>`.

For an instance with no `thresholds` specified, the service check has a status of either CRITICAL (zero processes running) or OK (at least one process running).

For an instance with `thresholds` specified, consider this example:

```yaml
instances:
  - name: my_worker_process
    search_string: ["/usr/local/bin/worker"]
    thresholds:
      critical: [1, 7]
      warning: [3, 5]
```

The Agent submits a `process.up` tagged `process:my_worker_process` whose status is:

- CRITICAL when there are less than 1 or more than 7 worker processes
- WARNING when there are 1, 2, 6, or 7 worker processes
- OK when there are 3, 4, or 5 worker processes

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

To get a better idea of how (or why) to monitor process resource consumption with Datadog, check out this [series of blog posts][12] about it.

[1]: https://docs.datadoghq.com/monitoring/#process
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/process/datadog_checks/process/data/conf.yaml.example
[4]: https://github.com/DataDog/integrations-core/blob/master/process/datadog_checks/process/process.py#L117
[5]: https://github.com/DataDog/docker-dd-agent
[6]: https://github.com/DataDog/integrations-core/tree/master/docker_daemon
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://docs.datadoghq.com/agent/faq/why-don-t-i-see-the-system-processes-open-file-descriptors-metric
[10]: https://github.com/DataDog/integrations-core/blob/master/process/metadata.csv
[11]: https://docs.datadoghq.com/help
[12]: https://www.datadoghq.com/blog/process-check-monitoring
