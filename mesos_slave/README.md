# Mesos Slave Integration

![Mesos Slave Dashboard][1]

## Overview

This Agent check collects metrics from Mesos slaves for:

- System load
- Number of tasks failed, finished, staged, running, etc
- Number of executors running, terminated, etc

And many more.

This check also creates a service check for every executor task.

## Setup

### Installation

See [Installing Datadog on Mesos with DC/OS][2] to install the Datadog Agent on each Mesos agent node with the DC/OS web UI.

### Configuration

#### DC/OS

1. In the DC/OS web UI, click on the **Universe** tab. Find the **datadog** package and click the Install button.
1. Click the **Advanced Installation** button.
1. Enter your Datadog API Key in the first field.
1. In the Instances field, enter the number of slave nodes in your cluster (You can determine the number of nodes in your cluster by clicking the Nodes tab on the left side of the DC/OS web ui).
1. Click **Review and Install** then **Install**

#### Marathon

If you are not using DC/OS, use the Marathon web UI or post to the API URL the following JSON to define the Datadog Agent. You must change `<YOUR_DATADOG_API_KEY>` with your API Key and the number of instances with the number of slave nodes on your cluster. You may also need to update the docker image used to more recent tag. You can find the latest [on Docker Hub][3]

```json
{
  "id": "/datadog-agent",
  "cmd": null,
  "cpus": 0.05,
  "mem": 256,
  "disk": 0,
  "instances": 1,
  "constraints": [
    ["hostname", "UNIQUE"],
    ["hostname", "GROUP_BY"]
  ],
  "acceptedResourceRoles": ["slave_public", "*"],
  "container": {
    "type": "DOCKER",
    "volumes": [
      {
        "containerPath": "/var/run/docker.sock",
        "hostPath": "/var/run/docker.sock",
        "mode": "RO"
      },
      { "containerPath": "/host/proc", "hostPath": "/proc", "mode": "RO" },
      {
        "containerPath": "/host/sys/fs/cgroup",
        "hostPath": "/sys/fs/cgroup",
        "mode": "RO"
      }
    ],
    "docker": {
      "image": "datadog/agent:latest",
      "network": "BRIDGE",
      "portMappings": [
        {
          "containerPort": 8125,
          "hostPort": 8125,
          "servicePort": 10000,
          "protocol": "udp",
          "labels": {}
        }
      ],
      "privileged": false,
      "parameters": [
        { "key": "name", "value": "datadog-agent" },
        { "key": "env", "value": "DD_API_KEY=<YOUR_DATADOG_API_KEY>" },
        { "key": "env", "value": "MESOS_SLAVE=true" }
      ],
      "forcePullImage": false
    }
  },
  "healthChecks": [
    {
      "protocol": "COMMAND",
      "command": { "value": "/probe.sh" },
      "gracePeriodSeconds": 300,
      "intervalSeconds": 60,
      "timeoutSeconds": 20,
      "maxConsecutiveFailures": 3
    }
  ],
  "portDefinitions": [
    { "port": 10000, "protocol": "tcp", "name": "default", "labels": {} },
    { "port": 10001, "protocol": "tcp", "labels": {} }
  ]
}
```

Unless you want to configure a custom `mesos_slave.d/conf.yaml`-perhaps you need to set `disable_ssl_validation: true`-you don't need to do anything after installing the Agent.

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `mesos_slave.d/conf.yaml` file to start collecting your Mesos logs:

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

    See the [sample mesos_slave.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

To enable logs for Kubernetes environments, see [Kubernetes Log Collection][6].

### Validation

#### DC/OS

Under the Services tab in the DC/OS web UI you should see the Datadog Agent shown. In Datadog, search for `mesos.slave` in the Metrics Explorer.

#### Marathon

If you are not using DC/OS, then datadog-agent is in the list of running applications with a healthy status. In Datadog, search for `mesos.slave` in the Metrics Explorer.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Mesos-slave check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Installing Datadog on Mesos with DC/OS][2]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mesos_slave/images/mesos_dashboard.png
[2]: https://www.datadoghq.com/blog/deploy-datadog-dcos
[3]: https://hub.docker.com/r/datadog/agent/tags
[4]: https://github.com/DataDog/integrations-core/blob/master/mesos_slave/datadog_checks/mesos_slave/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://github.com/DataDog/integrations-core/blob/master/mesos_slave/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/mesos_slave/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
