# Agent Check: SSH/SFTP

## Overview

This check lets you monitor SSH connectivity to remote hosts and SFTP response times.

## Setup
### Installation

The SSH/SFTP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server from which you'd like to test SSH connectivity.

### Configuration

1. Edit the `ssh_check.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][7].
    See the [sample ssh_check.d/conf.yaml][2] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - host: <SOME_REMOTE_HOST>  # required
            username: <SOME_USERNAME> # required
            password: <SOME_PASSWORD> # or use private_key_file
        #   private_key_file: <PATH_TO_PRIVATE_KEY>
        #   private_key_type:         # rsa or ecdsa; default is rsa
        #   port: 22                  # default is port 22
        #   sftp_check: False         # set False to disable SFTP check; default is True
        #   add_missing_keys: True    # default is False
    ```

2. [Restart the Agent][3] to start sending SSH/SFTP metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `ssh_check` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The SSH Check does not include any events at this time.

### Service Checks

**ssh.can_connect**:

Returns CRITICAL if the Agent cannot open an SSH session, otherwise OK.

**sftp.can_connect**:

Returns CRITICAL if the Agent cannot open an SFTP session, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/datadog_checks/ssh_check/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/ssh_check/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
