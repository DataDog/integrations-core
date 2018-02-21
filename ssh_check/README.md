# Agent Check: SSH/SFTP

## Overview

This check lets you monitor SSH connectivity to remote hosts and SFTP response times.

## Setup
### Installation

The SSH/SFTP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere from which you'd like to test SSH connectivity.

If you need the newest version of the SSH check, install the `dd-check-ssh-check` package; this package's check overrides the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://github.com/DataDog/integrations-core#installing-the-integrations).

### Configuration

Create a file `ssh_check.yaml` in the Agent's `conf.d` directory. See the [sample ssh_check.yaml](https://github.com/DataDog/integrations-core/blob/master/ssh_check/conf.yaml.example) for all available configuration options:

```
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

[Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending SSH/SFTP metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `ssh_check` under the Checks section:

```
  Checks
  ======
    [...]

    ssh_check
    -------
      - instance #0 [OK]
      - Collected 1 metric, 0 events & 2 service check

    [...]
```

## Compatibility

The ssh check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ssh_check/metadata.csv) for a list of metrics provided by this check.

### Events
The SSH Check check does not include any event at this time.

### Service Checks

**ssh.can_connect**:

Returns CRITICAL if the Agent cannot open an SSH session, otherwise OK.

**sftp.can_connect**:

Returns CRITICAL if the Agent cannot open an SFTP session, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
