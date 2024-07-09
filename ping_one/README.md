# PingOne Integration for Datadog

## Overview

[PingOne][1] is an identity-as-a-service (IDaaS) offering by Ping Identity. It's a cloud-based identity platform that provides a range of services related to identity and access management (IAM), including single sign-on (SSO), multi-factor authentication (MFA), user management, and more.

The PingOne integration collects Audit logs and sends them to Datadog. Using the out-of-the-box logs pipeline, the logs are parsed and enriched for easy searching and analysis. This integration includes several dashboards visualizing total Audit events, total successful and total failed login attempts, total successful and total failed kerberos login attempts, and more.

## Setup

### Configuration

#### PingOne Configuration

1. Login to [PingOne][2] with your credentials.
2. From the navigation sidebar, expand the **Applications** section and select **Applications**.
3. Click **+** (plus) to begin creating a new application.
4. Enter an **Application Name**.
5. Select **Worker** as the application type.
6. On the application flyout, ensure that the toggle switch in the header is activated in order to enable the application.
7. Select the **Roles** tab of the application flyout.
8. Click the **Grant Roles** button.
9. Under **Available responsibilities**, in the **Environment Admin section**, select the environments to grant access to, then click **Save**.
10. Select the **Configuration** tab of the application flyout.
11. From the General section, copy the **Client ID**, **Client Secret** and **Environment ID**.

#### PingOne DataDog Integration Configuration

Configure the Datadog endpoint to forward PingOne events as logs to Datadog.

1. Navigate to `PingOne`.
2. Add your PingOne credentials.

| PingOne Parameters | Description                                                                |
| ----------------------------- | -------------------------------------------------------------------------- |
| Client Id                       | The Client Id from PingOne.                                           |
| Client Secret                   | The Client Secret from PingOne.                                        |
| Environment Id                  | The Environment Id from PingOne.                                        |
| Domain                          | The Top level domain from PingOne.                                        |

## Data Collected

### Logs

The integration collects and forwards PingOne logs to Datadog.

### Metrics

The PingOne integration does not include any metrics.

### Events

The PingOne integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://www.pingidentity.com/en.html
[2]: https://www.pingidentity.com/bin/ping/signOnLink
[3]: https://docs.datadoghq.com/help/
