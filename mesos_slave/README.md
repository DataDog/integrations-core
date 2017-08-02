# Mesos_slave Integration

## Overview

This Agent check collects metrics from Mesos slaves for:

* System load
* Number of tasks failed, finished, staged, running, etc
* Number of executors running, terminated, etc

And many more.

This check also creates a service check for every executor task.

## Installation

Follow the instructions in our [blog post](https://www.datadoghq.com/blog/deploy-datadog-dcos/) to install the Datadog Agent on each Mesos agent node via the DC/OS web UI.

## Configuration

Unless you want to configure a custom `mesos_slave.yaml`—perhaps you need to set `disable_ssl_validation: true`—you don't need to do anything after installing the Agent.

## Validation

In the Datadog app, search for `mesos.slave` in the Metrics Explorer.

## Compatibility

The mesos_slave check is compatible with all major platforms.

## Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mesos_slave/metadata.csv) for a list of metrics provided by this check.

## Service Check

`mesos_slave.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Mesos slave metrics endpoint, otherwise OK.

`<executor_task_name>.ok`:

The mesos_slave check creates a service check for each executor task, giving it one of the following statuses:

|Task status|resultant service check status
|TASK_STARTING|AgentCheck.OK
|TASK_RUNNING|AgentCheck.OK
|TASK_FINISHED|AgentCheck.OK
|TASK_FAILED|AgentCheck.CRITICAL
|TASK_KILLED|AgentCheck.WARNING
|TASK_LOST|AgentCheck.CRITICAL
|TASK_STAGING |AgentCheck.OK
|TASK_ERROR|AgentCheck.CRITICAL

## Further Reading

See our blog post [Installing Datadog on Mesos with DC/OS](https://www.datadoghq.com/blog/deploy-datadog-dcos/).
