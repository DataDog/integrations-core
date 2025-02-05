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

#### Connect your ServiceNow instance to Datadog

1. Add your instance, username, password, and data preference options
    |Parameters|Description|
    |--------------------|--------------------|
    |Instance Name|ServiceNow instance name/subdomain to connect with. [Ex. {instance-name}.service-now.com].|
    |Username| Username of ServiceNow instance.|
    |Password| Password of ServiceNow instance.|
    |Data Collection Type|Dropdown to select the type of data collection: preconfigured or full.|
    |Get ITSM|Enable to collect ITSM data from ServiceNow. The default value is True.|
    |Get ITAM|Enable to collect ITAM data from ServiceNow. The default value is True.|
    |Get CMDB Health|Enable to collect CMDB Health data from ServiceNow. The default value is True.|
    |Get Security Incident Response|Enable to collect Security Incident Response data from ServiceNow. The default value is False. Note: Ensure Security Incident Response Plugin is installed before enabling|
    |Get Vulnerability Response|Enable to collect Vulnerability Response data from ServiceNow. The default value is False. Note: Ensure Vulnerability Response Plugin is installed before enabling|
2. Click the **Save** button to save your settings.

**Note:** You can create a new user with the necessary roles in ServiceNow for the integration.


## Data Collected

### Logs 

The ServiceNow integration collects and forwards ITSM, ITAM, Vulnerability Response (VR), Security Incident Response (SIR), and CMDB Health logs to Datadog.

### Metrics

The ServiceNow integration collects and forwards CMDB Health, and SecOps Health Analytics (Vulnerability Response) metrics to Datadog.

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