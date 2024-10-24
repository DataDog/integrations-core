# Agent Check: Vonage

[Vonage](https://www.vonage.com/) offers flexible and scalable voice, messaging, video, and data capabilities across unified communications, contact centers, and communications APIs. All the logs generated from voice, SMS, and dispatch APIs are available through the Reports API.

## Overview

This integration provides the following benefits:
1. **Centralized Data**: Combines SMS and voice call logs in one place for easier access and management.
2. **Enhanced analytics**: Enables analysis of communication patterns to inform business strategies.
3. **Trend identification**: Allows businesses to spot trends in customer interactions, aiding proactive engagement.
4. **Informed decision-making**: Provides insights that drive strategic decisions for growth and improvement.

## Setup

1. Log into [Vonage](https://www.vonage.com/log-in/).
2. Navigate to Vonage [dashboard](https://dashboard.nexmo.com/).
3. Here, you can obtain both the API key and API secret. 
4. Navigate to [Applications](https://dashboard.nexmo.com/applications).
5. Click on + Create a new Application to create a new application.
6. Enable the Messages Capabilities.
7. Enable the Voice Capabilities.
8. To make a call using the dashboard, Please refer to this [link](https://developer.vonage.com/en/voice/voice-api/getting-started?lang=using-dashboard).


### Configuration

Configure the Datadog endpoint to forward Vonage logs to Datadog.
1. Navigate to Vonage.
2. Add your Vonage credentials.

| Vonage Parameters | Description |
|----------|----------|
| API key | API Key of the Vonage account. |
| API secret | API Secret of the Vonage account. |


## Data Collected

### Logs

Logs are designed to collect and manage logs of SMS messages and voice calls. They capture essential details such as timestamps, sender and recipient information, message content, call duration, and call status.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/

