# PingOne

## Overview

[PingOne][1] is an identity-as-a-service (IDaaS) offering by Ping Identity. It's a cloud-based identity platform that provides a range of services related to identity and access management (IAM), including single sign-on (SSO), multi-factor authentication (MFA), user management, and more.

This integration ingests the following logs:

- Audit: Represents all actions performed in the PingOne admin console and PingDirectory. They can be used to document a historical record of activity for compliance purposes and other business policy enforcement.

The PingOne integration seamlessly collects the data of PingOne audit logs using the REST APIs. Using the out-of-the-box logs pipeline, the logs are parsed and enriched for easy searching and analysis. This integration includes several dashboards visualizing total Audit events, total successful and total failed login attempts, total successful and total failed kerberos login attempts, and more.

## Setup

### Generate API credentials in PingOne

1. Log into your [PingOne account][2].
2. From the navigation sidebar, expand the **Applications** section and select **Applications**.
3. Click **+** (plus) to begin creating a new application.
4. Enter an **Application Name**.
5. Select **Worker** as the application type.
6. On the application flyout, ensure that the toggle switch in the header is activated in order to enable the application.
7. Select the **Roles** tab of the application flyout.
8. Click the **Grant Roles** button.
9. Under **Available responsibilities**, in the **Environment Admin section**, select the environments to grant access to, then click **Save**.
10. Select the **Configuration** tab of the application flyout to get **Client ID**, **Client Secret** and **Environment ID**.

### Connect your PingOne account to Datadog

1. Add your PingOne credentials.

    | PingOne Parameters | Description                                                                |
    | ----------------------------- | ----------------------------------------------------------------|
    | Domain                        | The top level domain from PingOne.                              |
    | Environment ID                | The environment ID from PingOne.                                |
    | Client ID                     | The client ID from PingOne.                                     |
    | Client Secret                 | The client secret from PingOne.                                 |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

This integration collects and forwards PingOne audit logs to Datadog.

### Metrics

The PingOne integration does not include any metrics.

### Events

The PingOne integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://www.pingidentity.com/en.html
[2]: https://www.pingidentity.com/bin/ping/signOnLink
[3]: https://docs.datadoghq.com/help/
