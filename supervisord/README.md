# Agent Check: Supervisor

![Supervisor Event][1]

## Overview

This check monitors the uptime, status, and number of processes running under Supervisor.

## Setup

### Installation

The Supervisor check is included in the [Datadog Agent][2] package, so you don't need to install anything else on servers where Supervisor is running.

### Configuration

#### Prepare supervisord

The Agent can collect data from Supervisor via HTTP server or UNIX socket. The Agent collects the same data no matter which collection method you configure.

##### HTTP server

Add a block like this to Supervisor's main configuration file (e.g. `/etc/supervisor.conf`):

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

If Supervisor is running as root, make sure `chmod` or `chown` is set so that non-root users (i.e. dd-agent) can read the socket.

---

Reload `supervisord`.

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

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

Use the `proc_names` and/or `proc_regex` options to list processes you want the Agent to collect metrics on and create service checks for. If you don't provide either option, the Agent tracks _all_ child processes of Supervisor. If you provide both options, the Agent tracks processes from both lists (i.e. the two options are not mutually exclusive).

See the [example check configuration][4] for comprehensive descriptions of other check options.

[Restart the Agent][5] to start sending Supervisor metrics to Datadog.

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][10] for guidance on applying the parameters below.

| Parameter            | Value                                                                          |
| -------------------- | ------------------------------------------------------------------------------ |
| `<INTEGRATION_NAME>` | `supervisord`                                                                  |
| `<INIT_CONFIG>`      | blank or `{}`                                                                  |
| `<INSTANCE_CONFIG>`  | `{"host":"%%host%%", "port":"9001", "user":"<USERNAME>", "pass":"<PASSWORD>"}` |

### Validation

[Run the Agent's `status` subcommand][6] and look for `supervisord` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Supervisor check does not include any events.

### Service Checks

**supervisord.can_connect**:

Returns CRITICAL if the Agent cannot connect to the HTTP server or UNIX socket you configured, otherwise OK.

**supervisord.process.status**:

The Agent submits this service check for all child processes of supervisord (if neither `proc_names` nor `proc_regex` is configured) OR a set of child processes (those configured in `proc_names` and/or `proc_regex`), tagging each service check with `supervisord_process:<process_name>`.

This table shows the `supervisord.process.status` that results from each supervisord status:

| supervisord status | supervisord.process.status |
| ------------------ | -------------------------- |
| STOPPED            | CRITICAL                   |
| STARTING           | UNKNOWN                    |
| RUNNING            | OK                         |
| BACKOFF            | CRITICAL                   |
| STOPPING           | CRITICAL                   |
| EXITED             | CRITICAL                   |
| FATAL              | CRITICAL                   |
| UNKNOWN            | UNKNOWN                    |

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

- [Supervisor monitors your processes. Datadog monitors Supervisor.][9]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/supervisord/images/supervisorevent.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/supervisord/datadog_checks/supervisord/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/supervisord/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://www.datadoghq.com/blog/supervisor-monitors-your-processes-datadog-monitors-supervisor
[10]: https://docs.datadoghq.com/agent/kubernetes/integrations/
