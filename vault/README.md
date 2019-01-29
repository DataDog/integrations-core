# Agent Check: Vault
## Overview

This check monitors [Vault][1] cluster health and leader changes.

## Setup

### Installation

The Vault check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your server.

### Configuration

1. Edit the `vault.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your vault performance data.
  See the [sample vault.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `vault` under the Checks section.

## Data Collected
### Metrics

The Vault check does not include any metrics.

### Events

`vault.leader_change`:

This event will fire when the cluster leader changes.

### Service Checks

`vault.can_connect`:

Returns CRITICAL if the Agent cannot connect to Vault, otherwise OK.

`vault.unsealed`:

Returns CRITICAL if Vault is sealed, otherwise OK.

`vault.initialized`:

Returns CRITICAL if Vault is not yet initialized, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.vaultproject.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/vault/datadog_checks/vault/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help
