# Agent Check: SonarQube

## Overview

This check monitors [SonarQube][1].

## Setup

### Installation

The SonarQube check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

SonarQube exposes metrics from two sources: its web API and JMX. To collect all of the
[metrics specified below](#metrics), configure three instances of this check. One to monitor SonarQube's web API, and
the other two to monitor SonarQube's JMX beans.

Documentation on SonarQube's web API is available at `/web_api` on your SonarQube web UI. By default this integration
collects all relevant SonarQube performance metrics exposed through SonarQube's JMX beans. The configuration for these
default metrics is available in the [sonarqube.d/metrics.yaml][3] file. Documentation on these beans is available on
[SonarQube's website][4].

SonarQube's JMX server is **not enabled** by default, this means that unless it is enabled, `sonarqube.server.*` metrics are not collected. More information on how to enable and configure JMX within SonarQube is available within the [SonarQube documentation][5]. Below are configurations needed to enable the JMX server for some common Java processes:

```conf
# WEB SERVER
sonar.web.javaAdditionalOpts="
  -Dcom.sun.management.jmxremote=true
  -Dcom.sun.management.jmxremote.port=10443
  -Dcom.sun.management.jmxremote.rmi.port=10443
  ...
  "

# COMPUTE ENGINE
sonar.ce.javaAdditionalOpts="
  -Dcom.sun.management.jmxremote=true
  -Dcom.sun.management.jmxremote.port=10444
  -Dcom.sun.management.jmxremote.rmi.port=10444
  ...
  "

# ELASTICSEARCH
sonar.search.javaAdditionalOpts="
  -Dcom.sun.management.jmxremote=true
  -Dcom.sun.management.jmxremote.port=10445
  -Dcom.sun.management.jmxremote.rmi.port=10445
  ...
  "
```

This is a basic `sonarqube.d/conf.yaml` example based on SonarQube and JMX defaults. You can use it as a starting point when configuring for both the host-based or container-based Agent installation.

```yaml
init_config:
    is_jmx: false
    collect_default_metrics: true
instances:

  # Web API instance
  - is_jmx: false
    web_endpoint: http://localhost:9000
    auth_type: basic
    username: <username>    # Defined in the Web UI
    password: <password>    # Defined in the Web UI
    default_tag: component  # Optional
    components:             # Required
      my-project:
        tag: project_name

  # Web JMX instance
  - is_jmx: true
    host: localhost
    port: 10443           # See sonar.web.javaAdditionalOpts in SonarQube's sonar.properties file
    user: <username>      # Defined in SonarQube's sonar.properties file
    password: <password>  # Defined in SonarQube's sonar.properties file

  # Compute Engine JMX instance
  - is_jmx: true
    host: localhost
    port: 10444           # See sonar.ce.javaAdditionalOpts in SonarQube's sonar.properties file
    user: <username>      # Defined in SonarQube's sonar.properties file
    password: <password>  # Defined in SonarQube's sonar.properties file
```

**Note**: Once the integration is configured, have SonarQube scan at least one project to send metrics to Datadog.

Metrics collected by this integration are tagged with a `component` tag by default. If you wish to change the tag
name on a per component basis, specify the `tag` property within the component definition. To set it for all projects,
set the `default_tag` property on the instance config.

**Note**: Projects in SonarQube often contain multiple source control branches. This integration can only collect metrics from the default branch in SonarQube (typically `main`).

#### Search server metrics

SonarQube exposes a search server, which can be monitored using an additional instance of this integration and a configuration of the JMX metrics. To learn how to customize the metrics to collect, see the [JMX Checks documentation][6] for more detailed instructions. For an example, use the config below and default JMX metric config in [sonarqube.d/metrics.yaml][3].

```yaml
init_config:
  # The list of metrics to be collected by the integration.
  config:
    - include:
      domain: SonarQube
      name: <name>
      exclude_tags:
        - name
      attribute:
        MyMetric:
          alias: sonarqube.search_server.my_metric
          metric_type: gauge
instances:
  # Search Server JMX instance
  - is_jmx: true
    host: localhost
    port: 10445           # See sonar.search.javaAdditionalOpts in SonarQube's sonar.properties file
    user: <username>      # Defined in SonarQube's sonar.properties file
    password: <password>  # Defined in SonarQube's sonar.properties file
```

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `sonarqube.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your SonarQube data.
   See the [sample sonarqube.d/conf.yaml][7] for all available configuration options.

   This check has a limit of 350 metrics per JMX instance. The number of returned metrics is indicated in [the status page][13].
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect, see the [JMX Checks documentation][6] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][8].

2. [Restart the Agent][9].

##### Log collection

1. Enable SonarQube [logging][10].

2. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Add the following configuration block to your `sonarqube.d/conf.yaml` file. Change the `path` and `service` parameter values based on your environment. See the [sample sonarqube.d/conf.yaml][7] for all available configuration options.

   ```yaml
   logs:
     - type: file
       path: /opt/sonarqube/logs/access.log
       source: sonarqube
     - type: file
       path: /opt/sonarqube/logs/ce.log
       source: sonarqube
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/es.log
       source: sonarqube
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/sonar.log
       source: sonarqube
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
     - type: file
       path: /opt/sonarqube/logs/web.log
       source: sonarqube
       log_processing_rules:
         - type: multi_line
           name: log_start_with_date
           pattern: \d{4}\.\d{2}\.\d{2}
   ```

5. [Restart the Agent][9].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

##### Metric collection

For containerized environments, see the [Autodiscovery with JMX][11] guide.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][12].

| Parameter      | Value                                              |
| -------------- | -------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "sonarqube"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Components Discovery

You can configure how your components are discovered with the `components_discovery` parameter.

`limit`
: Maximum number of items to be autodiscovered.  
**Default value**: `10`

`include`
: Mapping of regular expression keys and component config values to autodiscover.  
**Default value**: empty map

`exclude`
: List of regular expressions with the patterns of components to exclude from autodiscovery.  
**Default value**: empty list

**Examples**:

Include a maximum of `5` components with names starting with `my_project`:

```yaml
components_discovery:
  limit: 5
  include:
    'my_project*':
```

Include a maximum of `20` components and exclude those beginning with `temp`:

```yaml
components_discovery:
  limit: 20
  include:
    '.*':
  exclude:
    - 'temp*'
```

Include all components with names starting with `issues`, apply the `issues_project` tag, and only collect metrics belonging to the category `issues`. As `limit` is not defined, the number of components discovered is limited to the default value `10`:
```yaml
components_discovery:
  include:
    'issues*':
       tag: issues_project
       include:
         - issues.
```

### Validation

[Run the Agent's status subcommand][13] and look for `sonarqube` under the **JMXFetch** section:

```text
========
JMXFetch
========
  Initialized checks
  ==================
    sonarqube
      instance_name : sonarqube-localhost-10444
      message : <no value>
      metric_count : 33
      service_check_count : 0
      status : OK
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
    sonarqube (1.1.0)
    -----------------
      Instance ID: sonarqube:1249c1ed7c7b489a [OK]
      Configuration Source: file:/etc/datadog-agent/conf.d/sonarqube.d/conf.yaml
      Total Runs: 51
      Metric Samples: Last Run: 39, Total: 1,989
      Events: Last Run: 0, Total: 0
      Service Checks: Last Run: 1, Total: 51
      Average Execution Time : 1.19s
      Last Execution Date : 2021-03-12 00:00:44.000000 UTC
      Last Successful Execution Date : 2021-03-12 00:00:44.000000 UTC
```

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this check.

### Events

SonarQube does not include any events.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}


[1]: https://www.sonarqube.org
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/datadog_checks/sonarqube/data/metrics.yaml
[4]: https://docs.sonarqube.org/latest/instance-administration/monitoring/
[5]: https://docs.sonarsource.com/sonarqube/latest/instance-administration/monitoring/instance/#how-do-i-activate-jmx
[6]: https://docs.datadoghq.com/integrations/java/
[7]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/datadog_checks/sonarqube/data/conf.yaml.example
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.sonarqube.org/latest/instance-administration/system-info/
[11]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[12]: https://docs.datadoghq.com/agent/docker/log/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/metadata.csv
[15]: https://github.com/DataDog/integrations-core/blob/master/sonarqube/assets/service_checks.json
