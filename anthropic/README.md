# Anthropic

## Overview

Use the Anthropic integration to monitor, troubleshoot, and evaluate your LLM-powered applications, such as chatbots or data extraction tools, using Anthropic's models.

If you are building LLM applications, use LLM Observability to investigate the root cause of issues,
monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

See the [LLM Observability tracing view video](https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max) for an example of how you can investigate a trace.

**Minimum Agent version:** 7.59.1

## Setup

# Configuring Anthropic LLM Evaluations for Datadog

## Overview

Datadog's LLM Observability enables end-to-end monitoring of your LLM application using Anthropic models. Follow the steps below to configure your Anthropic integration for LLM Evaluations.

## Prerequisites

- An **Anthropic account** with access to model deployments.
- A **valid Anthropic API key** with **write permissions** for model capabilities.

**Minimum Agent version:** 7.59.1

## Setup

### 1. Generate an Anthropic API key

1. Login to your [Anthropic dashboard][3].
2. Navigate to **API keys** under your profile.
3. Click the **Create Key** button.
   - For LLM Observability, ensure that the API key has **write** permission for **model capabilities**. This allows Datadog to invoke models in your Anthropic account.
4. Copy the created API key to your clipboard.

### 2. Configure Datadog's Anthropic integration

1. Navigate to the configuration tab inside Datadog's Anthropic integration tile.
2. On the **Configure** tab, click **Add New**.
3. Under **Name**, enter a name for your account. Under **API key**, enter your Anthropic API key.
4. Click the check mark to save.


### Additional Notes

- This integration allows LLM Observability to track Anthropic model performance.
- No additional permissions are required beyond enabling write access for model capabilities.

## Additional Resources

- [Anthropic API Documentation][4]


### LLM Observability: Get end-to-end visibility into your LLM application using Anthropic

You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

#### Installation for Python

##### If you do not have the Datadog Agent:

1. Install the `ddtrace` package:

```shell
  pip install ddtrace
```

2.  Start your application using the following command to enable Agentless mode:

```shell
  DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
```

##### If you already have the Datadog Agent installed:

1. Make sure the Agent is running and that APM and StatsD are enabled. For example, use the following command with Docker:

```shell
docker run -d \
  --cgroupns host \
  --pid host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -e DD_API_KEY=<DATADOG_API_KEY> \
  -p 127.0.0.1:8126:8126/tcp \
  -p 127.0.0.1:8125:8125/udp \
  -e DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true \
  -e DD_APM_ENABLED=true \
  gcr.io/datadoghq/agent:latest
```

2. If you haven't already, install the `ddtrace` package:

```shell
  pip install ddtrace
```

3. To automatically enable tracing, start your application using the `ddtrace-run` command:

```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <your_app>.py
```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

##### If you are running LLM Observability in a serverless environment (AWS Lambda):

1. Install the **Datadog-Python** and **Datadog-Extension** Lambda layers as part of your AWS Lambda setup.
2. Enable LLM Observability by setting the following environment variables:

```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
```

**Note**: In serverless environments, Datadog automatically flushes spans at the end of the Lambda function.

##### Automatic Anthropic tracing

The Anthropic integration allows for automatic tracing of chat message calls made by the Anthropic Python SDK, capturing latency, errors, input/output messages, and token usage during Anthropic operations.

The following methods are traced for both synchronous and asynchronous Anthropic operations:

- Chat messages (including streamed calls): `Anthropic().messages.create()`, `AsyncAnthropic().messages.create()`
- Streamed chat messages: `Anthropic().messages.stream()`, `AsyncAnthropic().messages.stream()`

No additional setup is required for these methods.

##### Validation

Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `dd-trace` integration:

```shell
ddtrace-run --info
```

Look for the following message to confirm the setup:

```shell
Agent error: None
```

##### Debugging

If you encounter issues during setup, enable debug logging by passing the `--debug` flag:

```shell
ddtrace-run --debug
```

This displays any errors related to data transmission or instrumentation, including issues with Anthropic traces.

## Data Collected

### Metrics

The Anthropic integration does not include any custom metrics.

### Service Checks

The Anthropic integration does not include any service checks.

### Events

The Anthropic integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/integrations/anthropic/
[2]: https://docs.datadoghq.com/help/
[3]: https://console.anthropic.com/login?selectAccount=true&returnTo=%2Fdashboard%3F
[4]: https://docs.anthropic.com/
