# Bitwarden

## Overview

[Bitwarden][1] is a password manager that generates, stores, and secures important digital assets in an end-to-end encrypted vault. Users can access their data from anywhere, on any device (desktop, laptop, mobile devices) with secure cloud syncing or self-hosted deployment.

This integration ingests the following logs:

- Event Logs: These logs include information about item events, user events, collection events, group events, and organization events.

This integration seamlessly collects event logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into event logs through out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

## Setup

### Generate API Credentials in Bitwarden

1. Log in to the Bitwarden **Admin Console** using an account with **owner** privileges.
2. Navigate to the **Settings** section.
3. Click **Organization info** in the Settings menu.
4. Scroll down to the **API Key** section.
5. Click **View API key**, enter your **Master password**, and then click **View API key** to reveal the **client_id** and **client_secret** values.
6. Copy the **client_id** and **client_secret**. These credentials are required to configure the integration in Datadog.

### Connect your Bitwarden Account to Datadog

1. Add your Bitwarden Credentials.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | Instance type                         | **Cloud** or **Self-hosted**                                         |
    | Self-hosted instance domain           | The domain of your self-hosted Bitwarden instance (required only for self-hosted Bitwarden setups). The instance must be publicly accessible through HTTPS. Example: vault.example.com, 123.123.123.123:8443.                                                                                              |
    | Cloud Region                          | Select the region where your Bitwarden cloud account is located. See [Bitwarden's documentation][4] to identify your region.   |
    | Client ID                             | Client ID from Bitwarden Admin Console                       |
    | Client Secret                         | Client Secret from Bitwarden Admin Console                   |

2. Click **Save** to save your settings.

## Data Collected

### Logs

The Bitwarden integration collects and forwards [event logs][3] to Datadog.

### Metrics

The Bitwarden integration does not include any metrics.

### Events

The Bitwarden integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://bitwarden.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://bitwarden.com/help/event-logs/
[4]: https://bitwarden.com/help/server-geographies/#tab-web-app-69DKS8RhYi7rLiU7v9QSeV
