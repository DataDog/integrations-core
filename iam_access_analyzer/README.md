# Agent Check: AWS IAM Access Analyzer

## Overview

Use AWS Identity and Access Management (IAM) Access Analyzer across your Amazon account to continuously analyze IAM permissions granted with any of your account policies. Datadog integrates with Amazon IAM Access Analyzer using a Lambda function that ships its logs to Datadog.

## Setup

### Log collection

1. If you haven't already, set up the [Datadog Forwarder][1] Lambda function.

2. Create a new rule in AWS EventBridge.

3. Define a custom event pattern with the following:

    ```json
    {
        "source": ["aws.access-analyzer"]
    }
    ```

4. Select an event bus and define the Datadog Lambda function as the target.

5. Save your rule.

6. See the [Log Explorer][2] to start exploring your logs.

## Data Collected

### Metrics

This integration does not not collect metrics 

### Service Checks

This integration does not include any service checks.

### Logs

This integration can be configured to send Logs.

### Events

This integration does not send events

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: /logs/guide/forwarder/
[2]: https://app.datadoghq.com/logs
[3]: https://docs.datadoghq.com/help
