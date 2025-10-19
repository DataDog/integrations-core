## Overview

[Forcepoint Secure Web Gateway][1] applies web security policies in the cloud or on the endpoint with distributed enforcement for secure, high-speed access to the web, wherever your people are. It also offers advanced data loss prevention (DLP) capabilities to keep sensitive information from leaking onto websites.



This integration ingests the following logs:

- **Web Logs**: Logs generated from general web traffic activity by users.
- **Web DLP Logs**: Logs generated from data loss prevention (DLP) policy actions.


The Forcepoint Secure Web Gateway integration gathers these logs and forwards them to Datadog for seamless analysis. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating advanced search and detailed insights. With preconfigured out-of-the-box dashboards, the integration offers visibility into web activities. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


**Minimum Agent version:** 7.61.0

## Setup

### Generate an OAuth token for Forcepoint Secure Web Gateway
1. Log into the Forcepoint ONE Security Service Edge Platform.
2. Navigate to **SETTINGS > API Interface > OAuth**.
3. The **REST API OAuth Configuration** page opens, which allows you to add and configure different levels of API permissions.
4. To add a new configuration, click the green plus icon.
5. On the **Edit Application** dialog, fill out the following information:

    a. **Name**: Enter a name for the new application configuration.

    b. **Permissions**: Select **Access your Forcepoint logs (logs api)**.

    c. **Permitted User Groups**: Select your required setting. Default is **All**.

    d. Click **OK** to save the changes. Your application is added to the list, but its status is still **Pending**.
6. Select your application's name in the **Application** column to open the **Edit Application** dialog.
    
    a. Click the **Token Authorization URL** to authorize your current permission and get an access token.
    
    b. On the **Requested Access** page, select **Approve** for the application permission settings. 
    
    c. For each permitted user, send them the Token Authorization URL and have them approve their access.
7. After approval, the user is given an access token that is unique to that user and that the user must keep. This access token is required to configure integration with Datadog. The token is valid forever and must be included in each request for authorization.
8. Once access has been approved, the application's status changes to **Authorized**.


For more information, refer to Forcepoint's documentation on [Setting up an OAuth token][2].

### Connect your Forcepoint Secure Web Gateway Edge to Datadog

1. Add your Access Token.
   | Parameters          | Description                                                                           |
   | ------------------- | ------------------------------------------------------------------------------------- |
   | Access Token       | Access token generated above                      |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Forcepoint Secure Web Gateway integration collects and forwards Web logs and Web DLP logs to Datadog. 

### Metrics

The Forcepoint Secure Web Gateway integration does not include any metrics.

### Events

The Forcepoint Secure Web Gateway integration does not include any events.

## Support

For any further assistance, contact [Datadog support][3].

[1]: https://www.forcepoint.com/product/secure-web-gateway-swg
[2]:https://help.forcepoint.com/fpone/sse_admin/prod/oxy_ex-1/deployment_guide/guid-18f77855-8dc9-436a-9fba-179f06a81066.html
[3]: https://docs.datadoghq.com/help/
