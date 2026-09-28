# CrowdStrike FDR

## Overview

[CrowdStrike Falcon Data Replicator (FDR)][1] is a paid add-on that streams raw Falcon endpoint telemetry to a CrowdStrike-managed Amazon S3 bucket, with file-availability notifications delivered over a CrowdStrike-managed Amazon SQS queue.

Integrate CrowdStrike FDR with Datadog to gain insights into Authentication & Identity, Account & Privilege Changes, Execution Monitoring & Threat Detection, File & Malware Activity, and Network Activity events using pre-built dashboard visualizations. See CrowdStrike's Events Data Dictionary for the full list of event types included in your FDR feed.

Send these logs to Datadog to search, monitor, and visualize this endpoint telemetry through out-of-the-box dashboards.

## Setup

### Enable the FDR add-on in CrowdStrike

FDR is a paid add-on and is not enabled by default.

1. Log in to the **CrowdStrike Falcon** console with an account that has **Administrator** privileges.
2. Navigate to **Support and resources** > **Support portal**.
3. Select **Support** > **Cases** > **Create Case**.
4. Set the **Product Area** to `API and Integrations` and the **Product Topic** to `Falcon Data Replicator`.
5. Provide your Falcon Customer ID (CID) and describe your request to enable the FDR add-on.
6. Submit the case and wait for CrowdStrike Support to confirm that FDR has been provisioned for your account.

### Create an FDR feed in the Falcon console

1. In the Falcon console, go to **Support and resources** > **Resources** > **Falcon data replicator**.
2. Create a new feed.
3. CrowdStrike generates the feed credentials:
   - An AWS Access Key ID
   - An AWS Secret Key
   - An SQS Queue URL

   These credentials are scoped by CrowdStrike to grant read-only access to your FDR queue and S3 bucket only. No AWS console configuration, IAM policy authoring, or cross-account role setup is required.

4. Copy the S3 path shown for the feed. It looks like `s3://cs-<name>-cannon-<id>-s3alias/<prefix>/`. Datadog needs only the bucket part: remove the leading `s3://` and everything from the next `/` onward. For the example above, enter `cs-<name>-cannon-<id>-s3alias`. Datadog checks that every file it downloads comes from this bucket.

### Connect your CrowdStrike FDR feed to Datadog

1. Add your AWS Access Key ID, AWS Secret Key, SQS Queue URL, and S3 bucket.

   | Parameter          | Description                                                                                                                                  |
   | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
   | AWS Access Key ID  | The AWS Access Key ID generated for your FDR feed.                                                                                           |
   | AWS Secret Key     | The AWS Secret Key generated for your FDR feed.                                                                                              |
   | SQS Queue URL      | The SQS Queue URL generated for your FDR feed, in the form `https://sqs.<region>.amazonaws.com/<account-id>/<queue-name>`. Datadog reads the AWS region from this URL. |
   | S3 Bucket          | The bucket name or access point alias from your feed's S3 path, without `s3://` or the trailing path. For example, `cs-<name>-cannon-<id>-s3alias`. |

2. Click **Save**.

When you save, Datadog checks only that each value has the right format. It does not test the credentials until it first polls the queue.

Datadog polls the queue every 5 minutes. For each file notification, it downloads and decompresses the referenced files and forwards the events to Datadog Logs. It deletes a notification from the queue only after Datadog Logs accepts every event in its files. If processing fails, the notification stays in the queue and Datadog retries it.

## Data Collected

### Logs

| Format         | Event Types                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| Gzipped NDJSON | Authentication & Identity, Account & Privilege Changes, Execution Monitoring & Threat Detection, File & Malware Activity, and Network Activity events. See CrowdStrike's Events Data Dictionary for the full list of event types. |

### Metrics

The CrowdStrike FDR integration does not include any metrics.

### Events

The CrowdStrike FDR integration does not include any events.

## Troubleshooting

### A value is rejected on save

The integration tile checks the format of the SQS Queue URL and S3 Bucket values. If either is rejected:

- For the S3 Bucket, remove the leading `s3://` and any path after the bucket name. Enter only a value such as `cs-<name>-cannon-<id>-s3alias`.
- For the SQS Queue URL, use the full `https://sqs.<region>.amazonaws.com/<account-id>/<queue-name>` URL from the Falcon console, not a queue ARN or queue name.
- Remove any leading or trailing whitespace.

### No logs are appearing in Datadog

Datadog first uses the credentials when it polls the queue, up to 5 minutes after you save. If no logs appear after that:

- Confirm the AWS Access Key ID, AWS Secret Key, and SQS Queue URL were copied exactly as generated by CrowdStrike.
- Confirm the S3 Bucket matches the bucket in the feed's S3 path. Datadog does not download files from any other bucket.
- Confirm the FDR feed is still active in the Falcon console and is generating new files.
- Confirm the FDR add-on has been provisioned for your CID. See [Enable the FDR add-on in CrowdStrike](#enable-the-fdr-add-on-in-crowdstrike).

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.crowdstrike.com/en-us/resources/data-sheets/falcon-data-replicator/
[2]: https://docs.datadoghq.com/help/
