## Overview

[Forcepoint Security Service Edge][1] simplifies security at the edge by delivering safe access and data protection. Security Service Edge (SSE) eliminates gaps in coverage by unifying policy configuration, enforcement and reporting under a single platform.


This integration ingests the following logs:

- **Cloud Logs (CloudSummary, CloudAudit)**: Logs related to the current status of files in cloud applications and scan results for each file in the account.
- **Access Logs**: Logs related to various application activities.
- **Admin Logs**: Admin events performed within the admin portal.
- **Health Logs (HealthProxy, HealthApi, HealthSystem)**: Logs related to system, API, and proxy health. 


Forcepoint Security Service Edge integration gathers these logs and forwards them to Datadog for seamless analysis. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. With preconfigured out-of-the-box dashboards, the integration offers clear visibility into activities within the Forcepoint Security Service Edge platform. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Generate OAuth Token in Forcepoint Security Service Edge:
1. Login to the Forcepoint ONE Security Service Edge Platform.
2. Navigate to **SETTINGS > API Interface > OAuth**.
3. On the open **REST API OAuth Configuration** page, add and configure different levels of API permissions.
4. Click the **green** plus icons to add a new configuration.
5. On the **Edit Application** dialog, fill out the information as follows:

    a. **Name**: Name for the new application configuration

    b. **Permissions**: Select **Access your Forcepoint logs (logs api)** option.

    c. **Permitted User Group**: Default is **All**. Select based on your requirements.

    d. Click **Ok** to save the changes. You should see your application added to the list, but listed as **Pending** under status.

6. Select the name of your application in the **Application** column to go into the **Edit Application**.

    a. On the **Edit Application** dialog, click the **Token Authorization URL** to authorize your current permission and get the access token.

    b. On the **Requested Access** page send this URL to each permitted user and have them **Approve** their access. The **Requested Access** page allows you to **Approve** or **Deny** the application permission settings.

7. After the user approves, they are given an **Access Token** that is unique to that user. The user must keep this access token, it is required to configure integrations in Datadog. The token is valid forever and must be included in each request for authorization.
8. Once access has been approved, you will notice that **Status** is changed to **Authorized**.


For more information, see the [Setting up an OAuth token][2] documentation.

### Connect your Forcepoint Security Service Edge Account to Datadog

1. Add your Access Token.
   | Parameters          | Description                                                                           |
   | ------------------- | ------------------------------------------------------------------------------------- |
   | Access Token        | Access token from Forcepoint Security Service Edge                         |

2. Click **Save**.

## Data Collected

### Logs

The Forcepoint Security Service Edge integration collects and forwards Cloud logs (CloudSummary, CloudAudit), Access logs, Admin logs and Health logs (HealthProxy, HealthApi, HealthSystem) to Datadog. 

### Metrics

The Forcepoint Security Service Edge integration does not include any metrics.

### Events

The Forcepoint Security Service Edge integration does not include any events.

## Support

For any further assistance, contact [Datadog support][3].

[1]: https://www.forcepoint.com/use-case/security-service-edge-sse
[2]:https://help.forcepoint.com/fpone/sse_admin/prod/oxy_ex-1/deployment_guide/guid-18f77855-8dc9-436a-9fba-179f06a81066.html
[3]: https://docs.datadoghq.com/help/