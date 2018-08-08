# Kubelet Integration

## Overview

This integration gets container metrics from kubelet

* Visualize and monitor kubelet stats
* Be notified about kubelet failovers and events.

## Installation

The Kubelet check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your servers.

## Configuration

Edit the `kubelet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to point to your server and port, set tags to send along with metrics.

## Validation

[Run the Agent's `status` subcommand][1] and look for `kubelet` under the Checks section.

## Compatibility

The kubelet check can run in two modes:

- the default prometheus mode is compatible with Kubernetes version 1.7.6 or superior
- the cAdvisor mode (enabled by setting the `cadvisor_port` option) should be compatible with versions 1.3 and up. Consistent tagging and filtering requires at least version 6.2 of the Agent.

## OpenShift <3.7 support

The cAdvisor 4194 port is disabled by default on OpenShift. To enable it, you need to add
the following lines to your [node-config file][2]:

```
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


[1]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[2]: https://docs.openshift.org/3.7/install_config/master_node_configuration.html#node-configuration-files
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
