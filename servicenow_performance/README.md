# ServiceNow Performance

## Overview

[ServiceNow][1] is a comprehensive platform that helps streamline and automate IT service, asset, security, and configuration management processes. It enables organizations to enhance operational efficiency, mitigate risks, and improve service delivery.

The ServiceNow integration collects the following types of data:

1. Logs:
    * ITSM 
    * ITAM 
    * Vulnerability Response (VR) 
    * Security Incident Response (SIR) 
    * CMDB Health

2. Metrics:
    * CMDB Health 
    * SecOps Health Analytics (Vulnerability Response)


This integration collects logs and metrics from the sources listed above and sends them to Datadog for analysis using the Log and Metrics Explorer.

* [Log Explorer][2]
* [Metrics Explorer][3]

## Setup

### Prerequisite
- List of required ServiceNow plugins and roles by module for integration
    |Module|User Roles Required|Plugin Required|
    |--------------------|--------------------|--------------------|
    |ITSM|`itil`|-|
    |ITAM|`asset`|-|
    |CMDB Health|`cmdb_dedup_admin`|-|
    |Vulnerability Response (VR)| `sn_sec_analytics.read` ,<br>`sn_vul.app_read_all` ,<br>`sn_vul.read_all` ,<br>`sn_vul_container.read_all`|`Vulnerability Response and Configuration Compliance for Containers` ,<br>`Vulnerability Response`|
    |Security Incident Response (SIR)|`sn_si.read`|`Security Incident Response`|

### Configuration
#### Connect your ServiceNow instance to Datadog

1. Add your instance, username, password, and data preference options
    |Parameters|Description|
    |--------------------|--------------------|
    |Instance Name|ServiceNow instance name/subdomain to connect with. For example, `{instance-name}.service-now.com`.|
    |Username| Username of ServiceNow instance.|
    |Password| Password of ServiceNow instance.|
    |Data Collection Type|Use the dropdown to select the type of data collection: preconfigured or full.|
    |Get ITSM|Enable to collect ITSM data from ServiceNow. The default value is True.|
    |Get ITAM|Enable to collect ITAM data from ServiceNow. The default value is True.|
    |Get CMDB Health|Enable to collect CMDB Health data from ServiceNow. The default value is True.|
    |Get Security Incident Response|Enable to collect Security Incident Response data from ServiceNow. The default value is False.|
    |Get Vulnerability Response|Enable to collect Vulnerability Response data from ServiceNow. The default value is False.|
2. Click the **Save** button to save your settings.


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