# Agent Check: SSH/SFTP

## Overview

This check lets you monitor SSH connectivity to remote hosts and SFTP response times.

## Setup
### Installation

The SSH/SFTP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) anywhere from which you'd like to test SSH connectivity. If you need the newest version of the check, install the `dd-check-ssh-check` package.

### Configuration

Create a file `ssh_check.yaml` in the Agent's `conf.d` directory:

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

Restart the Agent to start sending SSH/SFTP metrics and service checks to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `ssh_check` under the Checks section:

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

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)