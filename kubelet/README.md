# Kubelet Integration

## Overview

This integration gets container metrics from kubelet

* Visualize and monitor kubelet stats
* Be notified about kubelet failovers and events.

## Installation

Install the `dd-check-kubelet` package manually or with your favorite configuration manager

## Configuration

Edit the `kubelet.yaml` file to point to your server and port, set tags to send along with metrics.

## Validation

[Run the Agent's `status` subcommand][1] and look for `kubelet` under the Checks section:

    Checks
    ======

        kubelet
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kubelet check can run in two modes:

- the default prometheus mode is compatible with Kubernetes version 1.7.6 or superior
- the cAdvisor mode (enabled by setting the `cadvisor_port` option) should be compatible with versions 1.3 and up. Consistent tagging and filtering requires at least version 6.2 of the Agent.

The cAdvisor 4194 port is disabled by default on OpenShift. To enable it, you need to add
the following lines to your [node-config file][2]:

```
kubeletArguments:
  cadvisor-port: ["4194"]
```


[1]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[2]: https://docs.openshift.org/3.7/install_config/master_node_configuration.html#node-configuration-files
