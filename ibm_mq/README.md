# Agent Check: IBM MQ

## Overview

This check monitors [IBM MQ][1].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][10] for guidance on applying these instructions.

### Installation

The IBM MQ check is included in the [Datadog Agent][2] package.

In order to use the IBM MQ check, you need to:

1. Make sure the [IBM MQ Client][3] is installed (unless the IBM MQ server is already installed)
2. Update your LD_LIBRARY_PATH to include the location of the libraries

For example:

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

Put the library location in an ld configuration file.

```
sudo sh -c "echo /opt/mqm/lib64 > /etc/ld.so.conf.d/mqm64.conf"
sudo sh -c "echo /opt/mqm/lib > /etc/ld.so.conf.d/mqm.conf"
```

Update the bindings.

```
sudo ldconfig
```

#### Permissions and authentication

There are a number of ways to set up permissions in IBM MQ. Depending on how your setup works, create a `datadog` user within MQ with read only permissions.

Note: "Queue Monitoring" must be enabled and set to at least "Medium". This can be done via the MQ UI or with an mqsc command:

```
> /opt/mqm/bin/runmqsc
5724-H72 (C) Copyright IBM Corp. 1994, 2018.
Starting MQSC for queue manager datadog.


ALTER QMGR MONQ(MEDIUM) MONCHL(MEDIUM)
     1 : ALTER QMGR MONQ(MEDIUM) MONCHL(MEDIUM)
AMQ8005I: IBM MQ queue manager changed.

       :
One MQSC command read.
No commands have a syntax error.
All valid MQSC commands were processed.
```


### Configuration

1. Edit the `ibm_mq.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your IBM MQ performance data.
   See the [sample ibm_mq.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Metric collection

There are a number of options to configure IBM MQ, depending on how you're using it.

- `channel`: The IBM MQ channel
- `queue_manager`: The Queue Manager named
- `host`: The host where IBM MQ is running
- `port`: The port that IBM MQ has exposed

If you are using a username and password setup, you can set the `username` and `password`. If no username is set, the Agent process owner is used (e.g. `dd-agent`).

If you're using SSL Authentication, you can setup SSL Authentication.

And finally, the check only monitors the queues you have set in the config:

```yaml
queues:
  - APP.QUEUE.1
  - ADMIN.QUEUE.1
```

#### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Next, point the config file to the proper MQ log files. You can uncomment the lines at the bottom of the MQ integration's config file, and amend them as you see fit:

    ```
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

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ibm_mq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

**ibm_mq.can_connect**:<br/>
Returns `CRITICAL` if the Agent cannot connect to the MQ server for any reason, otherwise returns `OK`.

**ibm_mq.queue_manager**:<br/>
Returns `CRITICAL` if the Agent cannot retrieve stats from the queue manager, otherwise returns `OK`.

**ibm_mq.queue**:<br/>
Returns `CRITICAL` if the Agent cannot retrieve queue stats, otherwise returns `OK`.

**ibm_mq.channel**:<br/>
Returns `CRITICAL` if the Agent cannot retrieve channel stats, otherwise returns `OK`.

**ibm_mq.channel.status**:<br/>
Return `CRITICAL` if the status is INACTIVE/STOPPED/STOPPING. Returns `OK` if the status is RUNNING. Returns `WARNING` if the status might lead to running.

### Events

IBM MQ does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading
Additional helpful documentation, links, and articles:

* [Monitor IBM MQ metrics and logs with Datadog][9]

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://developer.ibm.com/messaging/mq-downloads
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitor-ibmmq-with-datadog
[10]: https://docs.datadoghq.com/agent/autodiscovery/integrations
