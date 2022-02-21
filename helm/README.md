# Agent Check: Helm

## Overview

This check monitors Helm deployments through the Datadog Agent.

Helm supports multiple storage backends. In v3, Helm defaults to Kubernetes secrets and in v2, Helm defaults to ConfigMaps. This check supports both options.

## Setup

### Installation

The Helm check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

This is a cluster check. See the [cluster checks documentation][2].

### Validation

[Run the Agent's status subcommand][3] and look for `helm` under the Checks section.

## Data Collected

### Metrics

This check reports a gauge, `helm.release`, set to 1 for each release deployed
in the cluster. The metric has tags that identify the Helm release (name, app
version, chart version, revision, etc.).

See [metadata.csv][4] for a list of metrics provided by this check.

### Events

The Helm integration does not include any events.

### Service Checks

The Helm integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/helm/metadata.csv
[5]: https://docs.datadoghq.com/help/
