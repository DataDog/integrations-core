# Agent Check: IBM WAS

## Overview

This check monitors [IBM Websphere Application Server (WAS)][1] through the Datadog Agent. This check supports IBM WAS versions >= 8.5.5.

## Setup

The IBM WAS Datadog integration collects enabled PMI Counters from the WebSphere Application Server environment. Setup requires enabling the PerfServlet, which provides a way for Datadog to retrieve performance data from WAS.

By default, this check collects JDBC, JVM, thread pool, and Servlet Session Manager metrics. You may optionally specify additional metrics to collect in the "custom_queries" section. See the [sample check configuration][2] for examples.

### Installation

The IBM WAS check is included in the [Datadog Agent][3] package.

#### Enable the PerfServlet
The servlet's .ear file (PerfServletApp.ear) is located in the WAS_HOME/installableApps directory, where WAS_HOME is the installation path for WebSphere Application Server.

The performance servlet is deployed exactly as any other servlet. Deploy the servlet on a single application server instance within the domain.

Note: Starting with version 6.1, you must enable application security to get the PerfServlet working.

### Configuration

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your IBM WAS performance data. See the [sample ibm_was.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][4].

#### Log Collection

Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:
```
    logs_enabled: true
```

Next, point the config file to the proper WAS log files. You can uncomment the lines at the bottom of the WAS integration's config file, and amend them as you see fit:

```yaml
logs:
 - type: file
   path: /opt/IBM/WebSphere/AppServer/profiles/InfoSphere/logs/server1/*.log
   source: ibm_was
   service: websphere
```

### Validation

[Run the Agent's status subcommand][5] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

**ibm_was.can_connect**  
Returns `CRITICAL` if the Agent cannot connect to the PerfServlet for any reason. Returns `OK` otherwise.

### Events

IBM WAS does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.ibm.com/cloud/websphere-application-platform
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[7]: https://docs.datadoghq.com/help
