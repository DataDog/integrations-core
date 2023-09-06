# Agent Check: Kubernetes API server metrics

![Kubernetes API Server dashboard][1]

## Overview

This check monitors [Kube_apiserver_metrics][2].

## Setup

### Installation

The Kube_apiserver_metrics check is included in the [Datadog Agent][3] package, so you do not need to install anything else on your server.

### Configuration

The main use case to run the kube_apiserver_metrics check is as a Cluster Level Check.
See the documentation for [Cluster Level Checks][4].
You can annotate the service of your apiserver with the following:

```yaml
annotations:
  ad.datadoghq.com/endpoints.check_names: '["kube_apiserver_metrics"]'
  ad.datadoghq.com/endpoints.init_configs: '[{}]'
  ad.datadoghq.com/endpoints.instances:
    '[{ "prometheus_url": "https://%%host%%:%%port%%/metrics", "bearer_token_auth": "true" }]'
```

Then the Datadog Cluster Agent schedules the check(s) for each endpoint onto Datadog Agent(s). 

You can also run the check by configuring the endpoints directly in the `kube_apiserver_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][5].
You must add `cluster_check: true` to your [configuration file][6] when using a static configuration file or ConfigMap to configure cluster checks. See the [sample kube_apiserver_metrics.d/conf.yaml][7] for all available configuration options.

By default the Agent running the check tries to get the service account bearer token to authenticate against the APIServer. If you are not using RBACs, set `bearer_token_auth` to `false`.

Finally, if you run the Datadog Agent on the master nodes, you can rely on [Autodiscovery][8] to schedule the check. It is automatic if you are running the official image `registry.k8s.io/kube-apiserver`.

### Validation

[Run the Agent's status subcommand][9] and look for `kube_apiserver_metrics` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Service Checks

Kube_apiserver_metrics does not include any service checks.

### Events

Kube_apiserver_metrics does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kube_apiserver_metrics/images/screenshot.png
[2]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/
[5]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[6]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/#set-up-cluster-checks
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[9]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/metadata.csv
[11]: https://docs.datadoghq.com/help/
