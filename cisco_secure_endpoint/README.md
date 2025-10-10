## Overview

[Cisco Secure Endpoint][1] is a single-agent solution that provides comprehensive protection, detection, response, and user access coverage to defend against threats to your endpoints. Cisco Secure Endpoint can detect and neutralize malicious activity in real time, ensuring robust protection of your digital assets.

This integration ingests the following logs:
- Audit: Audit logs provide activities performed by a user in the Cisco Secure Endpoint console.
- Event: Event logs are essential for tracking security events, enabling quick detection, response, and analysis of potential threats.

The Cisco Secure Endpoint integration provides out-of-the-box dashboards so you can gain insights into the Cisco Secure Endpoint's audit and event logs, enabling quick and necessary actions. Additionally, out-of-the-box detection rules are available to help you monitor and respond to potential security threats effectively.

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

### Generate API credentials in Cisco Secure Endpoint

1. Log in to your Cisco Secure Endpoint Console and navigate to the Menu Panel on the left side.
2. Select `Administration`, then select `Organization Settings`.
3. Click `Configure API Credentials` under the `Features` section to generate new API credentials.
4. Click on the `New API Credentials` button located at the right side under the `Legacy API Credentials (version 0 and 1)` section.
5. Add the following information in the pop-up modal:
    - Application Name: Any preferable name.
    - Scope: Select `Read-only`.
    - Click `Create`.
    - Once you click **Create**, the redirected page will display the client ID (like a third party API client ID) and API Key values.

### Connect your Cisco Secure Endpoint account to Datadog

1. Add your Cisco Secure Endpoint credentials.

    | Parameters | Description  |
    | ---------- | ------------ |
    | API Domain Name | The API domain name for Cisco Secure Endpoint Cloud is "api.\<region\>.amp.cisco.com". Adjust the "region" part based on the region of the Cisco Secure Endpoint server. If Cisco Secure Endpoint is hosted on VPC (Virtual Private Cloud), directly provide the API domain name. |
    | Client ID | Client ID from Cisco Secure Endpoint. |
    | API Key | API key from Cisco Secure Endpoint. |
    | Get Endpoint Details | Keep the default value of "true" to collect endpoint metadata for Cisco Secure Endpoint event logs. Otherwise, set this to "false". |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Cisco Secure Endpoint integration collects and forwards Cisco Secure Endpoint audit and event logs to Datadog.

### Metrics

The Cisco Secure Endpoint integration does not include any metrics.

### Events

The Cisco Secure Endpoint integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.cisco.com/site/in/en/products/security/endpoint-security/secure-endpoint/index.html
[2]: https://docs.datadoghq.com/help/