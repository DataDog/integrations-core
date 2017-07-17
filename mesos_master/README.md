# Mesos_master Check

# Overview

This check collects metrics from Mesos masters for:

* Cluster resources
* Slaves registered, active, inactive, connected, disconnected, etc
* Number of tasks failed, finished, staged, running, etc
* Number of frameworks active, inactive, connected, and disconnected

And many more.

# Installation

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

# Configuration

If you passed the correct Master URL when starting docker-dd-agent, the Agent is already using a default `mesos_master.yaml` to collect metrics from your masters; you don't need to configure anything else.

Unless your masters' API uses a self-signed certificate. In that case, set `disable_ssl_validation: true` in `mesos_master.yaml`.

# Validation

In the Datadog app, search for `mesos.cluster` in the Metrics Explorer.

# Compatibility

The mesos_master check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mesos_master/metadata.csv) for a list of metrics provided by this check.

# Service Checks

`mesos_master.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Mesos Master API to collect metrics, otherwise OK.

# Further Reading

See our blog post [Installing Datadog on Mesos with DC/OS](https://www.datadoghq.com/blog/deploy-datadog-dcos/).
