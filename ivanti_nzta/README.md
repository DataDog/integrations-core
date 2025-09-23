# Ivanti nZTA

## Overview

[Ivanti nZTA][1] is a cloud-based SaaS solution offering zero-trust authentication and access control for application infrastructures. It enables administrators to define policies for secure user and device access. This ensures application visibility, access control, and robust security.

This integration ingests the following logs:

- **Analytics Logs**: This endpoint contains information about system activity through Admin Logs, Access Logs, and Event Logs.
- **Alerts**: This endpoint contains information about alerts triggered by Ivanti nZTA, including security risks, and configuration changes.
- **Application Access**: This endpoint contains information about application accessed by users.

This integration collects logs from the sources listed above and sends them to Datadog for analysis with our Log Explorer and Cloud SIEM products

- [Log Explorer][3]
- [Cloud SIEM][4]

## Setup

### Generate API credentials in Ivanti nZTA

#### Create a new Admin User

1. Log in to your Ivanti nZTA platform.
2. Go to **Secure Access** > **Manage Users**.
3. Navigate to the **Authentication Servers** tab.
4. Under **Admin Auth**, click **Create User** and enter the following details:
   - **Full Name**: Enter a descriptive and identifiable name.
   - **User Name**: Enter a unique username.
   - **Password**: Enter a strong password.
   - **Confirm Password**: Re-enter the password.
5. Uncheck the **Temporary password** checkbox.
6. Click **Create User**.

**Note**: Use a newly created admin user solely for this integration, rather than the UI login, to ensure smooth execution.

#### Identify the Host

1. To identify the host of your Ivanti nZTA, check the Ivanti nZTA platform URL.
   <br>**For example**: `example.pulsezta.net`

### Connect your Ivanti nZTA Account to Datadog

1. Add your Host, Username, and Password.

   | Parameters | Description                                             |
   | ---------- | ------------------------------------------------------- |
   | Host       | The Host of your Ivanti nZTA platform.                  |
   | Username   | The Tenant Admin Username of your Ivanti nZTA platform. |
   | Password   | The Password of your Ivanti nZTA platform.              |

2. Click **Save**.

## Data Collected

### Logs

The Ivanti nZTA integration collects and forwards analytics logs, alerts, and application access logs to Datadog.

### Metrics

The Ivanti nZTA integration does not include any metrics.

### Service Checks

The Ivanti nZTA integration does not include any service checks.

### Events

The Ivanti nZTA integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://www.ivanti.com/products/ivanti-neurons-zero-trust-access
[2]: https://docs.datadoghq.com/help/
[3]: https://docs.datadoghq.com/logs/explorer/
[4]: https://www.datadoghq.com/product/cloud-siem/
