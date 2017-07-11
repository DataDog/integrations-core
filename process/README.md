# Process Check

# Overview

The process check lets you:

* Collect resource usage metrics for specific running processes on any host: CPU, memory, I/O, number of threads, etc
* Use [Process Monitors](http://docs.datadoghq.com/monitoring/#process): configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

# Installation

The process check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere you want to use the check. If you need the newest version of the check, install the `dd-check-process` package.

# Configuration

Unlike many checks, the process check doesn't monitor anything useful by default; you must tell it which processes you want to monitor, and how.

While there's no standard default check configuration, here's an example `process.yaml` that monitors ssh/sshd processes:

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

See the [example configuration](https://github.com/DataDog/integrations-core/blob/master/process/conf.yaml.example) for more details on configuration options.

Restart the Agent to start sending process metrics and service checks to Datadog.

# Validation

Run the Agent's `info` subcommand and look for process` under the Checks section:

```
  Checks
  ======
    [...]

    mcache
    -------
      - instance #0 [OK]
      - instance #1 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

Each instance configured in `process.yaml` should have one `instance #<num> [OK]` line in the output, regardless of how many search_strings it might be configured with.

# Compatibility

The process check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/process/metadata.csv) for a list of metrics provided by this check.

All metrics are per `instance` configured in process.yaml, and are tagged `process_name:<instance_name>`.

# Service Checks

**process.up**:

The Agent submits this service check for each instance in `process.yaml`, tagging each with `process:<name>`.

For an instance with no `thresholds` specified, the service check has a status of either CRITICAL (zero processes running) or OK (at least one process running).

For an instance with `threshold` specified, consider these configured thresholds:

```
instances:
  - name: my_worker_process
    search_string: ['/usr/local/bin/worker']
    thresholds:
      critical: [1, 7]
      warning: [3, 5]
```

The Agent submits a `process.up` tagged `process:my_worker_process` whose status will be:

- CRITICAL when there are less than 1 or more than 7 worker processes
- WARNING when there are 1, 2, 6, or 7 worker processes
- OK when there are 3, 4 or 5 worker processes
