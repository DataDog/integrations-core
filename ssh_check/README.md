# Agent Check: SSH/SFTP

## Overview

This check lets you monitor SSH connectivity to remote hosts and SFTP response times.

## Setup

### Installation

The SSH/SFTP check is included in the [Datadog Agent][1] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `ssh_check.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample ssh_check.d/conf.yaml][3] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - host: "<SOME_REMOTE_HOST>" # required
       username: "<SOME_USERNAME>" # required
       password: "<SOME_PASSWORD>" # or use private_key_file
       # private_key_file: <PATH_TO_PRIVATE_KEY>
       # private_key_type:         # rsa or ecdsa; default is rsa
       # port: 22                  # default is port 22
       # sftp_check: False         # set False to disable SFTP check; default is True
       # add_missing_keys: True    # default is False
   ```

2. [Restart the Agent][4] to start sending SSH/SFTP metrics and service checks to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

| Parameter            | Value                                                        |
| -------------------- | ------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `ssh_check`                                                  |
| `<INIT_CONFIG>`      | blank or `{}`                                                |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port":"22", "username":"<USERNAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's `status` subcommand][6] and look for `ssh_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The SSH Check does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/datadog_checks/ssh_check/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
