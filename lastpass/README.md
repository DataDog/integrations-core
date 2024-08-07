## Overview

[LastPass][1] is a password management solution that securely stores and manages passwords and other sensitive
information. LastPass provides users with the ability to generate passwords, synchronize passwords across multiple
devices, and add an extra layer of security through multi-factor authentication.

Integrate with Datadog to gain insights into reporting event logs through the LastPass Enterprise API. The data will be
normalized and enriched before ingestion. Pre-built dashboard visualizations provide immediate insights into LastPass
reporting events, while out-of-the-box detection rules enhance detection and response capabilities.

## Setup

### Configuration

#### Get config parameters of LastPass

##### Account Number

1. Use your email address and master password to log in and access the new [Admin Console](https://admin.lastpass.com/).
2. On the Dashboard tab, click the Profile email located in the top right corner to find the Account Number, which is
   preceded by the words "Account number".
3. Alternatively, you can find the Account Number, preceded by the words "Account number," by navigating to Advanced >
   Enterprise API.

##### Provisioning Hash

1. Access the new [Admin Console](https://admin.lastpass.com) by logging in with your email address and master password.
2. Navigate to Advanced > Enterprise API.
3. From there, you can create or reset a provisioning hash if it is forgotten.

##### Timezone

1. A dropdown with a list of timezones is provided. The timezone values are aligned with LastPass timezone values.
2. The user must select the timezone that is configured in their LastPass account.
3. To verify the LastPass account timezone, perform the following steps:
    - Log in to your LastPass Business account.
    - Access the [Vault page](https://lastpass.com/vault/).
    - Navigate to Account Settings.
    - Under the Account Information section, you can find the selected timezone.

#### LastPass DataDog Integration Configuration

Configure the Datadog endpoint to forward LastPass logs to Datadog.

1. Navigate to `LastPass`.
2. Add your LastPass credentials.

| LastPass Parameters | Description                                                      |
|---------------------|------------------------------------------------------------------|
| Account Number      | Account Number of your registered LastPass account.              |
| Provisioning Hash   | Provisioning Hash secret of your registered account on LastPass. |
| Timezone            | Timezone of your registered account on LastPass                  |

## Data Collected

### Logs

The LastPass integration collects and forwards LastPass Reporting Event logs to Datadog.

### Metrics

The LastPass integration does not include any metrics.

### Events

The LastPass integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.lastpass.com/products/business

[2]: https://docs.datadoghq.com/help/
