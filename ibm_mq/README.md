# Agent Check: IBM MQ

## Overview

This check monitors [IBM MQ][1] versions 8 to 9.0.

## Setup

### Installation

The IBM MQ check is included in the [Datadog Agent][2] package.

To use the IBM MQ check, you need to make sure the [IBM MQ Client][3] 9.1+ is installed (unless a compatible version of IBM MQ server is installed on the Agent host).
   
#### On Linux

Update your `LD_LIBRARY_PATH` and `C_INCLUDE_PATH` to include the location of the libraries. (Create these two environment variables if they don’t exist yet.)
For example, if you installed it in `/opt`:

```text
export LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=/opt/mqm/inc:$C_INCLUDE_PATH
```

**Note**: Agent v6+ uses `upstart`, `systemd` or `launchd` to orchestrate the datadog-agent service. Environment variables may need to be added to the service configuration files at the default locations of:

- Upstart (Linux): `/etc/init/datadog-agent.conf`
- Systemd (Linux): `/lib/systemd/system/datadog-agent.service`
- Launchd (MacOS): `~/Library/LaunchAgents/com.datadoghq.agent.plist`
  - This only works if MacOS SIP is disabled (might not be recommended depending on your security policy). This is due to [SIP purging `LD_LIBRARY_PATH` environ variable][4].

Example of the configuration for `systemd`:

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

Example of the configuration for `upstart`:

```conf
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

Example of the configuration for `launchd`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>KeepAlive</key>
        <dict>
            <key>SuccessfulExit</key>
            <false/>
        </dict>
        <key>Label</key>
        <string>com.datadoghq.agent</string>
        <key>EnvironmentVariables</key>
        <dict>
            <key>DD_LOG_TO_CONSOLE</key>
            <string>false</string>
            <key>LD_LIBRARY_PATH</key>
            <string>/opt/mqm/lib64:/opt/mqm/lib</string>
        </dict>
        <key>ProgramArguments</key>
        <array>
            <string>/opt/datadog-agent/bin/agent/agent</string>
            <string>run</string>
        </array>
        <key>StandardOutPath</key>
        <string>/var/log/datadog/launchd.log</string>
        <key>StandardErrorPath</key>
        <string>/var/log/datadog/launchd.log</string>
        <key>ExitTimeOut</key>
        <integer>10</integer>
    </dict>
</plist>
```

Each time there is an Agent update, these files are wiped and need to be updated again.

Alternatively, if you are using Linux, after the MQ Client is installed ensure the runtime linker can find the libraries. For example, using ldconfig:

Put the library location in an ld configuration file.

```shell
sudo sh -c "echo /opt/mqm/lib64 > /etc/ld.so.conf.d/mqm64.conf"
sudo sh -c "echo /opt/mqm/lib > /etc/ld.so.conf.d/mqm.conf"
```

Update the bindings:

```shell
sudo ldconfig
```

#### On Windows

There is a file called `mqclient.ini` in the IBM MQ data directory. It is normally `C:\ProgramData\IBM\MQ`.
Configure the environment variable `MQ_FILE_PATH`, to point at the data directory.

### Permissions and authentication

There are many ways to set up permissions in IBM MQ. Depending on how your setup works, create a `datadog` user within MQ with read only permissions.

**Note**: "Queue Monitoring" must be enabled and set to at least "Medium". This can be done using the MQ UI or with an mqsc command:

```text
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

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `ibm_mq.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your IBM MQ performance data. See the [sample ibm_mq.d/conf.yaml][5] for all available configuration options.
   There are many options to configure IBM MQ, depending on how you're using it.

   - `channel`: The IBM MQ channel
   - `queue_manager`: The Queue Manager named
   - `host`: The host where IBM MQ is running
   - `port`: The port that IBM MQ has exposed

    If you are using a username and password setup, you can set the `username` and `password`. If no username is set, the Agent process owner (`dd-agent`) is used.

    **Note**: The check only monitors the queues you have set with the `queues` parameter

    ```yaml
    queues:
      - APP.QUEUE.1
      - ADMIN.QUEUE.1
    ```

2. [Restart the Agent][6].

##### Log collection

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for the Datadog {{< region-param key="dd_site_name" >}} site**.
{{< /site-region >}}
partial -->

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, point the config file to the proper MQ log files. You can uncomment the lines at the bottom of the MQ integration's config file, and amend them as you see fit:

   ```yaml
     logs:
       - type: file
         path: '/var/mqm/log/<APPNAME>/active/AMQERR01.LOG'
         service: '<APPNAME>'
         source: ibm_mq
         log_processing_rules:
           - type: multi_line
             name: new_log_start_with_date
             pattern: "\d{2}/\d{2}/\d{4}"
   ```

3. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `ibm_mq`                                                                                                                        |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                                   |
| `<INSTANCE_CONFIG>`  | `{"channel": "DEV.ADMIN.SVRCONN", "queue_manager": "datadog", "host":"%%host%%", "port":"%%port%%", "queues":["<QUEUE_NAME>"]}` |

##### Log collection

<!-- partial
{{< site-region region="us3" >}}
**Log collection is not supported for the Datadog {{< region-param key="dd_site_name" >}} site**.
{{< /site-region >}}
partial -->

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][8].

| Parameter      | Value                                                                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "ibm_mq", "service": "<SERVICE_NAME>", "log_processing_rules": {"type":"multi_line","name":"new_log_start_with_date", "pattern":"\d{2}/\d{2}/\d{4}"}}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][9] and look for `ibm_mq` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

IBM MQ does not include any events.

### Service Checks

See [service_checks.json][11] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][12].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor IBM MQ metrics and logs with Datadog][13]

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://developer.ibm.com/messaging/mq-downloads
[4]: https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html#//apple_ref/doc/uid/TP40016462-CH3-SW1
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/metadata.csv
[11]: https://github.com/DataDog/integrations-core/blob/master/ibm_mq/assets/service_checks.json
[12]: https://docs.datadoghq.com/help/
[13]: https://www.datadoghq.com/blog/monitor-ibmmq-with-datadog
