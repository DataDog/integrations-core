# CrowdStrike FDR

## Overview

[CrowdStrike Falcon Data Replicator (FDR)][1] is a high-fidelity data export solution that enables organizations to securely stream raw endpoint telemetry in near real time. FDR delivers detailed event data through a data feed in JSON format using Amazon Web Services Simple Storage Service (Amazon S3) and Amazon Simple Queue Service (Amazon SQS).

Integrate CrowdStrike FDR with Datadog to gain insights into Authentication & Identity, Account & Privilege Changes, Execution Monitoring & Threat Detection, File & Malware Activity, and Network Behavior events using pre-built dashboard visualizations. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search, and detailed insights. Additionally, the integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Set up data replication from CrowdStrike FDR to a customer-owned S3 bucket

#### Setup a custom AWS S3 bucket
1. Sign in to the AWS Management Console and navigate to Amazon S3.
2. Provide the details as mentioned below:
   - **Bucket name**: Enter a Bucket name.
   - **AWS Region**: Choose a region.
      - You can only use your S3 bucket if you're using the US-1, US-2, or EU-1 CrowdStrike clouds.
      - Ensure that your bucket resides in the same AWS region as your Falcon CID.
        CrowdStrike terminology for cloud regions differs slightly from AWS, as shown in this table.
        | CrowdStrike region | AWS region   |
        |--------------------|--------------|
        | US-1               | us-west-1    |
        | US-2               | us-west-2    |
        | EU-1               | eu-central-1 |

        For example, if your Falcon CID resides in US-1, the bucket must reside in AWS's us-west-1 region.
3. Click **Create bucket**.
4. Once the bucket is created, click on the newly created bucket.
5. Go to the **Permissions** tab.
6. Click **Bucket policy** > **Edit**.
7. Replace the 2 occurrences of the **<bucket_name>** placeholder in the below policy statement with your own bucket's name and add it in the **Policy** section: 
    ```
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "Allow cs ls",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::292230061137:root"
          },
          "Action": [
            "s3:ListBucket",
            "s3:GetBucketLocation"
          ],
          "Resource": "arn:aws:s3:::<bucket_name>"
        },
        {
          "Sid": "allow cs all",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::292230061137:root"
          },
          "Action": "s3:*",
          "Resource": "arn:aws:s3:::<bucket_name>/*"
        }
      ]
    }
    ```
8. Copy the **Bucket ARN** of your S3 bucket.
9. Click **Save changes**.

#### Raise a support ticket in CrowdStrike
1. Log in to the **CrowdStrike Falcon** console with an account that has **Administrator** privileges.
2. Navigate to **Support and resources** > **Support portal**.
3. Select **Support** > **Cases**.
4. Click **Create Case**.
5. Provide `FDR to send data to a customer-owned S3 bucket` as a **Case Title**.
6. In the **Description** section of the support case, be sure to include the following details:
    - The Falcon Customer ID (CID)
    - Indicate the below type of events you wish to have provided in this new FDR feed.
      - primary events (All events found within the Events Data Dictionary)
    - The ARN of the custom S3 bucket copied in **Step-8** from `Setup Custom AWS S3 Bucket`
    - Confirmation that the bucket has been set up according to the specifications outlined
7. **Customer ID (CID)**: Provide Falcon Customer ID
8. **Preferred Working Time Zone**: Select any preferred timezone
9. **Product Area**: Select `API and Integrations`
10. **Product Topic**: Select `Falcon Data Replicator`
11. Click **Submit Case**.
12. Wait until CrowdStrike Support confirms that provisioning is complete.

## Configure Datadog Forwarder

Refer to the [Datadog Forwarder][2] documentation for detailed configuration guidance.
- During the Datadog Forwarder configuration, set the **source** as follows:
    - For **CloudFormation** deployments, set `DdSource` to `crowdstrike-fdr`.
    - For **Terraform** deployments, set `dd_source` to `crowdstrike-fdr`.
    - For **Manual** deployments, set the `DD_SOURCE` environment variable to `crowdstrike-fdr`.

## Data Collected

### Logs

| Format | Event Types |
| ------ | ----------- |
| JSON   | Primary Events |

### Metrics

The CrowdStrike FDR integration does not include any metrics.

### Events

The CrowdStrike FDR integration does not include any events.

## Support

For any further assistance, contact [Datadog support][3].

[1]: https://www.crowdstrike.com/en-us/resources/data-sheets/falcon-data-replicator/
[2]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=cloudformation
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/CrowdStrike/FDR