## Overview

[LastPass][1] is a password management solution that securely stores and manages passwords and other sensitive
information. LastPass provides users with the ability to generate passwords, synchronize passwords across multiple
devices, and add an extra layer of security through multi-factor authentication.

Integrate LastPass with Datadog to gain insights into reporting event logs through the LastPass Enterprise API. The data is
normalized and enriched before ingestion. Pre-built dashboard visualizations provide immediate insights into LastPass
reporting events, while out-of-the-box detection rules enhance detection and response capabilities.

## Setup

### Configuration

#### Get config parameters of LastPass

##### Account number

1. Log in to the [Admin Console](https://admin.lastpass.com/) with your email address and master password.
2. On the **Dashboard** tab, click the profile email located in the top right corner to find the account number.
3. Alternatively, you can find the account number by navigating to **Advanced** > **Enterprise API**.

##### Provisioning hash

1. Log in to the [Admin Console](https://admin.lastpass.com) with your email address and master password.
2. Navigate to **Advanced** > **Enterprise API**.
3. From there, you can create or reset a provisioning hash if you forgot it.

##### Time zone

1. The options in the **Time Zone** dropdown menu are based on LastPass' time zone values.
2. You must select the time zone that is configured in your LastPass account.
3. To verify your LastPass account's time zone, do the following:
    - Log in to your LastPass Business account.
    - Access the [Vault page](https://lastpass.com/vault/).
    - Navigate to **Account Settings**.
    - Find the selected time zone under the **Account Information** section.

#### Configure the LastPass and Datadog integration

Configure the Datadog endpoint to forward LastPass logs to Datadog.

1. Navigate to `LastPass` integration on Datadog platform.
2. Add your LastPass credentials.

| LastPass Parameters | Description                                                          |
|---------------------|----------------------------------------------------------------------|
| Account number      | The account number of your registered LastPass account.              |
| Provisioning hash   | The provisioning hash secret of your registered account on LastPass. |
| Time zone           | The time zone of your registered account on LastPass                 |

## Data Collected

### Logs

The LastPass integration collects and forwards LastPass reporting event logs to Datadog.

### Metrics

The LastPass integration does not include any metrics.

### Events

The LastPass integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.lastpass.com/products/business

[2]: https://docs.datadoghq.com/help/
