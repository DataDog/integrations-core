# Agent Check: Vault
## Overview

This check monitors [Vault][1] cluster health and leader changes.

## Setup
### Installation

The Vault check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `vault.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your vault performance data. See the [sample vault.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

| Parameter            | Value                                    |
|----------------------|------------------------------------------|
| `<INTEGRATION_NAME>` | `vault`                                  |
| `<INIT_CONFIG>`      | blank or `{}`                            |
| `<INSTANCE_CONFIG>`  | `{"api_url": "http://%%host%%:8200/v1"}` |

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

```
logs_enabled: true
```

2. Add this configuration block to your `vault.d/conf.yaml` file to start collecting your Vault logs:
    * Audit logs must enabled by a privileged user with the appropriate policies, [see more][11].
        ```
        $ vault audit enable file file_path=/vault/vault-audit.log
        ```
    * [Server logs][12] are not written to file by default. You can configure static server logs in the [start up script][13].
        The following script is outputting the logs to `/var/log/vault.log`
        ```
        ...
        [Service]
        ...
        ExecStart=/bin/sh -c '/home/vagrant/bin/vault server -config=/home/vagrant/vault_nano/config/vault -log-level="trace" > /var/log/vault.log
        ...
        ```
 

    ````yaml
    logs:
    - type: file
        path: /vault/vault-audit.log
        source: vault
        service: vault
    - type: file
        path: /var/log/vault.log
        source: vault
    ```

### Validation

[Run the Agent's status subcommand][7] and look for `vault` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

`vault.leader_change`:
This event fires when the cluster leader changes.

### Service Checks

`vault.can_connect`:
Returns CRITICAL if the Agent cannot connect to Vault, otherwise OK.

`vault.unsealed`:
Returns CRITICAL if Vault is sealed, otherwise OK.

`vault.initialized`:
Returns CRITICAL if Vault is not yet initialized, otherwise OK.

`vault.prometheus.health`:
Returns CRITICAL if the check cannot access the metrics endpoint. Otherwise, returns OK.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading
Additional helpful documentation, links, and articles:

* [Monitor HashiCorp Vault with Datadog][10]

[1]: https://www.vaultproject.io
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/vault/datadog_checks/vault/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/vault/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-hashicorp-vault-with-datadog
[11]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#enabling-audit-devices
[12]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#vault-server-logs
[13]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#not-finding-the-server-logs