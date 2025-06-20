## Overview

[Carbon Black Cloud][1] is a software-as-a-service (SaaS) solution that provides next-generation anti-virus (NGAV), endpoint detection and response (EDR), advanced threat hunting, and vulnerability management within a single console using a single sensor. 

Integrate Carbon Black Cloud with Datadog to gain insights into Alerts, Auth Events, Endpoint Events and Watchlist Hits using pre-built dashboard visualizations. Additionally, integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Configure AWS S3 Bucket

- Please refer the [Use AWS S3 guide][2].

### Configure Datadog Forwarder

- Please refer the [Datadog Forwarder][3]

### Configure Carbon Black Cloud Data Forwarder

1. Login to **Carbon Black Cloud console** as a Super Admin privileges.
2. On the left navigation pane, click **Settings > Data Forwarders**.
3. Click **Add Forwarder**.
4. Enter a unique name for the Data Forwarder.
5. Select a **Type** from the dropdown list.
6. Select an **AWS S3** option from the provider dropdown list.
7. Enter the **S3 bucket** name you have created on AWS.
8. For the **S3 prefix**, please use the base prefix **carbon-black-cloud** for all types. The following specific prefixes should be applied according to the type:
    1. For **Alert** type, use the prefix: `carbon-black-cloud-alerts`
    2. For **Auth event** type, use the prefix: `carbon-black-cloud-auth-events`
    3. For **Endpoint event** types, use the prefix: `carbon-black-cloud-endpoint-events`
    4. For **Watchlist Hit** type, use the prefix: `carbon-black-cloud-watchlist-hits`
8. Set the **forwarder status** to `On`.
9. To apply the changes, click **Save**.

## Data Collected

### Logs

The Carbon Black Cloud integration collects `Alert`, `Auth event`, `Endpoint event`, and `Watchlist hit` logs.

### Metrics

The Carbon Black Cloud integration does not include any metrics.

### Events

The Carbon Black Cloud integration does not include any events.

## Support

For any further assistance, contact [Datadog support][4].


[1]: https://www.broadcom.com/products/carbon-black/threat-prevention/carbon-black-cloud
[2]: https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/data-forwarder/quick-setup/#option-1-use-aws-s3
[3]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=cloudformation
[4]: https://docs.datadoghq.com/help/
