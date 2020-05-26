# Agent Check: SSH/SFTP

## Overview

This check lets you monitor SSH connectivity to remote hosts and SFTP response times.

## Setup

### Installation

The SSH/SFTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server from which you'd like to test SSH connectivity.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

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

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.

| Parameter            | Value                                                        |
| -------------------- | ------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `ssh`                                                        |
| `<INIT_CONFIG>`      | blank or `{}`                                                |
| `<INSTANCE_CONFIG>`  | `{"host": "%%host%%", "port":"22", "username":"<USERNAME>"}` |

### Validation

[Run the Agent's `status` subcommand][5] and look for `ssh_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The SSH Check does not include any events.

### Service Checks

**ssh.can_connect**:

Returns CRITICAL if the Agent cannot open an SSH session, otherwise OK.

**sftp.can_connect**:

Returns CRITICAL if the Agent cannot open an SFTP session, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/datadog_checks/ssh_check/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
