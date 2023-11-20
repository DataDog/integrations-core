# Agent Check: AWS IAM Access Analyzer

## Overview

Use AWS Identity and Access Management (IAM) Access Analyzer across your Amazon account to continuously analyze IAM permissions granted with any of your account policies. Datadog integrates with Amazon IAM Access Analyzer using a Lambda function that ships its findings as logs to Datadog.

## Setup

### Log collection

1. If you haven't already, set up the [Datadog Forwarder][1] Lambda function.

2. Create a new rule with type `Rule with an event pattern` in AWS EventBridge.

3. For the event source configuration, select `Other`. For `Creation method`, select `Custom pattern (JSON editor)`. For `Event pattern`, copy and paste the following JSON:

    ```json
    {
        "source": ["aws.access-analyzer"]
    }
    ```

4. Select `AWS service` to use as the target type. Select `Lambda function` as the target and select the Datadog Forwarder Lambda or enter the ARN.

5. Save your rule.

6. Once the AWS Access Analyzer runs and produces findings, the events will be picked up by the Datadog Lambda Forwarder tagged with `source:access-analyzer`. See the [Log Explorer][2] to start exploring your logs.

## Data Collected

### Metrics

This integration does not include any metrics.

### Service Checks

This integration does not include any service checks.

### Logs

This integration can be configured to send logs.

### Events

This integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: /logs/guide/forwarder/
[2]: https://app.datadoghq.com/logs?query=source%3Aaccess-analyzer
[3]: https://docs.datadoghq.com/help
