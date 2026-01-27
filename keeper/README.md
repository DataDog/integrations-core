## Overview

[Keeper][1] is a zero-knowledge password management solution that helps organizations securely store, share, and manage credentials across users, devices, and applications.

Integrate Keeper with Datadog to gain insights into reporting event logs using pre-built dashboard visualizations. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Prerequisites

- This integration requires Keeper Advanced Reporting and Alerts Module (ARAM) add-on.

### Configuration

#### Enable Keeper Logging to Datadog

1. Login to Keeper [admin console][2].
2. Go to **Reporting & Alerts** from the navigation panel on the left side.
3. Select **External Logging** from tabs on top.
4. Under **Datadog**, click **Setup**.
5. On the pop-up form, configure the fields as follows:
      1. Enter your [Datadog site][4] under **URL** (e.g., `datadoghq.com`).
      2. Enter your [Datadog API key][5] under **API Key**.
      3. You can test the connection by clicking **Test Connection**.
      4. Click **Save**.

## Data Collected

### Logs

The Keeper integration enables reporting events logging to Datadog. These logs include:
- Login events: tracks user and admin login attempts.
- Account activities: includes changes to user accounts. 
- Password Sharing: includes activities related to record or folder sharing.
- Security events: captures security-related actions.
- General usage: logs general user activities.
- Policy activities: records changes to administrative policies or restrictions.
- BreachWatch events: alerts password risks.
- Privileged Access Manager events: logs activities related to secure remote access, session management, and infrastructure connectivity.
- Secrets Manager events: tracks API-based secret access and related actions.
- Compliance reporting: captures compliance reporting actions.
- Security Benchmark events: logs actions taken on security best practice recommendations.
- KeeperChat events: logs messaging activity inside the KeeperChat.


### Metrics

The Keeper integration does not include any metrics.

### Events

The Keeper integration does not include any events.

## Support

For any further assistance, contact [Datadog support][3].

[1]: https://www.keepersecurity.com/en_GB/enterprise.html
[2]: https://keepersecurity.com/en_GB/console/?#login
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[5]: https://docs.datadoghq.com/account_management/api-app-keys/#add-an-api-key-or-client-token
