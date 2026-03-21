# BlueCat Integrity

## Overview

[BlueCat Integrity][1] is a centralized DDI platform that automates and secures enterprise network infrastructure management.

Integrate BlueCat Integrity with Datadog's pre-built dashboard visualizations to gain insights into DNS and DHCP activity events. With Datadog's built-in log pipelines, you can parse and enrich these logs to facilitate easy search and detailed insights. Additionally, this integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Configuration

#### Webhook Configuration

Configure the Datadog endpoint to forward BlueCat Integrity DHCP activity events as logs to Datadog.

1. Copy the generated URL inside the **Configuration** tab on the Datadog [BlueCat Integrity][2] tile.
2. Sign in to BlueCat Integrity Portal.
3. Click the **Servers** tab in the sidebar, then choose **Servers**.
4. From the list, click the name of the server to configure the log collection.
5. Open the **Services** tab.
6. Under **Monitoring and analytics**, locate the **DHCP activity service** panel and click **Edit service**.
7. Under **General**, set the following parameters:
   - **Enabled**: Select this check box to enable DHCP activity service.
   - **DHCPv4 enabled**: Select this check box to collect DHCPv4 activity events.
   - **DHCPv6 enabled**: Select this check box to collect DHCPv6 activity events.
8. On the **Destination tab**, set the following parameters:
   - **Sink type**: Select HTTP.
   - On selecting HTTP, the following fields appear:
      - Output URI: Enter the webhook URL generated in step 1.
9. On the **Certificate** tab, under CA certificate, export the public SSL certificate for *.datadoghq.com from your browser's certificate viewer (the certificate presented when accessing Datadog over HTTPS) and upload it here.
10. Click **Save**.
11. Perform steps 5-10 on every server from which logs need to be collected.


Configure the Datadog endpoint to forward BlueCat Integrity DNS activity events as logs to Datadog.

1. Copy the generated URL inside the **Configuration** tab on the Datadog [BlueCat Integrity][2] tile.
2. Sign in to BlueCat Integrity Portal.
3. Click the **Servers** tab in the sidebar, then choose **Servers**.
4. From the list, click the name of the server to configure the log collection.
5. Open the **Services** tab.
6. Under **Monitoring and analytics**, locate the **DNS activity service** panel and click **Edit service**.
7. Under **General**, set the following parameters:
   - **Enabled**: Select this check box to enable the service.
8. On the **Destination tab**, set the following parameters:
   - **Sink type**: Select HTTP
   - On selecting HTTP, the following fields appear:
      - **Output URI**: Enter the webhook URL generated in step 1.
9. On the **Certificate** tab, under CA certificate, export the public SSL certificate for *.datadoghq.com from your browser's certificate viewer (the certificate presented when accessing Datadog over HTTPS) and upload it here.
10. Click **Save**.
11. Perform steps 5-10 on every server from which logs need to be collected.


## Data Collected

### Logs

The BlueCat Integrity integration collects DHCP and DNS activity events.

### Metrics

The BlueCat Integrity integration does not include any metrics.

### Events

The BlueCat Integrity integration does not include any events.

## Support

For further assistance, contact [Datadog support][3].

[1]: https://bluecatnetworks.com/products/integrity/
[2]: /integrations/bluecat-integrity
[3]: https://docs.datadoghq.com/help/