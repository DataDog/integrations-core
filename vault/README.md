# Agent Check: Vault

## Overview

This check monitors [Vault][1] cluster health and leader changes.

## Setup

### Installation

The Vault check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

#### Prerequisites

For Vault check to work properly, you need to a) enable unauthenticated access to vault metrics or b) provide a Vault client token.

a) Set Vault [`unauthenticated_metrics_access`][14] configuration to `true`.

This will allow unauthenticated access to the `/v1/sys/metrics` endpoint.

b) Use a Vault client token.

Below is an example using JWT auth method, but you can also use other [auth methods][15].

The capabilities needed for Vault integration to work properly are the following:

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

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `vault.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4] to start collecting your vault performance data. See the [sample vault.d/conf.yaml][5] for all available configuration options.

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

2. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

| Parameter            | Value                                    |
| -------------------- | ---------------------------------------- |
| `<INTEGRATION_NAME>` | `vault`                                  |
| `<INIT_CONFIG>`      | blank or `{}`                            |
| `<INSTANCE_CONFIG>`  | `{"api_url": "http://%%host%%:8200/v1"}` |

`INSTANCE_CONFIG` needs to be customized depending on your vault authentication config. See example in Host section above. 

#### Log Collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Configure Vault to enable audit and server logs.

   - Audit logs must be enabled by a privileged user with the appropriate policies. See [Enabling audit devices][11] for more information.

     ```shell
     vault audit enable file file_path=/vault/vault-audit.log
     ```

   - Make sure that [server logs][12] are written to file. You can configure static server logs in the [Vault systemd startup script][13].
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

- [Monitor HashiCorp Vault with Datadog][10]

[1]: https://www.vaultproject.io
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations
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
[14]: https://www.vaultproject.io/docs/configuration/listener/tcp#unauthenticated_metrics_access
[15]: https://www.vaultproject.io/docs/auth
