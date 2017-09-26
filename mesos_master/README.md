# Mesos_master Check

## Overview

This check collects metrics from Mesos masters for:

* Cluster resources
* Slaves registered, active, inactive, connected, disconnected, etc
* Number of tasks failed, finished, staged, running, etc
* Number of frameworks active, inactive, connected, and disconnected

And many more.
## Setup
### Installation
The installation is the same on Mesos with and without DC/OS. 
Run the docker-dd-agent container on each of your Mesos master nodes:

```
docker run -d --name dd-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -e API_KEY=<YOUR_DATADOG_API_KEY> \
  -e MESOS_MASTER=yes \
  -e MARATHON_URL=http://leader.mesos:8080 \
  -e SD_BACKEND=docker \
  datadog/docker-dd-agent:latest
```

Substitute your Datadog API key and Mesos Master's API URL into the command above.

### Configuration

If you passed the correct Master URL when starting docker-dd-agent, the Agent is already using a default `mesos_master.yaml` to collect metrics from your masters; you don't need to configure anything else.

Unless your masters' API uses a self-signed certificate. In that case, set `disable_ssl_validation: true` in `mesos_master.yaml`.

### Validation

In the Datadog app, search for `mesos.cluster` in the Metrics Explorer.

## Compatibility

The mesos_master check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mesos_master/metadata.csv) for a list of metrics provided by this integration.

### Events
The Mesos-master check does not include any event at this time.

### Service Checks

`mesos_master.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Mesos Master API to collect metrics, otherwise OK.

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
