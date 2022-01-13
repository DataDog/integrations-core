# Agent Integration: journald

## Overview

Systemd-journald is a system service that collects and stores logging data. 
It creates and maintains structured, indexed journals based on logging information from a variety of sources.

## Setup

### Installation

The journald check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

Journal files, by default, are owned and readable by the systemd-journal system group. To start collecting your journal logs, you need to:

1. [Install the Agent][2] on the instance running the journal.
2. Add the `dd-agent` user to the `systemd-journal` group by running:
    ```text
     usermod -a -G systemd-journal dd-agent
    ```

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

To configure this check for an Agent running on a host:

Edit the `journald.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting logs.

#### Log collection

Collecting logs is disabled by default in the Datadog Agent, you need to enable it in the `datadog.yaml` with:

```yaml
logs_enabled: true
```

Then add this configuration block to your `journald.d/conf.yaml` file to start collecting your Logs:

```yaml
logs:
    - type: journald
      container_mode: true
```

To fill `source` and `service` attributes, the Agent collects `SYSLOG_IDENTIFIER` , `_SYSTEMD_UNIT` and `_COMM`and set them to the first non empty value. To take advantage of the integration pipelines, Datadog recommends setting the `SyslogIdentifier` parameter in the `systemd` service file directly, or in a `systemd` service override file. Their location depends on your distribution, but you can find the location of the `systemd` service file by using the command `systemctl show -p FragmentPath <unit_name>`.

**Note**: With Agent 7.17+, if `container_mode` is set to `true`, the default behavior changes for logs coming from Docker containers. The `source` attribute of your logs is automatically set to the corresponding short image name of the container instead of simply `docker`.

[Restart the Agent][1].


<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying the parameters below.

#### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][5].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "journald", "service": "<YOUR_APP_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


#### Advanced features

##### Change journal location

By default the Agent looks for the journal at the following locations:

- `/var/log/journal`
- `/run/log/journal`

If your journal is located elsewhere, add a `path` parameter with the corresponding journal path.

##### Filter journal units

It's possible to filter in and out specific units by using these parameters:

- `include_units`: Includes all units specified.
- `exclude_units`: Excludes all units specified.

Example:

```yaml
logs:
    - type: journald
      path: /var/log/journal/
      include_units:
          - docker.service
          - sshd.service
```

##### Collect container tags

Tags are critical for finding information in highly dynamic containerized environments, which is why the Agent can collect container tags in journald logs.

This works automatically when the Agent is running from the host. If you are using the containerized version of the Datadog Agent, mount your journal path and the following file:

- `/etc/machine-id`: this ensures that the Agent can query the journal that is stored on the host.

### Validation

Run the Agent's [status subcommand][6] and look for `journald` under the Logs Agent section.

## Data Collected

### Metrics

journald does not include any metrics.

### Service Checks

journald does not include any service checks.

### Events

journald does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
