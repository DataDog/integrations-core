# Marathon Integration

## Overview

The Agent's Marathon check lets you:

* Track the state and health of every application: see configured memory, disk, cpu, and instances; monitor the number of healthy and unhealthy tasks
* Monitor the number of queued applications and the number of deployments

## Setup
### Installation

The Marathon check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Marathon master.

### Configuration

1. Edit the `marathon.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2].
    See the [sample marathon.d/conf.yaml][3] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - url: https://<server>:<port> # the API endpoint of your Marathon master; required
        #   acs_url: https://<server>:<port> # if your Marathon master requires ACS auth
            user: <username> # the user for marathon API or ACS token authentication
            password: <password> # the password for marathon API or ACS token authentication
    ```

    The function of `user` and `password` depends on whether or not you configure `acs_url`; If you do, the Agent uses them to request an authentication token from ACS, which it then uses to authenticate to the Marathon API. Otherwise, the Agent uses `user` and `password` to directly authenticate to the Marathon API.

2. [Restart the Agent][4] to begin sending Marathon metrics to Datadog.

#### Log Collection

 **Available for Agent >6.0**

 1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

     ```yaml
    logs_enabled: true
    ```

 2. Because Marathon uses logback, you can specify a custom log format. With Datadog, two formats are supported out of the box, the default one provided by Marathon, and the Datadog recommended format. Add a fileappender to your configuration as in the following example and replace `$PATTERN$` with either `[%date] %-5level %message \(%logger:%thread\)%n` for Marathon default format or `%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n` for Datadog recommended format.

    ```xml
    <?xml version="1.0" encoding="UTF-8"?>

    <configuration>
        <shutdownHook class="ch.qos.logback.core.hook.DelayingShutdownHook"/>
        <appender name="stdout" class="ch.qos.logback.core.ConsoleAppender">
            <encoder>
                <pattern>[%date] %-5level %message \(%logger:%thread\)%n</pattern>
            </encoder>
        </appender>
        <appender name="async" class="ch.qos.logback.classic.AsyncAppender">
            <appender-ref ref="stdout" />
            <queueSize>1024</queueSize>
        </appender>
        <appender name="FILE" class="ch.qos.logback.core.FileAppender">
            <file>/var/log/marathon.log</file>
            <append>true</append>
            <!-- set immediateFlush to false for much higher logging throughput -->
            <immediateFlush>true</immediateFlush>
            <encoder>
                <pattern>$PATTERN$</pattern>
            </encoder>
        </appender>
        <root level="INFO">
            <appender-ref ref="async"/>
            <appender-ref ref="FILE"/>
        </root>
    </configuration>
    ```

 3. Add this configuration block to your `marathon.d/conf.yaml` file to start collecting your Marathon logs:

     ```yaml
    logs:
      - type: file
        path: /var/log/marathon.log
        source: marathon
        service: <SERVICE_NAME>
    ```

 3. [Restart the Agent][5].

### Validation

[Run the Agent's `status` subcommand][5] and look for `marathon` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The Marathon check does not include any events.

### Service Checks

`marathon.can_connect`:

Returns CRITICAL if the Agent cannot connect to the Marathon API to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/marathon/datadog_checks/marathon/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/marathon/metadata.csv
[7]: https://docs.datadoghq.com/help
