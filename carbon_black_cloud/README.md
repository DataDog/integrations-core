## Overview

[Carbon Black Cloud][1] is a cloud-native endpoint protection platform (EPP) that provides what you need to secure your endpoints using a single, lightweight agent and an easy-to-use console.

Integrate Carbon Black Cloud with Datadog to gain insights into Alerts, Audit Logs, Auth Events, Endpoint Events and Watchlist Hits using pre-built dashboard visualizations. Additionally, integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Configure AWS S3 Bucket

- Please refer the [Use AWS S3 guide][2].

### Configure Datadog Forwarder

Refer to the [Datadog Forwarder][3] documentation for detailed configuration guidance.
- During the Datadog Forwarder configuration, set the **source** as follows:
    - For **CloudFormation** deployments, set **DdSource** to **carbon-black-cloud**.
    - For **Terraform** deployments, set **dd_source** to **carbon-black-cloud**.
    - For **Manual** deployments, set the **DD_SOURCE** environment variable to **carbon-black-cloud**.

### Configure Carbon Black Cloud Data Forwarder

1. Login to **Carbon Black Cloud console** as a Super Admin privileges.
2. On the left navigation pane, click **Settings > Data Forwarders**.
3. Click **Add Forwarder**.
4. Enter a unique name for the Data Forwarder.
5. Select a **Type** from the dropdown list.
6. Select an **AWS S3** option from the provider dropdown list.
7. Enter the **S3 bucket** name you have created on AWS.
8. Set the **forwarder status** to `On`.
9. Enter any S3 prefix of your choice.
10. To apply the changes, click **Save**.

## Data Collected

### Logs

The Carbon Black Cloud integration collects `Alert`, `Audit log`, `Auth event`, `Endpoint event`, and `Watchlist hit` logs.

### Metrics

The Carbon Black Cloud integration does not include any metrics.

### Events

The Carbon Black Cloud integration does not include any events.

## Support

For any further assistance, contact [Datadog support][4].


[1]: https://www.broadcom.com/products/carbon-black/threat-prevention/carbon-black-cloud
[2]: https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/data-forwarder/quick-setup/#option-1-use-aws-s3
[3]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=manual
[4]: https://docs.datadoghq.com/help/
