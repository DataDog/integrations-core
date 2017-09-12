# Mesos_slave Integration

## Overview

This Agent check collects metrics from Mesos slaves for:

* System load
* Number of tasks failed, finished, staged, running, etc
* Number of executors running, terminated, etc

And many more.

This check also creates a service check for every executor task.

## Setup
### Installation

Follow the instructions in our [blog post](https://www.datadoghq.com/blog/deploy-datadog-dcos/) to install the Datadog Agent on each Mesos agent node via the DC/OS web UI.

### Configuration

Unless you want to configure a custom `mesos_slave.yaml`—perhaps you need to set `disable_ssl_validation: true`—you don't need to do anything after installing the Agent.

### Validation

In the Datadog app, search for `mesos.slave` in the Metrics Explorer.

## Compatibility

The mesos_slave check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mesos_slave/metadata.csv) for a list of metrics provided by this check.

### Events
The Mesos-slave check does not include any event at this time.

### Service Check

`mesos_slave.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Mesos slave metrics endpoint, otherwise OK.

`<executor_task_name>.ok`:

The mesos_slave check creates a service check for each executor task, giving it one of the following statuses:

|||
|---|---|
|Task status|resultant service check status
|TASK_STARTING|AgentCheck.OK
|TASK_RUNNING|AgentCheck.OK
|TASK_FINISHED|AgentCheck.OK
|TASK_FAILED|AgentCheck.CRITICAL
|TASK_KILLED|AgentCheck.WARNING
|TASK_LOST|AgentCheck.CRITICAL
|TASK_STAGING |AgentCheck.OK
|TASK_ERROR|AgentCheck.CRITICAL

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
See our blog post [Installing Datadog on Mesos with DC/OS](https://www.datadoghq.com/blog/deploy-datadog-dcos/).
