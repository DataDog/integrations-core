# Jamf Pro

## Overview

[Jamf Pro][1] is an Apple device management tool that helps organizations deploy, configure, and secure Macs, iPhones, and iPads. It enables automated setup, app management, and compliance for Apple devices at scale.

Integrate Jamf Pro with Datadog to gain insights into [Events][2] using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

Jamf Cloud Premium customers can also send the Jamf Pro Access log (sign-in attempts) and Change Management log (changes made by administrators, API clients, and Jamf Pro itself) to Datadog with [Jamf Log Stream][4]. These logs are searchable in Datadog. The integration's log pipeline doesn't parse them.

## Setup

### Webhook Configuration

Configure the Datadog endpoint to forward Jamf Pro detections as logs to Datadog.

1. {{< integration-api-key-picker >}}
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

The webhook URL generated in step 1 sends logs to the intake for your Datadog site, so these steps work on every Datadog site, including EU sites.

**Note**: Jamf Pro sends a check-in event every time a device checks in, which is 96 events per device per day at the default 15-minute check-in frequency. To control indexing costs, use [exclusion filters][5].

### Jamf Log Stream Configuration

Jamf Log Stream is available only for Jamf Cloud Premium, not for self-hosted Jamf Pro. Jamf Support enables it on your Jamf Cloud instance. Keep the Jamf Cloud logging time zone set to Coordinated Universal Time (UTC), the default, so that Datadog reads the log timestamps correctly.

Choose one of the following destinations. Amazon S3 with the Datadog Forwarder is the documented route. The Datadog destination is managed by Jamf: Jamf doesn't publish which Datadog sites it supports, which log source it sets, or how it batches logs.

#### Amazon S3 Destination

1. Create an Amazon S3 bucket for the logs.
2. Contact Jamf Support and ask them to stream the Access log and the Change Management log to your bucket. Provide the bucket name.
3. After Jamf Support confirms that streaming is enabled, add the bucket policy from [Jamf's instructions][6] to the bucket. If the bucket uses AWS Key Management Service (AWS KMS) encryption, also add Jamf's role to the key policy.
4. Install the [Datadog Forwarder][7] in the bucket's AWS account and region. Use a Forwarder that only forwards this bucket, because the source setting applies to every log the Forwarder sends. Set:
   - The source to `jamf-pro`: **DdSource** for CloudFormation, or `DD_SOURCE` for a manual deployment.
   - The multiline pattern to `\[(JSSACCESSLOG|CHANGEMANAGEMENT)\]`, so that each Change Management entry stays one log with its detail lines: **DdMultilineLogRegexPattern** for CloudFormation, or `DD_MULTILINE_LOG_REGEX_PATTERN` for a manual deployment.

   If you deploy the Forwarder with Terraform, check the Datadog Forwarder Terraform module's documentation for how to set the source and the multiline pattern.
5. [Add a trigger][8] on the bucket to the Forwarder.

#### Datadog Destination

1. [Create a Datadog API key][9], or use an existing one.
2. Contact Jamf Support and ask them to stream the Access log and the Change Management log to Datadog. Provide your API key and the logs intake host for your [Datadog site][10], such as `http-intake.logs.datadoghq.eu` for EU1. Ask Jamf Support which form of the host it needs.
3. Ask Jamf Support to confirm that the Datadog destination supports your Datadog site. If it doesn't, use the Amazon S3 destination.

### Validation

1. After a device checks in, search for `source:jamf-pro` in the [Log Explorer][11]. Webhook events arrive within a minute.
2. After someone signs in to Jamf Pro, search for `source:jamf-pro JSSACCESSLOG`. Logs arrive within about 20 minutes with the Amazon S3 destination, and within a few minutes with the Datadog destination. If logs from the S3 bucket don't arrive, or arrive unreadable, contact [Datadog support][3].
3. If logs from the Datadog destination don't appear under `source:jamf-pro`, search for `JSSACCESSLOG` without the source filter and give the source you find to [Datadog support][3].

### Monitor Log Delivery

To be alerted when Jamf stops sending logs, create [log monitors][12]:

- On `source:jamf-pro`, alerting when no logs arrive for 1 hour.
- On `source:jamf-pro JSSACCESSLOG`, alerting when no logs arrive for 24 hours. Use this monitor only with the Amazon S3 destination, or after validation step 2 shows Datadog destination logs under `source:jamf-pro`, and only if someone signs in to Jamf Pro or an API client requests a token at least once a day.

## Data Collected

### Logs

| Format | Event Types |
| ------ | ----------- |
| JSON   | Computer Added, Computer Check-In, Computer Inventory Completed, Computer Patch Policy Completed, Computer Policy Finished, Computer Push Capability Changed, Device Added To DEP, JSS Shutdown, JSS Startup, Mobile Device Check-In, Mobile Device Command Completed, Mobile Device Enrolled, Mobile Device Inventory Completed, Mobile Device Push Sent, Mobile Device Unenrolled, Patch Software Title Updated, Push Sent, Rest API Operation, SCEP Challenge, Smart Group Computer Membership Change, Smart Group Mobile Device Membership Change, Smart Group User Membership Change |
| Text   | Access log, Change Management log (Jamf Log Stream) |

### Metrics

The Jamf Pro integration does not include any metrics.

### Service Checks

The Jamf Pro integration does not include any service checks.

### Events

The Jamf Pro integration does not include any events.

## Support

For any further assistance, contact [Datadog support][3].

[1]: https://www.jamf.com/products/jamf-pro/
[2]: https://developer.jamf.com/jamf-pro/docs/webhooks-1
[3]: https://docs.datadoghq.com/help/
[4]: https://developer.jamf.com/jamf-pro/docs/jamf-log-stream
[5]: /logs/pipelines/indexes
[6]: https://learn.jamf.com/r/en-US/technical-articles/Jamf_Cloud_Overview_and_FAQ
[7]: https://docs.datadoghq.com/logs/guide/forwarder/
[8]: https://docs.datadoghq.com/logs/guide/send-aws-services-logs-with-the-datadog-lambda-function/
[9]: /organization-settings/api-keys
[10]: https://docs.datadoghq.com/getting_started/site/
[11]: /logs?query=source%3Ajamf-pro
[12]: /monitors/create/log
