# Process Check

## Overview

The process check lets you:

* Collect resource usage metrics for specific running processes on any host: CPU, memory, I/O, number of threads, etc
* Use [Process Monitors](http://docs.datadoghq.com/monitoring/#process): configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

## Setup
### Installation

The process check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you want to use the check.

If you need the newest version of the Process check, install the `dd-check-process` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Unlike many checks, the process check doesn't monitor anything useful by default; you must tell it which processes you want to monitor, and how.

While there's no standard default check configuration, here's an example `process.yaml` that monitors ssh/sshd processes. See the [sample process.yaml](https://github.com/DataDog/integrations-core/blob/master/process/conf.yaml.example) for all available configuration options:

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

You can also configure the check to find any process by exact PID (`pid`) or pidfile (`pid_file`). If you provide more than one of `search_string`, `pid`, and `pid_file`, the check will the first option it finds in that order (e.g. it uses `search_string` over `pid_file` if you configure both).

To have the check search for processes in a path other than `/proc`, set `procfs_path: <your_proc_path>` in `datadog.conf`, NOT in `process.yaml` (its use has been deprecated there). Set this to `/host/proc` if you're running the Agent from a Docker container (i.e. [docker-dd-agent](https://github.com/DataDog/docker-dd-agent)) and want to monitor processes running on the server hosting your containers. You DON'T need to set this to monitor processes running _in_ your containers; the [Docker check](https://github.com/DataDog/integrations-core/tree/master/docker_daemon) monitors those.

See the [example configuration](https://github.com/DataDog/integrations-core/blob/master/process/conf.yaml.example) for more details on configuration options.

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending process metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `process` under the Checks section:

```
  Checks
  ======
    [...]

    process
    -------
      - instance #0 [OK]
      - instance #1 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

Each instance configured in `process.yaml` should have one `instance #<num> [OK]` line in the output, regardless of how many search_strings it might be configured with.

## Compatibility

The process check is compatible with all major platforms.

## Data Collected
### Metrics

**Note**: Some metrics are not available on Linux or OSX:

* Process I/O metrics aren't available on Linux or OSX since the files that the agent must read (/proc//io) are only readable by the process's owner. For more information, [read the Agent FAQ](https://docs.datadoghq.com/agent/faq/why-don-t-i-see-the-system-processes-open-file-descriptors-metric)
* `system.cpu.iowait` is not available on windows

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/process/metadata.csv) for a list of metrics provided by this check.

All metrics are per `instance` configured in process.yaml, and are tagged `process_name:<instance_name>`.

### Events
The Process check does not include any event at this time.

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
To get a better idea of how (or why) to monitor process resource consumption with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/process-check-monitoring/) about it.
