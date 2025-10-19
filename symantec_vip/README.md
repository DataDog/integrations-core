# Symantec VIP

## Overview

[Symantec VIP][1] (Validation and ID Protection Service) is a cloud-based authentication service that helps enterprises secure access to networks and applications while maintaining productivity.

This integration ingests the following logs:

- Event: Represents user management operations such as user creation, password setting, user group management, and batch operations, including transaction details and result statuses.

This integration seamlessly collects all the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into event logs through the out-of-the-box dashboards.

**Minimum Agent version:** 7.70.0

## Setup

### Generate API credentials in Symantec VIP

**Obtaining VIP certificate**:  
Follow the steps in the official documentation: [Obtaining VIP certificate.][2]

**Activating the VIP Report Streaming Service using VIP Certificate**:
- Before integrating the VIP Report Streaming Service, you must enable the service with Symantec. Contact your Symantec representative to enable the service. Once the service is enabled, activate the VIP Report Streaming Service for your VIP account using the activate API.
- Follow the steps mentioned in the official documentation to activate API: [Activate VIP Report Streaming Service][3]

**Jurisdiction hash**:  
The jurisdiction hash of the user account is available on the **Account Information** tab of the **Account** page in VIP Manager.

### Connect your Symantec VIP Account to Datadog

1. Add your Symantec VIP credentials.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | Jurisdiction Hash                     | Jurisdiction hash of your account.                           |
    | VIP Cert Pem File Content             | Content of VIP Certificate (.pem) file that will be used to connect to streaming endpoint                         |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Symantec VIP integration collects and forwards event logs to Datadog.

### Metrics

The Symantec VIP integration does not include any metrics.

### Service Checks

The Symantec VIP integration does not include any service checks.

### Events

The Symantec VIP integration does not include any events.

## Support

Need help? Contact [Datadog support][4].

[1]: https://vip.symantec.com/
[2]: https://techdocs.broadcom.com/us/en/symantec-security-software/identity-security/vip/cloud/vip-web-services-and-apis-v127046027-d2278e2328/VIP-Reporting-Streaming-Service/about-the-api-v109910792-d2376e278/obtaining-the-certificate-v109910553-d2376e636.html#v109910553
[3]: https://techdocs.broadcom.com/us/en/symantec-security-software/identity-security/vip/cloud/vip-web-services-and-apis-v127046027-d2278e2328/VIP-Reporting-Streaming-Service/about-the-api-v109910792-d2376e278/activating-the-v133376930-d2376e309.html
[4]: https://docs.datadoghq.com/help/
