# Automox

## Overview

[Automox][1] is a cloud-native endpoint management platform that automates patching, configuration, and remediation for Windows, macOS, and Linux devices.

This integration collects the following from an Automox organization:

- **Audit trail**: administrative activity in the Automox console, such as sign-ins, policy and device changes, API key and role management, and remote control sessions.
- **Console events**: devices added and removed, patches applied and failed, policy actions, and users created and removed.
- **Policy executions**: the outcome of each policy run, with the number of devices that succeeded, failed, or are still pending.
- **Metrics**: device inventory and status, outstanding patches by severity and age, known-exploited vulnerabilities, policy compliance, manual approvals, and devices that need attention.

With the out-of-the-box logs pipeline, the logs are parsed, enriched, and mapped to the Open Cybersecurity Schema Framework (OCSF) for easy searching and analysis. The integration includes a dashboard and recommended monitors for patch exposure and policy compliance.

## Setup

### Generate an API key in Automox

1. Log in to the [Automox console][2].
2. Go to **Settings** > **Keys**, and create an API key. An organization API key is sufficient. A [global API key][3] also works.
3. Copy the API key.

### Find your organization ID

The integration needs the numeric ID of the Automox organization, not its UUID. While in the Automox console:

1. Go to [Setup & Configuration > Organizations][4].
2. Copy the numeric Organization ID value.

### Connect your Automox organization to Datadog

1. Add your Automox organization ID and API key.

    | Automox Parameters | Description                                                      |
    |--------------------|------------------------------------------------------------------|
    | Organization ID    | The numeric ID of the Automox organization to collect data from. |
    | API Key            | The API key generated in the steps above.                        |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Automox integration collects the Automox audit trail, console events, and policy executions.

### Metrics

The Automox integration collects device, patch, policy compliance, and approval metrics.

### Events

The Automox integration does not include any events.

### Service Checks

The Automox integration does not include any service checks.

## Support

For further assistance, contact [Datadog Support][5].

[1]: https://www.automox.com/
[2]: https://console.automox.com/
[3]: https://docs.automox.com/product/Developer/Using_Global_API_Keys.htm
[4]: https://console.automox.com/global/setup/organizations
[5]: https://docs.datadoghq.com/help/
