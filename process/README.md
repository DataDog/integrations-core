# Process Check

## Overview

The process check lets you:

* Collect resource usage metrics for specific running processes on any host: CPU, memory, I/O, number of threads, etc
* Use [Process Monitors][1]: configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

## Setup
### Installation

The process check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

Unlike many checks, the process check doesn't monitor anything useful by default; you must tell it which processes you want to monitor, and how.

While there's no standard default check configuration, here's an example `process.d/conf.yaml` that monitors ssh/sshd processes. See the [sample process.d/conf.yaml][3] for all available configuration options:

```
init_config:

instances:
  - name: ssh
    search_string: ['ssh', 'sshd']

# To search for sshd processes using an exact cmdline
# - name: ssh
#   search_string: ['/usr/sbin/sshd -D']
#   exact_match: True
```

Our process check uses the psutil python package to [check processes on your machine][4]. By default this process check works on exact match and looks at the process names only. By setting `exact_match` to **False** in your yaml file, the agent looks at the command used to launch your process and recognizes every process that contains your keywords.  

You can also configure the check to find any process by exact PID (`pid`) or pidfile (`pid_file`). If you provide more than one of `search_string`, `pid`, and `pid_file`, the check uses the first option it finds in that order (e.g. it uses `search_string` over `pid_file` if you configure both).  

To have the check search for processes in a path other than `/proc`, set `procfs_path: <your_proc_path>` in `datadog.conf`, NOT in `process.yaml` (its use has been deprecated there). Set this to `/host/proc` if you're running the Agent from a Docker container (i.e. [docker-dd-agent](https://github.com/DataDog/docker-dd-agent)) and want to monitor processes running on the server hosting your containers. You DON'T need to set this to monitor processes running _in_ your containers; the [Docker check][5] monitors those.  

Some process metrics require either running the datadog collector as the same user as the monitored process or privileged access to be retrieved.
Where the former option is not desired, and to avoid running the datadog collector as `root`, the `try_sudo` option lets the process check try using `sudo` to collect this metric.
As of now, only the `open_file_descriptors` metric on Unix platforms is taking advantage of this setting.
Note: the appropriate sudoers rules have to be configured for this to work
```
dd-agent ALL=NOPASSWD: /bin/ls /proc/*/fd/
```

See the [example configuration][3] for more details on configuration options.

[Restart the Agent][6] to start sending process metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand][7] and look for `process` under the Checks section.

## Data Collected
### Metrics

**Note**: Some metrics are not available on Linux or OSX:

* Process I/O metrics aren't available on Linux or OSX since the files that the agent read (/proc//io) are only readable by the process's owner. For more information, [read the Agent FAQ][8]
* `system.cpu.iowait` is not available on windows

See [metadata.csv][9] for a list of metrics provided by this check.

All metrics are per `instance` configured in process.yaml, and are tagged `process_name:<instance_name>`.

### Events
The Process check does not include any events at this time.

### Service Checks
**process.up**:

The Agent submits this service check for each instance in `process.yaml`, tagging each with `process:<name>`.

For an instance with no `thresholds` specified, the service check has a status of either CRITICAL (zero processes running) or OK (at least one process running).

For an instance with `thresholds` specified, consider this example:

```
instances:
  - name: my_worker_process
    search_string: ['/usr/local/bin/worker']
    thresholds:
      critical: [1, 7]
      warning: [3, 5]
```

The Agent submits a `process.up` tagged `process:my_worker_process` whose status is:

- CRITICAL when there are less than 1 or more than 7 worker processes
- WARNING when there are 1, 2, 6, or 7 worker processes
- OK when there are 3, 4 or 5 worker processes

## Troubleshooting
Need help? Contact [Datadog Support][10].

## Further Reading
To get a better idea of how (or why) to monitor process resource consumption with Datadog, check out our [series of blog posts][11] about it.


[1]: https://docs.datadoghq.com/monitoring/#process
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/process/datadog_checks/process/data/conf.yaml.example
[4]: https://github.com/DataDog/integrations-core/blob/master/process/datadog_checks/process/process.py#L117
[5]: https://github.com/DataDog/integrations-core/tree/master/docker_daemon
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[8]: https://docs.datadoghq.com/agent/faq/why-don-t-i-see-the-system-processes-open-file-descriptors-metric
[9]: https://github.com/DataDog/integrations-core/blob/master/process/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/process-check-monitoring/
