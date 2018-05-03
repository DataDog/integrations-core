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
Run the datadog-agent container on each of your Mesos master nodes:

```
docker run -d --name datadog-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -e DD_API_KEY=<YOUR_DATADOG_API_KEY> \
  -e MESOS_MASTER=yes \
  -e MARATHON_URL=http://leader.mesos:8080 \
  datadog/agent:latest
```

Substitute your Datadog API key and Mesos Master's API URL into the command above.

### Configuration

If you passed the correct Master URL when starting datadog-agent, the Agent is already using a default `mesos_master.d/conf.yaml` to collect metrics from your masters; you don't need to configure anything else. See the [sample mesos_master.d/conf.yaml][1] for all available configuration options.

Unless your masters' API uses a self-signed certificate. In that case, set `disable_ssl_validation: true` in `mesos_master.yaml`.

### Validation

In the Datadog app, search for `mesos.cluster` in the Metrics Explorer.

## Data Collected
### Metrics

See [metadata.csv][2] for a list of metrics provided by this integration.

### Events
The Mesos-master check does not include any event at this time.

### Service Checks

`mesos_master.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Mesos Master API to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][3].

## Further Reading

* [Installing Datadog on Mesos with DC/OS][4]


[1]: https://github.com/DataDog/integrations-core/blob/master/mesos_master/conf.yaml.example
[2]: https://github.com/DataDog/integrations-core/blob/master/mesos_master/metadata.csv
[3]: http://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/deploy-datadog-dcos/
