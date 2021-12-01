# Agent Check: weblogic

## Overview

This check monitors Oracle [Weblogic][1] Server. 

## Setup

### Installation

The Weblogic check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

This check is JMX-based and collects metrics from the PlatformMBeanServer exported by the JVM, so JMX Remote Monitoring needs to be enabled on your Weblogic servers. Follow the instructions in the [Oracle documentation][8].

Ensure that the [`PlatformMBeanServerUsed`][9] attribute value is set to `true` in the Weblogic Administration Console (default value is `true` in Weblogic Server versions 10.3.3.0 and above).  

### Configuration

1. Edit the `weblogic.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your weblogic performance data.
   See the [sample weblogic.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][3].
   You can specify the metrics you are interested in by editing the [configuration][2].
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][5].

2. [Restart the Agent][6]

### Validation

[Run the Agent's `status` subcommand][3] and look for `weblogic` under the Checks section.

## Data Collected

### Metrics

See [`metadata.csv`][10] for a list of metrics provided by this integration.  

### Log collection

_Available for Agent versions >6.0_

1. WebLogic logging services use an implementation based on the Java Logging APIs by default. Clone and edit the [integration pipeline][11] if you have a different format.
2. Collecting logs is disabled by default in the Datadog Agent, enable it in your datadog.yaml file:
   ```yaml
   logs_enabled: true
   ```
3. Uncomment and edit the logs configuration block in your weblogic.d/conf.yaml file. Change the path and service parameter values based on your environment. See the [sample weblogic.d/conf.yaml][2] for all available configuration options.
   ```yaml
    - type: file
      path: <DOMAIN_DIR>/servers/<ADMIN_SERVER_NAME>/logs/<ADMIN_SERVER_NAME>.log
      source: weblogic
      service: <SERVER_NAME>
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \####<\w{3} (0?[1-9]|[12][0-9]|3[01]), \d{4}
    - type: file
      path: <DOMAIN_DIR>/servers/<SERVER_NAME>/logs/<SERVER_NAME>.log
      source: weblogic
      service: <SERVER_NAME>
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \####<\w{3} (0?[1-9]|[12][0-9]|3[01]), \d{4}
    - type: file
      path: <DOMAIN_DIR>/servers/<SERVER_NAME>/logs/access.log
      source: weblogic
      service: <SERVER_NAME>
      log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \####<\w{3} (0?[1-9]|[12][0-9]|3[01]), \d{4}
   ```
4. [Restart the Agent][6]

### Containerized
For containerized environments, see the [Autodiscovery with JMX][12] guide.

### Events

The weblogic integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/weblogic/datadog_checks/weblogic/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.datadoghq.com/integrations/java/
[5]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://github.com/DataDog/integrations-core/blob/master/weblogic/assets/service_checks.json
[8]: https://docs.oracle.com/javase/8/docs/technotes/guides/management/agent.html#gdenl
[9]: https://docs.oracle.com/en/middleware/standalone/weblogic-server/14.1.1.0/jmxcu/understandwls.html#GUID-1D2E290E-F762-44A8-99C2-EB857EB12387
[10]: https://github.com/DataDog/integrations-core/blob/master/weblogic/metadata.csv
[11]: https://docs.datadoghq.com/logs/processing/#integration-pipelines 
[12]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent