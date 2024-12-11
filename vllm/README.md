# Agent Check: vLLM

## Overview

This check monitors [vLLM][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The vLLM check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `vllm.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your vllm performance data. See the [sample vllm.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `vllm` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The vLLM integration does not include any events.

### Service Checks

The vLLM integration does not include any service checks.

See [service_checks.json][7] for a list of service checks provided by this integration.

### Logs

Log collection is disabled by default in the Datadog Agent. If you are running your Agent as a container, see [container installation][10] to enable log collection. If you are running a host Agent, see [host Agent][11] instead.
In either case, make sure that the `source` value for your logs is `vllm`. This setting ensures that the built-in processing pipeline finds your logs. To set your log configuration for a container, see [log integrations][12].

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading
Additional helpful documentation, links, and articles:
- [Optimize LLM application performance with Datadog's vLLM integration][13]


[1]: https://docs.vllm.ai/en/stable/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/vllm/datadog_checks/vllm/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/vllm/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/vllm/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/containers/docker/log/?tab=containerinstallation#installation
[11]: https://docs.datadoghq.com/containers/docker/log/?tab=hostagent#installation
[12]: https://docs.datadoghq.com/containers/docker/log/?tab=dockerfile#log-integrations
[13]: https://www.datadoghq.com/blog/vllm-integration/