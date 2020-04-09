# Agent Check: Kubernetes API server metrics

## Overview

This check monitors [Kube_apiserver_metrics][1].

## Setup

### Installation

The Kube_apiserver_metrics check is included in the [Datadog Agent][2] package, so you do not need to install anything else on your server.

### Configuration

The main use case to run the kube_apiserver_metrics check is as a Cluster Level Check.
Refer to the dedicated documentation for [Cluster Level Checks][3].
You can annotate the service of your apiserver with the following:

```yaml
Annotations:
  ad.datadoghq.com/endpoints.check_names: ["kube_apiserver_metrics"]
  ad.datadoghq.com/endpoints.init_configs: [{}]
  ad.datadoghq.com/endpoints.instances:
    [{ "prometheus_url": "https://%%host%%:%%port%%/metrics", "bearer_token_auth": "true" }]
```

Then the Datadog Cluster Agent schedules the check(s) for each endpoint onto Datadog Agent(s).

You can also run the check by configuring the endpoints directly in the `kube_apiserver_metrics.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent’s configuration directory][4].
See the [sample kube_apiserver_metrics.d/conf.yaml][2] for all available configuration options.

By default the Agent running the check tries to get the service account bearer token to authenticate against the APIServer. If you are not using RBACs, set `bearer_token_auth` to `false`.

Finally, if you run the Datadog Agent on the master nodes, you can rely on [Autodiscovery][5] to schedule the check. It is automatic if you are running the official image `k8s.gcr.io/kube-apiserver`.

### Validation

[Run the Agent's status subcommand][6] and look for `kube_apiserver_metrics` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

Kube_apiserver_metrics does not include any service checks.

### Events

Kube_apiserver_metrics does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://kubernetes.io/docs/reference/command-line-tools-reference/kube-apiserver
[2]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kube_apiserver_metrics/metadata.csv
[8]: https://docs.datadoghq.com/help
