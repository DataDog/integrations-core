# Agent Check: Kube_apiserver_metrics

## Overview

This check monitors [Kube_apiserver_metrics][1].

## Setup

### Installation

The Kube_apiserver_metrics check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

The main use case to run the kube_apiserver_metrics check is as a Cluster Level Check.
Refer to the dedicated documentation for [Cluster Level Checks][3].
You can annotate the service of your apiserver with the following:
```
Annotations:       ad.datadoghq.com/endpoint.check_names: ["kube_apiserver_metrics"]
                   ad.datadoghq.com/endpoint.init_configs: [{}]
                   ad.datadoghq.com/endpoint.instances:
                     [
                       {
                         "prometheus_url": "%%host%%:%%port%%/metrics"
                       }
                     ]
```
The Datadog Cluster Agent will then schedule the check(s) for each endpoint onto Datadog Agent(s).

Disclaimer: Your apiserver(s) need to run as pods, support for other methods (systemd unit) will be added in an upcoming version of the Datadog Cluster Agent.

You can also run the check by configuring the endpoints directly in the `kube_apiserver_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your
See the [sample kube_apiserver_metrics.d/conf.yaml][2] for all available configuration options.

Finally, if you run the Datadog Agent on the master nodes, you can rely on [Autodiscovery][4] to schedule the check. It will be automatic if you are running the official image `k8s.gcr.io/kube-apiserver`.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `kube_apiserver_metrics` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

Kube_apiserver_metrics does not include any service checks.

### Events

Kube_apiserver_metrics does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/autodiscovery/clusterchecks/
[4]: https://docs.datadoghq.com/agent/autodiscovery/?tab=kubernetes
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/metadata.csv
[8]: https://docs.datadoghq.com/help/
