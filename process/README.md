# Process Integration

## Overview

* Capture metrics from specific running processes on a system such as CPU %, memory, and I/O.
* Monitor the status of running processes with Process Monitors (Requires Datadog Agent >= 5.1.0).

## Installation

Install the `dd-check-process` package manually or with your favorite configuration manager

## Configuration

Configure the Agent to connect to your processes. Our example configuration will monitor the ssh, sshd, and postgres processes.

1. Edit `/etc/dd-agent/conf.d/process.yaml`
```
init_config:
  # used to override the default procfs path, e.g. for docker
  # containers to see the processes of the host at /host/proc
  # procfs_path: /proc
instances:
  - name: ssh
    search_string: ['ssh', 'sshd']

  - name: postgres
    search_string: ['postgres']

  - name: pid_process
    pid: 1278 
    # Do not use search_string when searching by pid or multiple processes will be grabbed
```
2. Restart the Agent

```sudo /etc/init.d/datadog-agent restart```
Refer to the comments in the process check [conf.yaml.example](https://github.com/DataDog/integrations-core/blob/master/process/conf.yaml.example) file for more options.

After the Agent has sent data to Datadog you can visit the [New Monitor section of the application](https://app.datadoghq.com/monitors#create/process) to set up a Monitor. If you only see information on how to configure the process check in the Agent, Datadog has not yet received any process information from the Agent. Use the instructions below to validate whether the Agent has been configured correctly.

For more details about configuring this integration refer to the following file(s) on GitHub:

* [Process Check YAML example](https://github.com/DataDog/integrations-core/blob/master/process/conf.yaml.example)
* [Process Check check.py](https://github.com/DataDog/integrations-core/blob/master/process/check.py)

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        process
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The process check is compatible with all major platforms

## Further Reading

See our blog post [Inspeqtor Process Monitoring with Datadog](https://www.datadoghq.com/blog/process-monitoring-inspeqtor-datadog/)
