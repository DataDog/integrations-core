# Agent Check: IBM MQ

## Overview

This check monitors [IBM MQ][1] versions 9.1 and above.

## Setup

### Installation

The IBM MQ check is included in the [Datadog Agent][2] package.

To use the IBM MQ check, ensure that an [IBM MQ Client][3] version 9.1+ is installed (unless a compatible version of IBM MQ server is already installed on the Agent host). For example the [9.3 Redistributable client][17]. Currently, the IBM MQ check does not support connecting to an IBM MQ server on z/OS.

#### On Linux

Update your `LD_LIBRARY_PATH` to include the location of the libraries. Create this environment variable if it doesn't exist yet.
For example, if you installed the client under `/opt`:

```text
export LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib:$LD_LIBRARY_PATH
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

There are many ways to set up permissions in IBM MQ. Depending on how your setup works, create a `datadog` user within MQ with read only permissions and, optionally, `+chg` permissions. `+chg` permissions are required to collect metrics for [reset queue statistics][14] (`MQCMD_RESET_Q_STATS`). If you do not wish to collect these metrics you can disable `collect_reset_queue_metrics` on the configuration. Collecting reset queue statistics performance data will also reset the performance data.

**Note**: "Queue Monitoring" must be enabled on the MQ server and set to at least "Medium". This can be done using the MQ UI or with an `mqsc` command in the server's host:

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
   - `convert_endianness`: You need to enable this if your MQ server is running on AIX or IBM i

    If you are using a username and password setup, you can set the `username` and `password`. If no username is set, the Agent process owner (`dd-agent`) is used.

    **Note**: The check only monitors the queues you have set with the `queues` parameter

    ```yaml
    queues:
      - APP.QUEUE.1
      - ADMIN.QUEUE.1
    ```

2. [Restart the Agent][6].

##### Log collection

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

### Reset queue statistics MQRC_NOT_AUTHORIZED permission warning
If you are getting the following warning:

```
Warning: Error getting pcf queue reset metrics for SAMPLE.QUEUE.1: MQI Error. Comp: 2, Reason 2035: FAILED: MQRC_NOT_AUTHORIZED
```

This is due to the `datadog` user not having the `+chg` permission to collect reset queue metrics. To fix this, you can either give `+chg` permissions to the `datadog` user [using `setmqaut`][15] and collect queue reset metrics, or you can disable the `collect_reset_queue_metrics`:
```yaml
    collect_reset_queue_metrics: false
```

### High resource utilization
The IBM MQ check performs queries on the server, sometimes these queries can be expensive and cause a degradation on the check.

If you observe that the check is taking a long time to execute or that is consuming many resources on your host,
you can potentially reduce the scope of the check by trying the following:

* If you are using `auto_discover_queues`, try using `queue_patterns` or `queue_regex` instead to only discover certain queues. This is particularly relevant if your system creates dynamic queues.
* If you are autodiscovering queues with `queue_patterns` or `queue_regex`, try tightening the pattern or regex so it matches _less_ queues.
* Disable `auto_discover_channels` if you have too many channels.
* Disable `collect_statistics_metrics`.

### Errors in the logs
* `Unpack for type ((67108864,)) not implemented`: If you're seeing errors like this, and your MQ server is running on a IBM OS, enable `convert_endianness` and restart your Agent.

### Warnings in the logs
* `Error getting [...]: MQI Error. Comp: 2, Reason 2085: FAILED: MQRC_UNKNOWN_OBJECT_NAME`: If you're seeing messages like this, it is because the integration is trying to collect metrics from a queue that doesn't exist. This can be either due to misconfiguration or, if you're using `auto_discover_queues`,  the integration can discover a [dynamic queue][16] and then, when it tries to gather its metrics, the queue no longer exists. In this case you can mitigate the issue by providing a stricter `queue_patterns` or `queue_regex`, or just ignore the warning.  


### Other

Need help? Contact [Datadog support][12].


## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor IBM MQ metrics and logs with Datadog][13]

[1]: https://www.ibm.com/products/mq
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://www.ibm.com/docs/en/ibm-mq/9.3?topic=roadmap-mq-downloads#mq_downloads_admins__familyraclients__title__1
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
[14]: https://www.ibm.com/docs/en/ibm-mq/9.1?topic=formats-reset-queue-statistics
[15]: https://www.ibm.com/docs/en/ibm-mq/9.2?topic=reference-setmqaut-grant-revoke-authority
[16]: https://www.ibm.com/docs/en/ibm-mq/9.2?topic=queues-dynamic-model
[17]: https://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/WebSphere+MQ&release=9.3.0.0&platform=All&function=fixid&fixids=*IBM-MQC-Redist-*
