# Agent Check: IBM Spectrum LSF

## Overview

This check monitors [IBM Spectrum LSF][1] using the Datadog Agent. 

Include a high level overview of what this integration does:
- What does your product do (in 1-2 sentences)?
- What value will customers get from this integration, and why is it valuable to them?
- What specific data will your integration monitor, and what's the value of that data?

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The IBM Spectrum LSF check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `ibm_spectrum_lsf.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `ibm_spectrum_lsf` performance data. See the [sample ibm_spectrum_lsf.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `ibm_spectrum_lsf` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The IBM Spectrum LSF integration does not include any events.

### Service Checks

The IBM Spectrum LSF integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/datadog_checks/ibm_spectrum_lsf/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_spectrum_lsf/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
