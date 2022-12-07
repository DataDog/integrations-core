# Mesos_master Check

This check collects metrics for Mesos masters. For Mesos slave metrics, see the [Mesos Slave integration][1].

![Mesos master Dashboard][2]

## Overview

This check collects metrics from Mesos masters for:

- Cluster resources
- Slaves registered, active, inactive, connected, disconnected, etc
- Number of tasks failed, finished, staged, running, etc
- Number of frameworks active, inactive, connected, and disconnected

And many more.

## Setup

### Installation

The installation is the same on Mesos with and without DC/OS. Run the datadog-agent container on each of your Mesos master nodes:

```shell
docker run -d --name datadog-agent \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -e DD_API_KEY=<YOUR_DATADOG_API_KEY> \
  -e MESOS_MASTER=true \
  -e MARATHON_URL=http://leader.mesos:8080 \
  datadog/agent:latest
```

Substitute your Datadog API key and Mesos Master's API URL into the command above.

### Configuration

If you passed the correct Master URL when starting datadog-agent, the Agent is already using a default `mesos_master.d/conf.yaml` to collect metrics from your masters. See the [sample mesos_master.d/conf.yaml][3] for all available configuration options.

Unless your masters' API uses a self-signed certificate. In that case, set `disable_ssl_validation: true` in `mesos_master.d/conf.yaml`.

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `mesos_master.d/conf.yaml` file to start collecting your Mesos logs:

    ```yaml
    logs:
      - type: file
        path: /var/log/mesos/*
        source: mesos
    ```

    Change the `path` parameter value based on your environment, or use the default docker stdout:

    ```yaml
    logs:
      - type: docker
        source: mesos
    ```

    See the [sample mesos_master.d/conf.yaml][3] for all available configuration options.

3. [Restart the Agent][4].

To enable logs for Kubernetes environments, see [Kubernetes Log Collection][5].

### Validation

In Datadog, search for `mesos.cluster` in the Metrics Explorer.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Mesos-master check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

- [Installing Datadog on Mesos with DC/OS][9]

[1]: https://docs.datadoghq.com/integrations/mesos/#mesos-slave-integration
[2]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mesos_master/images/mesos_dashboard.png
[3]: https://github.com/DataDog/integrations-core/blob/master/mesos_master/datadog_checks/mesos_master/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/log/
[6]: https://github.com/DataDog/integrations-core/blob/master/mesos_master/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/mesos_master/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/deploy-datadog-dcos
