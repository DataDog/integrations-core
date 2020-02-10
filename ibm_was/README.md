# Agent Check: IBM WAS

## Overview

This check monitors [IBM Websphere Application Server (WAS)][1] through the Datadog Agent. This check supports IBM WAS versions >= 8.5.5.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

The IBM WAS Datadog integration collects enabled PMI Counters from the WebSphere Application Server environment. Setup requires enabling the PerfServlet, which provides a way for Datadog to retrieve performance data from WAS.

By default, this check collects JDBC, JVM, thread pool, and Servlet Session Manager metrics. You may optionally specify additional metrics to collect in the "custom_queries" section. See the [sample check configuration][3] for examples.

### Installation

The IBM WAS check is included in the [Datadog Agent][4] package.

#### Enable the PerfServlet

The servlet's .ear file (PerfServletApp.ear) is located in the `<WAS_HOME>/installableApps` directory, where `<WAS_HOME>` is the installation path for WebSphere Application Server.

The performance servlet is deployed exactly as any other servlet. Deploy the servlet on a single application server instance within the domain.

**Note**: Starting with version 6.1, you must enable application security to get the PerfServlet working.

### Modify the currently monitored statistic set

By default, your application server is only configured for "Basic" monitoring. In order to gain complete visibility into your JVM, JDBC connections, and servlet connections, change the currently monitored statistic set for your application server from "Basic" to "All".

From the Websphere Administration Console, you can find this setting in `Application servers > <YOUR_APP_SERVER> > Performance Monitoring Infrastructure (PMI)`.

Once you've made this change, click "Apply" to save the configuration and restart your application server. Additional JDBC, JVM, and servlet metrics should appear in Datadog shortly after this change.

### Configuration

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your IBM WAS performance data. See the [sample ibm_was.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Next, edit `ibm_was.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your WAS log files.

   ```yaml
   logs:
     - type: file
       path: /opt/IBM/WebSphere/AppServer/profiles/InfoSphere/logs/server1/*.log
       source: ibm_was
       service: websphere
   ```

3. [Restart the Agent][5].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                         |
| -------------------- | ----------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `ibm_was`                                                                     |
| `<INIT_CONFIG>`      | blank or `{}`                                                                 |
| `<INSTANCE_CONFIG>`  | `{"servlet_url": "http://%%host%%:%%port%%/wasPerfTool/servlet/perfservlet"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][6].

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "ibm_was", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][7] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

**ibm_was.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to the PerfServlet for any reason, otherwise returns `OK`.

### Events

IBM WAS does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.ibm.com/cloud/websphere-application-platform
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/docker/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[9]: https://docs.datadoghq.com/help
