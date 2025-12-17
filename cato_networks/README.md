## Overview

[Cato Networks][1] provides a single-vendor Secure Access Service Edge (SASE) platform that converges SD-WAN, global private networking, and a full network security stack into a cloud-based service.

This integration ingests the following logs:

- **Audit Logs**: This logs provide detailed information on admin actions performed within the system.
- **Events**: This logs provide detailed insights into security, detection and response, connectivity, and system events within the Cato Networks platform.

Integrate Cato Networks with Datadog to gain insights into audit logs and events using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Audit Log Collection

#### Obtaining Client Credentials
1. Log in to Cato Networks platform and navigate to **Resources** > **Service API Keys**.
2. In the **Service API Keys** tab, click **New** and provide the following details:
    - Select the **Service Principal**.
    - Enter the **Key Name**.
    - Set the **API Permission** as **Downgrade to View**.
    - Set **Any IP** under the **Allow access from IPs** section.
3. Click **Apply** button and copy the **Token**.
4. Navigate to **Account** > **Account Info** and copy the **Account ID**.
5. Identify your Cato Networks Region by checking the prefix of your URL: 
    - cc.us1.catonetworks.com - us1 
    - cc.catonetworks.com - Keep region as empty

#### Connect your Cato Networks Account to Datadog

1. Add your `Cato Account ID`, `API Token` and `Region`.
   | Parameters | Description |
   | ---------- | ---------------------------------------------- |
   | Cato Account ID | The account ID from your Cato Networks platform URL |
   | API Token | The API Token of your Cato Networks platform |
   | Region | The prefix from your Cato Networks platform URL |
2. Click **Save**.


### Event Log collection

#### Configure AWS S3 Bucket
**Note**: Please use **cato-networks** as the **S3 prefix**.  
Please refer the [Configuring the AWS S3 Bucket][2] 

#### Configure Event Integration in CATO Network
Please refer the [Adding Amazon S3 Integration for Events][3]

#### Configure Datadog Forwarder
Please refer the [Datadog Forwarder][4]


## Data Collected

### Logs

The Cato Networks integration collects and forwards audit logs and events to Datadog.

### Metrics

The Cato Networks integration does not include any metrics.

### Events

The Cato Networks integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.catonetworks.com/
[2]: https://support.catonetworks.com/hc/en-us/articles/9726441847965-Integrating-Cato-Events-with-AWS-S3#h_01K06PD8YPXBZJH5P0BP625BB1
[3]: https://support.catonetworks.com/hc/en-us/articles/9726441847965-Integrating-Cato-Events-with-AWS-S3#h_01K06PD8YP6JCM5618J4YYDFAS
[4]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=cloudformation
[5]: https://docs.datadoghq.com/help/
