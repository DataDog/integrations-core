# Agent Check: IBM MQ

## Overview

This check monitors [IBM MQ][1].

## Setup

### Installation

The IBM MQ check is included in the [Datadog Agent][2] package.

In order to use the IBM MQ check, you need to install the [IBM MQ Client][3], unless the IBM MQ server is already installed on the box. Take note of where you installed it.

Update your LD_LIBRARY_PATH to include the location of the libraries. For example:

```
export LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH
```

*Note*: Agent 6 uses Upstart or systemd to orchestrate the datadog-agent service. Environment variables may need to be added to the service configuration files at the default locations of /etc/init/datadog-agent.conf (Upstart) or /lib/systemd/system/datadog-agent.service (systemd). See documentation on Upstart or systemd for more information on how to configure these settings.

Here's an example of the configuration that's used for systemd:

```yaml
[Unit]
Description="Datadog Agent"
After=network.target
Wants=datadog-agent-trace.service datadog-agent-process.service
StartLimitIntervalSec=10
StartLimitBurst=5

[Service]
Type=simple
PIDFile=/opt/datadog-agent/run/agent.pid
Environment="LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH"
User=dd-agent
Restart=on-failure
ExecStart=/opt/datadog-agent/bin/agent/agent run -p /opt/datadog-agent/run/agent.pid

[Install]
WantedBy=multi-user.target
```

Here's an example of the upstart config:

```
description "Datadog Agent"

start on started networking
stop on runlevel [!2345]

respawn
respawn limit 10 5
normal exit 0

# Logging to console from the Agent is disabled since the Agent already logs using file or
# syslog depending on its configuration. We make Upstart log what the process still outputs in order
# to log panics/crashes to /var/log/upstart/datadog-agent.log
console log
env DD_LOG_TO_CONSOLE=false
env LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH

setuid dd-agent

script
  exec /opt/datadog-agent/bin/agent/agent start -p /opt/datadog-agent/run/agent.pid
end script

post-stop script
  rm -f /opt/datadog-agent/run/agent.pid
end script
```

Each time there is an agent update, these files are wiped and will need to be updated again.

Alternatively, if you are using Linux, after the MQ Client is installed ensure the runtime linker can find the libraries. For example, using ldconfig:

```
# Put the library location in an ld configuration file.

sudo sh -c "echo /opt/mqm/lib64 > /etc/ld.so.conf.d/mqm64.conf"
sudo sh -c "echo /opt/mqm/lib > /etc/ld.so.conf.d/mqm.conf"

# Update the bindings.

sudo ldconfig
```

#### Permissions and Authentication

There are a number of ways to set up permissions in IBM MQ. Depending on how your setup works, create a `datadog` user within MQ with read only permissions.


### Configuration

1. Edit the `ibm_mq.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your IBM MQ performance data.
   See the [sample ibm_mq.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

#### Metric Collection

There are a number of options to configure IBM MQ, depending on how you're using it.

`channel`: The IBM MQ channel
`queue_manager`: The Queue Manager named
`host`: The host where IBM MQ is running
`port`: The port that IBM MQ has exposed

If you're using a username and password setup, you can set the username and password.

If you're using SSL Authentication, you can setup SSL Authentication.

And finally, the check only monitors the queues you have set in the config:

```yaml
queues:
  - APP.QUEUE.1
  - ADMIN.QUEUE.1
```

#### Log Collection

Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

Next, point the config file to the proper MQ log files. You can uncomment the lines at the bottom of the MQ integration's config file, and amend them as you see fit:

```yaml
logs:
  - type: file
    path: /var/mqm/log/<APPNAME>/active/AMQERR01.LOG
    service: <APPNAME>
    source: ibm_mq
    log_processing_rules:
      - type: multi_line
        name: new_log_start_with_date
        pattern: "\d{2}/\d{2}/\d{4}"
```

### Validation

[Run the Agent's `status` subcommand][6] and look for `ibm_mq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

There are three service checks:

`ibm_mq.can_connect`: checks if we can connect to IBM MQ
`ibm_mq.queue_manager`: checks if the Queue Manager is working
`ibm_mq.queue`: checks if the queue exists

### Events

IBM MQ does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://developer.ibm.com/messaging/mq-downloads/
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
