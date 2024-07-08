## Overview

[Cisco Secure Endpoint][1] is a single-agent solution that provides comprehensive protection, detection, response, and user access coverage to defend against threats to your endpoints. Using cutting-edge technology, it detects and neutralizes malicious activity in real-time, ensuring robust protection for your digital assets.

This integration ingests the following logs:
- Audit: Audit logs provide activities performed by user in Cisco Secure Endpoint console.
- Event: Event logs are essential for tracking security events, enabling quick detection, response, and analysis of potential threats.

The Cisco Secure Endpoint integration provides OOTB Dashboard visualizations to gain quick insights into the Cisco Secure Endpoint's audit  and event logs, thus enabling quick and necessary actions. Also, OOTB detection rules are designed to help users monitor and respond to potential security threats effectively.


## Setup

### Configuration

#### Get API Credentials for Cisco Secure Endpoint 


--> Refer the below Steps to create Client ID and API Key:
1. Log in to your Cisco Secure Endpoint Console. Click on the Left side Menu Panel.
2. Select `Administration`, Inside that select `Organization Settings`.
3. Click `Configure API Credentials` under `Features` section,  to generate the new API Credentials.
4. Click on the `New API Credentials` button located at the right side under section `Legacy API Credentials (version 0 and 1)`.
5. Add the below details in the pop-up:
    - Application Name: Any preferable name
    - Scope: Select `Read-only`
    - Click on `Create`.
    - Once you click on create, the redirected page will display the client ID(i.e: 3rd Party API client ID) and API Key values.
        - NOTE: Please make a note of the API Key, as it will only be displayed once.

#### Cisco Secure Endpoint DataDog Integration Configuration

Configure the Datadog endpoint to forward Cisco Secure Endpoint logs to Datadog.

1. Navigate to `Cisco Secure Endpoint`.
2. Add your Cisco Secure Endpoint credentials.

| Cisco Secure Endpoint Parameters | Description  |
| -------------------- | ------------ |
| API Host URL                |The API Host URL for Cisco Secure Endpoint Cloud is "https://api.\<region\>.apm.cisco.com". Adjust the "region" part based on the region of the Cisco Secure Endpoint server. If Cisco Secure Endpoint is hosted on VPC(Virtual Private Cloud), directly provide the API Host URL. |
| Client ID      | Client ID from Cisco Secure Endpoint.    |
| API Key           | API Key from Cisco Secure Endpoint.         |
| Get Endpoint Details    | Keep it "true" to collect endpoint metadata  for Cisco Secure Endpoint Event Logs, otherwise "false". |


## Data Collected

### Logs

The Cisco Secure Endpoint integration collects and forwards Cisco Secure Endpoint Audit and Event logs to Datadog.

### Metrics

The Cisco Secure Endpoint integration does not include any metrics.

### Events

The Cisco Secure Endpoint integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.cisco.com/site/in/en/products/security/endpoint-security/secure-endpoint/index.html
[2]: https://docs.datadoghq.com/help/