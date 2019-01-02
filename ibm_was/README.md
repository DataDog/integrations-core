# Agent Check: IBM WAS

## Overview

This check monitors [IBM WAS][1] through the Datadog Agent.

## Setup

The IBM WAS Datadog integration collects enabled PMI Counters from the WebSphere Application Server environment. Setup requires enabling the PerfServlet as documented on the [IBM documentation][2].

### Installation

The IBM WAS check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your IBM WAS performance data. See the [sample ibm_was.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Service Checks

**ibm_was.can_connect**  
Returns `CRITICAL` if the Agent cannot connect to the PerfServlet for any reason. Returns `OK` otherwise.

### Events

IBM WAS does not include any events at this time.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://www.ibm.com/cloud/websphere-application-platform
[2]: https://www.ibm.com/support/knowledgecenter/en/SSAW57_8.5.5/com.ibm.websphere.nd.multiplatform.doc/ae/tprf_devprfservlet.html
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[8]: https://docs.datadoghq.com/help/
