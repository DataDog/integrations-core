## Overview

[Forcepoint Security Service Edge][1] simplifies security at the edge by delivering safe access and data protection. Security Service Edge (SSE) eliminates gaps in coverage by unifying policy configuration, enforcement and reporting under a single platform.


This integration ingests the following logs:

- **Cloud Logs (CloudSummary, CloudAudit)**: It contains logs related to scanning results of each file.
- **Access Logs**: It contains logs related to various application activities.
- **Admin Logs**: It contains all admin events performed within the admin portal.
- **Health Logs (HealthProxy, HealthApi, HealthSystem)**: It contains logs related to system, api and proxy health. 


Forcepoint Security Service Edge integration gathers these logs and forwards them to Datadog for seamless analysis. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. With preconfigured out-of-the-box dashboards, the integration offers clear visibility into activities within the Forcepoint Security Service Edge platform. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Generate OAuth Token in Forcepoint Security Service Edge:
1. Login to the Forcepoint ONE Security Service Edge Platform.
2. Navigate to **SETTINGS > API Interface > OAuth**.
3. **REST API OAuth Configuration** page opens which allows you to add and configure different levels of API permissions.
4. To add a new configuration, click the **green** plus icons.
5. On the **Edit Application** dialog, fill out the information as mentioned below:

    a. **Name**: Name for the new application configuration

    b. **Permissions**: Select **Access your Forcepoint logs (logs api)** option.

    c. **Permitted User Group**: Select as per your requirement. Default is **All**.

    d. Click **Ok** to save the changes.
    - You will now see your application added to the list, but still listed as **Pending** under status.
6. Select the name of your application in the **Application** column to  go into the **Edit Application**.

    a. On the **Edit Application** dialog, you will need the **Token Authorization URL** to authorize your current permission and get the access token.

    b. Click on the URL and it will take you to the **Requested Access** page allowing you to **Approve** or **Deny** the application permission settings. Again you will need to send this URL to each permitted user and have them **Approve** their access.
7. After you approve, you will be given an **Access Token** that is unique to that user  and that the user must keep. This access token will be required to configure integration in datadog. The token is valid forever and must be included in each request for authorization.
8. Once access has been approved, you will notice that **Status** is changed to **Authorized**.


For reference: [Setting up an OAuth token Documentation][2]

### Connect your Forcepoint Security Service Edge Account to Datadog

1. Add your Access Token.
   | Parameters          | Description                                                                           |
   | ------------------- | ------------------------------------------------------------------------------------- |
   | Access Token       | Access token from Forcepoint Security Service Edge                         |

2. Click the Save button to save your settings.

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