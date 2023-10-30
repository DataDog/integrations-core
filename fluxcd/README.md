# Agent Check: fluxcd

## Overview
[Flux](https://fluxcd.io/) is a set of continuous and progressive delivery solutions for Kubernetes that are open and extensible.
This check monitors fluxcd through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

To install the fluxcd check on your host:


1. Install the [developer toolkit][10]
 on any machine.

2. Run `ddev release build fluxcd` to build the package.

3. [Download the Datadog Agent][2].

4. Upload the build artifact to any host with an Agent and
 run `datadog-agent integration install -w
 path/to/fluxcd/dist/<ARTIFACT_NAME>.whl`.

### Configuration

1. Edit the `fluxcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your fluxcd performance data. See the [sample fluxcd.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `fluxcd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The fluxcd integration does not include any events.

### Service Checks

The fluxcd integration does not include any service checks.


## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://fluxcd.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-extras/blob/master/fluxcd/datadog_checks/fluxcd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-extras/blob/master/fluxcd/metadata.csv
[8]: https://github.com/DataDog/integrations-extras/blob/master/fluxcd/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/developers/integrations/python/
