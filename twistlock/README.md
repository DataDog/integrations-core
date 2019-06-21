# Agent Check: Twistlock

## Overview

[Twistlock][1] is a security scanner. It scans containers, hosts and packages to find vulnerabilities and compliance issues.

## Setup

### Installation

The Twistlock check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

Edit the `twistlock.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your twistlock performance data. See the [sample twistlock.d/conf.yaml][2] for all available configuration options.

If you're using Kubernetes, add the config to replication controller section of twistlock_console.yaml before deploying:

```yaml
...
apiVersion: v1
kind: ReplicationController
metadata:
  name: twistlock-console
  namespace: twistlock
spec:
  replicas: 1
  selector:
    name: twistlock-console
  template:
    metadata:
      annotations:
        ad.datadoghq.com/twistlock-console.check_name: '["twistlock"]'
        ad.datadoghq.com/twistlock-console.init_configs: '[{}]'
        ad.datadoghq.com/twistlock-console.instances: '[{"url":"http://%%host%%:8083", "username":"USERNAME", "password": "PASSWORD"}]'
        ad.datadoghq.com/twistlock-console.logs: '[{"source": "twistlock", "service": "twistlock"}]'
      name: twistlock-console
      namespace: twistlock
      labels:
        name: twistlock-console
...
```


[Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `twistlock` under the Checks section.

#### Log Collection

**Available for Agent >6.0**

##### Kubernetes

* Collecting logs is disabled by default in the Datadog Agent. Enable it in your [daemonset configuration][5]:

```
(...)
  env:
    (...)
    - name: DD_LOGS_ENABLED
        value: "true"
    - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
        value: "true"
(...)
```

* Make sure that the Docker socket is mounted to the Datadog Agent as done in [this manifest][6].

* Make sure the log section is included in the Pod annotation for the defender, where the container name can be found just below in the pod spec:

```yaml
ad.datadoghq.com/<container-name>.logs: '[{"source": "twistlock", "service": "twistlock"}]'
```

* [Restart the Agent][3] to begin sending Twistlock logs to Datadog.

##### Docker

* Collecting logs is disabled by default in the Datadog Agent. Enable it by adding those two environment variables:

```
DD_LOGS_ENABLED=true
```

* Add a label on the defender container:

```yaml
ad.datadoghq.com/<container-name>.logs: '[{"source": "twistlock", "service": "twistlock"}]'
```

* Make sure that the Docker socket is mounted to the Datadog Agent. More information about the required configuration to collect logs with the Datadog Agent available in the [Docker documentation][7]

* [Restart the Agent][3] to begin sending Twistlock logs to Datadog.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

Twistlock sends service checks when a scan fails.

### Events

Twistlock sends an event when a new CVE is found.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.twistlock.com
[2]: https://github.com/DataDog/integrations-core/blob/master/twistlock/datadog_checks/twistlock/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#log-collection
[6]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#create-manifest
[7]: https://docs.datadoghq.com/logs/log_collection/docker/?tab=containerinstallation
[8]: https://github.com/DataDog/integrations-core/blob/master/twistlock/metadata.csv
[9]: https://docs.datadoghq.com/help
