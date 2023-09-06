# Kubelet Integration

## Overview

This integration gets container metrics from kubelet

- Visualize and monitor kubelet stats
- Be notified about kubelet failovers and events.

## Setup

### Installation

The Kubelet check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `kubelet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample kubelet.d/conf.yaml][7] for all available configuration options.

### Validation

Run the [Agent's status subcommand][3] and look for `kubelet` under the Checks section.

### Compatibility

The kubelet check can run in two modes:

- The default prometheus mode is compatible with Kubernetes version 1.7.6 or superior
- The cAdvisor mode (enabled by setting the `cadvisor_port` option) should be compatible with versions 1.3 and up. Consistent tagging and filtering requires at least version 6.2 of the Agent.

## OpenShift <3.7 support

The cAdvisor 4194 port is disabled by default on OpenShift. To enable it, you need to add
the following lines to your [node-config file][4]:

```text
kubeletArguments:
  cadvisor-port: ["4194"]
```

If you cannot open the port, disable both sources of container metric collection, by setting:

- `cadvisor_port` to `0`
- `metrics_endpoint` to `""`

The check can still collect:

- kubelet health service checks
- pod running/stopped metrics
- pod limits and requests
- node capacity metrics

## Data Collected

### Service Checks

See [service_checks.json][5] for a list of service checks provided by this integration.

### Excluded containers

To restrict the data collected to a subset of the containers deployed, set the [`DD_CONTAINER_EXCLUDE` environment variable][8]. Metrics are not included from the containers specified in that environment variable.

For network metrics reported at the pod level, containers cannot be excluded based on `name` or `image name` since other containers can be part of the same pod. So, if `DD_CONTAINER_EXCLUDE` applies to a namespace, the pod-level metrics are not reported if the pod is in that namespace. However, if `DD_CONTAINER_EXCLUDE` refers to a container name or image name, the pod-level metrics are reported even if the exclusion rules apply to some containers in the pod.

## Troubleshooting

Need help? Contact [Datadog support][6].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.openshift.org/3.7/install_config/master_node_configuration.html#node-configuration-files
[5]: https://github.com/DataDog/integrations-core/blob/master/kubelet/assets/service_checks.json
[6]: https://docs.datadoghq.com/help/
[7]: https://github.com/DataDog/integrations-core/blob/master/kubelet/datadog_checks/kubelet/data/conf.yaml.default
[8]: https://docs.datadoghq.com/agent/guide/autodiscovery-management/?tab=containerizedagent
