# Agent Check: Vault

## Overview

This check monitors [Vault][1] cluster health and leader changes.

## Setup

### Installation

The Vault check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

#### Prerequisites

1. Ensure you have enabled [Prometheus metrics in the Vault configuration][3].

2. For the Vault check to work properly, you need to either enable unauthenticated access to Vault metrics (Vault 1.3.0+) or provide a Vault client token:

   **To enable unauthenticated access**, set Vault's [`unauthenticated_metrics_access`][4] configuration to `true`. This allows unauthenticated access to the `/v1/sys/metrics` endpoint.
   
     **Note**: The `/sys/metrics` endpoint requires Vault v1.1.0 or higher to collect metrics.
   
    **To use a Vault client token**, follow the example below. The example uses the JWT auth method, but you can also use other [auth methods][5]. 
    
The Vault integration requires the following capabilities:

     Content of `metrics_policy.hcl`:
   ```text
   path "sys/metrics*" {
     capabilities = ["read", "list"]
   }
   ```

      Setup policy and role:

   ```text
   $ vault policy write metrics /path/to/metrics_policy.hcl
   $ vault auth enable jwt
   $ vault write auth/jwt/config jwt_supported_algs=RS256 jwt_validation_pubkeys=@<PATH_TO_PUBLIC_PEM>
   $ vault write auth/jwt/role/datadog role_type=jwt bound_audiences=<AUDIENCE> user_claim=name token_policies=metrics
   $ vault agent -config=/path/to/agent_config.hcl
   ```

   Content of `agent_config.hcl`:
   ```
   exit_after_auth = true
   pid_file = "/tmp/agent_pid"

   auto_auth {
     method "jwt" {
       config = {
         path = "<JWT_CLAIM_PATH>"
         role = "datadog"
       }
     }

     sink "file" {
       config = {
         path = "<CLIENT_TOKEN_PATH>"
       }
     }
   }

   vault {
     address = "http://0.0.0.0:8200"
   }
   ```

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `vault.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your vault performance data. See the [sample vault.d/conf.yaml][7] for all available configuration options.

    Configuration for running the integration without token (with vault config `unauthenticated_metrics_access` set to true):

    ```yaml
    init_config:

    instances:
        ## @param api_url - string - required
        ## URL of the Vault to query.
        #
      - api_url: http://localhost:8200/v1

        ## @param no_token - boolean - optional - default: false
        ## Attempt metric collection without a token.
        #
        no_token: true
    ```

    Configuration for running the integration with a client token:

    ```yaml
    init_config:

    instances:
        ## @param api_url - string - required
        ## URL of the Vault to query.
        #
      - api_url: http://localhost:8200/v1

        ## @param client_token - string - optional
        ## Client token necessary to collect metrics.
        #
        client_token: <CLIENT_TOKEN>

        ## @param client_token_path - string - optional
        ## Path to a file containing the client token. Overrides `client_token`.
        ## The token will be re-read after every authorization error.
        #
        # client_token_path: <CLIENT_TOKEN_PATH>
    ```

2. [Restart the Agent][8].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

| Parameter            | Value                                    |
| -------------------- | ---------------------------------------- |
| `<INTEGRATION_NAME>` | `vault`                                  |
| `<INIT_CONFIG>`      | blank or `{}`                            |
| `<INSTANCE_CONFIG>`  | `{"api_url": "http://%%host%%:8200/v1"}` |

`INSTANCE_CONFIG` needs to be customized depending on your vault authentication config. See example in Host section above. 

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Configure Vault to enable audit and server logs.

   - Audit logs must be enabled by a privileged user with the appropriate policies. See [Enabling audit devices][10] for more information.

     ```shell
     vault audit enable file file_path=/vault/vault-audit.log
     ```

   - Make sure that [server logs][11] are written to file. You can configure static server logs in the [Vault systemd startup script][12].
     The following script is outputting the logs to `/var/log/vault.log`.

     ```text
     ...
     [Service]
     ...
     ExecStart=/bin/sh -c '/home/vagrant/bin/vault server -config=/home/vagrant/vault_nano/config/vault -log-level="trace" > /var/log/vault.log
     ...
     ```

3. Add this configuration block to your `vault.d/conf.yaml` file to start collecting your Vault logs:

   ```yaml
   logs:
     - type: file
       path: /vault/vault-audit.log
       source: vault
       service: "<SERVICE_NAME>"
     - type: file
       path: /var/log/vault.log
       source: vault
       service: "<SERVICE_NAME>"
   ```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

Run the [Agent's status subcommand][13] and look for `vault` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

**Note**: Version 3.4.0+ of this check uses [OpenMetrics][21] for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, set the value of `use_openmetrics` to `false` in the configuration.

### Events

`vault.leader_change`:
This event fires when the cluster leader changes.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][16].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor HashiCorp Vault with Datadog][17]
- [Monitor HashiCorp Vault metrics and logs][18]
- [Tools for HashiCorp Vault monitoring][19]
- [How to monitor HashiCorp Vault with Datadog][20]

[1]: https://www.vaultproject.io
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://www.vaultproject.io/docs/configuration/telemetry#prometheus
[4]: https://www.vaultproject.io/docs/configuration/listener/tcp#unauthenticated_metrics_access
[5]: https://www.vaultproject.io/docs/auth
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/vault/datadog_checks/vault/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#enabling-audit-devices
[11]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#vault-server-logs
[12]: https://learn.hashicorp.com/vault/operations/troubleshooting-vault#not-finding-the-server-logs
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/vault/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/vault/assets/service_checks.json
[16]: https://docs.datadoghq.com/help/
[17]: https://www.datadoghq.com/blog/monitor-hashicorp-vault-with-datadog
[18]: https://www.datadoghq.com/blog/monitor-vault-metrics-and-logs/
[19]: https://www.datadoghq.com/blog/vault-monitoring-tools
[20]: https://www.datadoghq.com/blog/vault-monitoring-with-datadog
[21]: https://docs.datadoghq.com/integrations/openmetrics/
