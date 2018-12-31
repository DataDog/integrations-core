# Agent Check: IBM WAS

## Overview

This check monitors [IBM WAS][1].

## Setup

The IBM WAS Datadog Integration collects enabled PMI Counters from the WebSphere Application Server environment. Setup requires enabling the PerfServlet as documented on the [IBM documentation][8]

### Installation

The Ibm_was check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your ibm_was performance data.
   See the [sample ibm_was.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this check

### Events

`IBM WAS` does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][5].

[1]: https://www.ibm.com/cloud/websphere-application-platform
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/service_checks.json
[8]: https://www.ibm.com/support/knowledgecenter/en/SSAW57_8.5.5/com.ibm.websphere.nd.multiplatform.doc/ae/tprf_devprfservlet.html