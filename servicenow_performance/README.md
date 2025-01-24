# ServiceNow Performance

## Overview

[ServiceNow][1] is a comprehensive platform that helps streamline and automate IT service, asset, security, and configuration management processes. It enables organizations to enhance operational efficiency, mitigate risks, and improve service delivery.

The ServiceNow integration collects below types of data:

1. Logs:
    * ITSM 
    * ITAM 
    * Vulnerability Response (VR) 
    * Security Incident Response (SIR) 
    * CMDB Health

2. Metrics:
    * CMDB Health 
    * SecOps Health Analytics (Vulnerability Response)


This integration collects logs and metrics from the sources listed above and sends them to Datadog for analysis with our Log and Metrics Explorer.

* [Log Explorer][2]
* [Metrics Explorer][3]

## Setup

### Prerequisite

1. OAuth plugin should be active for ServiceNow instance.
    * It is active by default on new and upgraded instances.
    * You can verify this by following the instructions in the [OAuth Plugin Activation Guide][4]. 
    * Additionally, ensure that the OAuth activation property is set to True by checking the settings outlined in the [OAuth Property Activation Guide][5].
2. Ensure `glide.oauth.inbound.client.credential.grant_type.enabled` system property is set to **True**
    * If the property does not exist, [create a new][8] one with same name and set it **True**

### Configuration

#### Generate OAuth API credentials in ServiceNow

1. Log in to your ServiceNow instance as an administrator.
2. Navigate to **All > System OAuth > Application Registry**.
3. Click **New** in the top-right corner.
4. On the interceptor page, click **Create an OAuth API Endpoint for External Clients** and enter the following details in the form:
    * **Name**: Enter a name for the OAuth application.
    * **Active**: Ensure the checkbox is selected.
    * **OAuth Application User**: Select/[Create][7] a user with the following roles.
        *   |Module|Roles|
            |--------------------|--------------------|
            |ITSM|`itil`|
            |ITAM|`asset`|
            |CMDB Health|`cmdb_dedup_admin`|
            |Vulnerability Response (VR)|`sn_vul.read_all`, `sn_vul.app_read_all`, `sn_vul_container.read_all`, `sn_sec_analytics.read`|
            |Security Incident Response (SIR)|`sn_si.read`|
        * Note: If the above property is not visible, please [Add OAuth Application User Property][9] and refresh the Application Page
5. In the **Auth Scopes** section, click on `Insert a new row…` below Auth Scope, select **useraccount**, and click the save button.
6. Click Save.
7. Navigate to the newly created application, from the list of applications.
8. Get the **Client ID** and **Client Secret** by clicking the lock icon next to **Client Secret**.


#### Connect your ServiceNow instance to Datadog

1. Add your instance, oauth credentials, and data preference options
    |Parameters|Description|
    |--------------------|--------------------|
    |Instance Name|ServiceNow instance name/subdomain to connect with. [Ex. {instance-name}.service-now.com].|
    |Client ID|The Client ID from ServiceNow platform.|
    |Client Secret|The Client Secret from ServiceNow platform.|
    |Data Collection Type|Dropdown to select the type of data collection: preconfigured or full.|
    |Get ITSM|Enable to collect ITSM data from ServiceNow. The default value is True.|
    |Get ITAM|Enable to collect ITAM data from ServiceNow. The default value is True.|
    |Get CMDB Health|Enable to collect CMDB Health data from ServiceNow. The default value is True.|
    |Get Security Incident Response|Enable to collect Security Incident Response data from ServiceNow. The default value is False. Note: Ensure Security Incident Response Plugin is installed before enabling|
    |Get Vulnerability Response|Enable to collect Vulnerability Response data from ServiceNow. The default value is False. Note: Ensure Vulnerability Response Plugin is installed before enabling|
2. Click the **Save** button to save your settings.

## Data Collected

### Logs 

The ServiceNow integration collects and forwards Vulnerabilities logs to Datadog.

### Metrics

The ServiceNow integration collects and forwards Frameworks metrics to Datadog.

{{< get-metrics-from-git "servicenow-performance" >}}

### Service Checks

The ServiceNow integration does not include any service checks.

### Events

The ServiceNow integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.servicenow.com/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://docs.datadoghq.com/metrics/explorer/
[4]: https://www.servicenow.com/docs/bundle/xanadu-platform-security/page/administer/security/task/t_ActivateOAuth.html
[5]: https://www.servicenow.com/docs/bundle/xanadu-platform-security/page/administer/security/task/t_SetTheOAuthProperty.html
[6]: https://docs.datadoghq.com/help/
[7]: https://www.servicenow.com/docs/bundle/xanadu-platform-administration/page/administer/users-and-groups/task/t_CreateAUser.html
[8]: https://www.servicenow.com/docs/bundle/vancouver-platform-administration/page/administer/reference-pages/task/t_AddAPropertyUsingSysPropsList.html
[9]: https://www.servicenow.com/docs/bundle/xanadu-platform-security/page/integrate/authentication/task/add-oauth-application-user.html