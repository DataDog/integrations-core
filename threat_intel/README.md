# Threat Intel

## Overview

This integration queries the [AbuseIPDB](https://www.abuseipdb.com/) threat intelligence API to check IP addresses for known malicious activity and sends the results as logs to Datadog.

The check periodically queries the configured IP addresses against the AbuseIPDB database, reporting abuse confidence scores, ISP information, country of origin, and report counts.

## Setup

### Prerequisites

You need an AbuseIPDB API key. You can sign up for a free account at [AbuseIPDB](https://www.abuseipdb.com/).

### Installation

The Threat Intel check is included in the [Datadog Agent][1] package. No additional installation is needed on your server.

### Configuration

1. Edit the `threat_intel.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting threat intelligence data. See the [sample threat_intel.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `threat_intel` under the Checks section.

## Data Collected

### Logs

The Threat Intel check sends log events containing threat intelligence data for each queried IP address, including:

- IP address
- Abuse confidence score
- Country code
- ISP
- Domain
- Total reports
- Whitelist status
- Last reported timestamp

### Service Checks

**threat_intel.can_connect**: Returns `CRITICAL` if the check fails to query the AbuseIPDB API. Returns `OK` otherwise.

## Support

Need help? Contact [Datadog support][5].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://github.com/DataDog/integrations-core/blob/master/threat_intel/datadog_checks/threat_intel/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
