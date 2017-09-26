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
#### DC/OS

1. In the DC/OS web UI, click on the **Universe** tab. Find the **datadog** package and click the Install button.
1. Click the **Advanced Installation** button.
1. Enter your Datadog API Key in the first field.
1. In the Instances field, enter the number of slave nodes in your cluster (You can determine the number of nodes in your cluster by clicking the Nodes tab on the left side of the DC/OS web ui).
1. Click **Review and Install** then **Install**

#### Marathon

If you are not using DC/OS, then use either the Marathon web UI or post to the API URL the following JSON to define the Datadog Agent application. You will need to change the DATADOGAPIKEY with your API Key and the number of instances with the number of slave nodes on your cluster. You may also need to update the docker image used to more recent tag. You can find the latest [on Docker Hub](https://hub.docker.com/r/datadog/docker-dd-agent/tags/)

```json
{
  "id": "/datadog-agent",
  "cmd": null,
  "cpus": 0.05,
  "mem": 256,
  "disk": 0,
  "instances": 1,
  "constraints": [["hostname","UNIQUE"],["hostname","GROUP_BY"]],
  "acceptedResourceRoles": ["slave_public","*"],
  "container": {
    "type": "DOCKER",
    "volumes": [
      {"containerPath": "/var/run/docker.sock","hostPath": "/var/run/docker.sock","mode": "RO"},
      {"containerPath": "/host/proc","hostPath": "/proc","mode": "RO"},
      {"containerPath": "/host/sys/fs/cgroup","hostPath": "/sys/fs/cgroup","mode": "RO"}
    ],
    "docker": {
      "image": "datadog/docker-dd-agent:11.0.5160",
      "network": "BRIDGE",
      "portMappings": [
        {"containerPort": 8125,"hostPort": 8125,"servicePort": 10000,"protocol": "udp","labels": {}},
        {"containerPort": 9001,"hostPort": 9001,"servicePort": 10001,"protocol": "tcp","labels": {}}
      ],
      "privileged": false,
      "parameters": [
        {"key": "name","value": "dd-agent"},
        {"key": "env","value": "API_KEY=DATADOGAPIKEY"},
        {"key": "env","value": "MESOS_SLAVE=true"},
        {"key": "env","value": "SD_BACKEND=docker"}
      ],
      "forcePullImage": false
    }
  },
  "healthChecks": [
    {
      "gracePeriodSeconds": 300,
      "intervalSeconds": 60,
      "timeoutSeconds": 20,
      "maxConsecutiveFailures": 3,
      "portIndex": 1,
      "path": "/",
      "protocol": "HTTP",
      "ignoreHttp1xx": false
    }
  ],
  "portDefinitions": [
    {"port": 10000,"protocol": "tcp","name": "default","labels": {}},
    {"port": 10001,"protocol": "tcp","labels": {}}
  ]
}
```

Unless you want to configure a custom `mesos_slave.yaml`—perhaps you need to set `disable_ssl_validation: true`—you don't need to do anything after installing the Agent.

### Validation
#### DC/OS
Under the Services tab in the DC/OS web UI you should see the Datadog Agent shown. In the Datadog app, search for `mesos.slave` in the Metrics Explorer.

#### Marathon
If you are not using DC/OS, then datadog-agent will be in the list of running applications with a healthy status. In the Datadog app, search for mesos.slave in the Metrics Explorer.

## Compatibility

The mesos_slave check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/mesos_slave/metadata.csv) for a list of metrics provided by this integration.

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
