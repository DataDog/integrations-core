# Kubelet Integration

## Overview

This integration gets container metrics from kubelet

- Visualize and monitor kubelet stats
- Be notified about kubelet failovers and events.

## Setup

### Installation

The Kubelet check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `kubelet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2], to point to your server and port, set tags to send along with metrics.

### Validation

[Run the Agent's `status` subcommand][3] and look for `kubelet` under the Checks section.

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

If you cannot open the port, you can disable both sources of container metric collection, by setting:

- `cadvisor_port` to `0`
- `metrics_endpoint` to `""`

The check will still be able to collect:

- kubelet health service checks
- pod running/stopped metrics
- pod limits and requests
- node capacity metrics

## Data Collected

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

### Excluded containers

You can restrict the data collected to a subset of the containers
deployed by setting the [`DD_CONTAINER_EXCLUDE` environment
variable][7]. This integration does not report metrics from the containers
specified in that environment variable.

For network metrics reported at the pod level, excluding containers based on
"name" or "image name" will not work since other containers can be part of the
same pod. So, if `DD_CONTAINER_EXCLUDE` applies to a namespace, the pod-level
metrics will not be reported if the pod is in that namespace. However, if
`DD_CONTAINER_EXCLUDE` refers to a container name or an image name, the
pod-level metrics will be reported even if the exclusion rules defined apply to
some containers included in the pod.


## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.openshift.org/3.7/install_config/master_node_configuration.html#node-configuration-files
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-core/blob/master/kubelet/assets/service_checks.json
[7]: https://docs.datadoghq.com/agent/guide/autodiscovery-management/?tab=containerizedagent
