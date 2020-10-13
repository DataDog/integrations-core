# Agent Check: SonarQube

## Overview

This check monitors [SonarQube][1].

## Setup

### Installation

The SonarQube check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `sonarqube.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your SonarQube data.
   See the [sample sonarqube.d/conf.yaml][3] for all available configuration options.

   This check has a limit of 350 metrics per JMX instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect, visit the [JMX Checks documentation][4] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][5].

2. [Restart the Agent][6].

##### Log collection

1. Enable SonarQube [logging][7].

2. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Add the following configuration block to your `sonarqube.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample sonarqube.d/conf.yaml][3] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /opt/sonarqube/logs/access.log
       source: sonarqube
       service: <SERVICE>
     - type: file
       path: /opt/sonarqube/logs/ce.log
       source: sonarqube
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/es.log
       source: sonarqube
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/sonar.log
       source: sonarqube
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/web.log
       source: sonarqube
       service: <SERVICE>
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
   ```

5. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][8] guide.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][9].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "sonarqube", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][10] and look for `sonarqube` under the **JMXFetch** section:

```text
========
JMXFetch
========
  Initialized checks
  ==================
    sonarqube
      instance_name : sonarqube-localhost-10443
      message : <no value>
      metric_count : 38
      service_check_count : 0
      status : OK
```

If you set an instance without `is_jmx: true`, also look for `sonarqube` under the **Collector** section:

```text
=========
Collector
=========
  Running Checks
  ==============
    sonarqube (1.0.0)
    -----------------
      Instance ID: sonarqube:f872f6fd88ce0d82 [OK]
      Configuration Source: file:/etc/datadog-agent/conf.d/sonarqube.d/sonarqube.yaml
      Total Runs: 2,925
      Metric Samples: Last Run: 39, Total: 114,075
      Events: Last Run: 0, Total: 0
      Service Checks: Last Run: 1, Total: 2,925
      Average Execution Time : 29ms
      Last Execution Date : 2020-10-29 13:25:37.000000 UTC
      Last Successful Execution Date : 2020-10-29 13:25:37.000000 UTC
      metadata:
        version.build: 37579
        version.major: 8
        version.minor: 5
        version.patch: 0
        version.raw: 8.5.0.37579
        version.scheme: semver
```

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

### Service Checks

**sonarqube.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored SonarQube instance's JMX endpoint, otherwise returns `OK`.

**sonarqube.api_access**:<br>
Returns `CRITICAL` if the Agent is unable to connect to and collect metrics from the monitored SonarQube instance's web endpoint, otherwise returns `OK`.

### Events

SonarQube does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.sonarqube.org
[2]: https://docs.datadoghq.com/agent/
[3]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/datadog_checks/sonarqube/data/conf.yaml.example
[4]: https://docs.datadoghq.com/integrations/java/
[5]: https://docs.datadoghq.com/help/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.sonarqube.org/latest/instance-administration/system-info/
[8]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[9]: https://docs.datadoghq.com/agent/docker/log/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/metadata.csv
