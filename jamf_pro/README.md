# Jamf Pro

## Overview

[Jamf Pro][1] is an Apple device management tool that helps organizations deploy, configure, and secure Macs, iPhones, and iPads. It enables automated setup, app management, and compliance for Apple devices at scale.

Integrate Jamf Pro with Datadog to gain insights into [Events][2] using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.68.1

## Setup

### Configuration

#### Webhook Configuration

Configure the Datadog endpoint to forward Jamf Pro detections as logs to Datadog.

1. Copy the generated URL inside the **Configuration** tab on the Datadog [Jamf Pro][3] tile.
2. In Jamf Pro, click **Settings** in the sidebar.
3. In the **Global** section, click **Webhooks**.
4. Click **New**.
5. Enter a display name for the webhook.
6. Enter a URL for the webhook generated in the above section.
7. Choose **None** from the Authentication Type dropdown.
8. Enter the connection timeout for the webhook.
9. Enter the read timeout for the webhook.
10. Choose **JSON** in Content Type.
11. Choose the event that will trigger the webhook in the Webhook Event dropdown.
12. Click **Save**.
13. Ensure that steps 3-11 are repeated for each of the 22 event types, to ensure complete data collection coverage.

## Data Collected

### Logs

| Format | Event Types |
| ------ | ----------- |
| JSON   | Computer Added, Computer Check-In, Computer Inventory Completed, Computer Patch Policy Completed, Computer Policy Finished, Computer Push Capability Changed, Device Added To DEP, JSS Shutdown, JSS Startup, Mobile Device Check-In, Mobile Device Command Completed, Mobile Device Enrolled, Mobile Device Inventory Completed, Mobile Device Push Sent, Mobile Device Unenrolled, Patch Software Title Updated, Push Sent, Rest API Operation, SCEP Challenge, Smart Group Computer Membership Change, Smart Group Mobile Device Membership Change, Smart Group User Membership Change |

### Metrics

The Jamf Pro integration does not include any metrics.

### Events

The Jamf Pro integration does not include any events.

## Support

For any further assistance, contact [Datadog support][4].

[1]: https://www.jamf.com/products/jamf-pro/
[2]: https://developer.jamf.com/jamf-pro/docs/webhooks-1
[3]: /integrations/jamf-pro
[4]: https://docs.datadoghq.com/help/
