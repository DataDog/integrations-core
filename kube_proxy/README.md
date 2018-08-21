# Kube_proxy Integration

## Overview

Get metrics from kube_proxy service in real time to:

* Visualize and monitor kube_proxy states
* Be notified about kube_proxy failovers and events.

## Configuration

The integration relies on the `--metrics-bind-address` option of the kube-proxy, by default it's bound to `127.0.0.1:10249`.
Either start the agent on the host network if the kube-proxy is also on the host network (default) or start the kube-proxy with the `--metrics-bind-address=0.0.0.0:10249`

Edit the `kube_proxy.d/conf.yaml` file to point to your server and port, set the masters to monitor

Note: If you edit the namespace & metrics name, or add any other metric they are considered as custom

Please contribute to the integration if you want to add a relevant metric.

## Validation

[Run the Agent's `status` subcommand][1] and look for `kube_proxy` under the Checks section.


[1]: https://docs.datadoghq.com/agent/faq/agent-status-and-information/
