# Agent Check: Supervisor

![Supervisor Event][1]

## Overview

This check monitors the uptime, status, and number of processes running under Supervisor.

## Setup

### Installation

The Supervisor check is included in the [Datadog Agent][2] package, so you don't need to install anything else on servers where Supervisor is running.

### Configuration

#### Prepare supervisord

The Agent can collect data from Supervisor through a HTTP server or UNIX socket. The Agent collects the same data no matter which collection method you configure.

##### HTTP server

Add a block like this to Supervisor's main configuration file (`/etc/supervisor.conf`):

```ini
[inet_http_server]
port=localhost:9001
;username=user  # optional
;password=pass  # optional
```

##### UNIX socket

Add blocks like these to `/etc/supervisor.conf` (if they're not already there):

```ini
[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[unix_http_server]
file=/var/run/supervisor.sock
chmod=777
chown=nobody:nogroup
;username=user  # optional
;password=pass  # optional
```

If Supervisor is running as root, make sure `chmod` or `chown` is set so that non-root users, such as `dd-agent`, can read the socket.

---

Reload `supervisord`.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `supervisord.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample supervisord.d/conf.yaml][4] for all available configuration options:

```yaml
init_config:

instances:
  ## Used to tag service checks and metrics, i.e. supervisor_server:supervisord0
  - name: supervisord0
    host: localhost
    port: 9001
  ## To collect from the socket instead
  # - name: supervisord0
  #   socket: unix:///var/run/supervisor.sock
```

Use the `proc_names` and/or `proc_regex` options to list processes you want the Agent to collect metrics on and create service checks for. If you don't provide either option, the Agent tracks _all_ child processes of Supervisor. If you provide both options, the Agent tracks processes from both lists meaning the two options are not mutually exclusive.

See the [example check configuration][4] for comprehensive descriptions of other check options.

[Restart the Agent][5] to start sending Supervisor metrics to Datadog.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][6] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `supervisord`                                                                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                      |
| `<INSTANCE_CONFIG>`  | `{"name":"<SUPERVISORD_SERVER_NAME>", "host":"%%host%%", "port":"9001", "username":"<USERNAME>", "password":"<PASSWORD>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Log collection



1. Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `supervisord.d/conf.yaml` file to start collecting your Supervisord Logs:

   ```yaml
   logs:
     - type: file
       path: /path/to/my/directory/file.log
       source: supervisord
   ```

   Change the `path` parameter value and configure it for your environment.
   See the [sample supervisord.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

Run the [Agent's status subcommand][7] and look for `supervisord` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

The Supervisor check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Supervisor monitors your processes. Datadog monitors Supervisor.][11]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/supervisord/images/supervisorevent.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/supervisord/datadog_checks/supervisord/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/supervisord/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/supervisord/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/supervisor-monitors-your-processes-datadog-monitors-supervisor
