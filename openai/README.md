# OpenAI

## Overview

Monitor, troubleshoot, and evaluate your LLM-powered applications, such as chatbots or data extraction tools, using [OpenAI][1]. With LLM Observability, you can investigate the root cause of issues, monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

[LLM Obs tracing view video][16]

Get cost estimation, prompt and completion sampling, error tracking, performance metrics, and more out of [OpenAI][1] account-level, Python, Node.js, and PHP library requests using Datadog metrics and APM.

## Setup

<!-- xxx tabs xxx -->
<!-- xxx tab "API Key" xxx -->

**IMPORTANT**: An **admin-scoped API key** is **required** to collect usage metrics and Cloud Cost Management (CCM) data. Without an admin-scoped API key, this integration cannot ingest `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics, and CCM cost data are not available.

**Note**: To collect all metrics provided by this integration, also follow the APM setup instructions in addition to the API key setup.

### Installation

# Configuring OpenAI Integration for Datadog

## Overview

Datadog's OpenAI integration allows you to collect usage metrics, cost data, and enables [LLM Observability][19] to monitor your OpenAI models. Follow the steps below to generate an OpenAI API key and configure the integration.

## Prerequisites

- An **OpenAI account** with admin write permissions
- A **valid OpenAI API key**:
  - **For Cloud Cost Management (CCM) and usage metrics**: An **admin-scoped API key is mandatory**. Project-scoped keys cannot collect this data.
  - **For LLM Observability only**: A standard API key with write permissions for model capabilities is sufficient.

## Setup

### 1. Generate an OpenAI API key

**For Cloud Cost Management and usage metrics**, you must create an **admin-scoped API key**:

1. Log in to your [OpenAI Account][10].
2. Navigate to the [Admin Keys page][20] or go to **API keys** under **Organization settings** and select the **Admin keys** tab.
3. Click **Create a new secret key**.
4. Copy the created admin API Key to your clipboard.

**For LLM Observability only** (without CCM and usage metrics), you can use a standard API key:

1. Log in to your [OpenAI Account][10].
2. Navigate to **API keys** under **Organization settings**.
3. Click **Create a new secret key**.
   - Ensure that the API key has **write** permission for **model capabilities** to invoke models in your LLM account.
4. Copy the created API Key to your clipboard.

### 2. Configure Datadog's OpenAI integration

1. Navigate Datadog's [OpenAI integration tile][11] and open the **Configuration** tab.
2. Click **Add Account**.
3. Under **Account Name**, enter a name for your account. Under **API Key**, enter your OpenAI API key (**must be admin-scoped for CCM and usage metrics**). Optionally, add a comma-separated list of tags for metrics associated with this account.
3. Under **Resources**, enable toggles depending on your use case:
   - **Collect Cost Data**: If enabled, cost data is visible in [Cloud Cost Management][14] within 24 hours. **Requires an admin-scoped API key.** See ([collected data][15]).
   - **Use this API key to evaluate your LLM applications**: If enabled, evaluations are run through this API key in LLM Observability.

### Additional Notes

- **Admin-scoped API key requirement**: An admin-scoped API key is **mandatory** for collecting usage metrics and Cloud Cost Management data. This integration only collects `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics when an admin-scoped API key is provided.
- If you enable Cloud Cost Management for OpenAI without an admin-scoped API key, cost metrics are not available.

## Additional Resources

- [OpenAI API Documentation][17]
- [Generating an API Token][18]


<!-- NOTE: This section is overwritten by the OpenAI configuration component exported in -->
<!-- web-ui. Make sure to update the markdown / code there to see any changes take -->
<!-- effect on the tile. -->

<!-- xxz tab xxx -->
<!-- xxx tab "Python" xxx -->

**Note**: This setup method does not collect `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics. To collect these metrics, also follow the API key setup instructions.

### Installation

#### LLM Observability: Get end-to-end visibility into your LLM application's calls to OpenAI

You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

##### If you do not have the Datadog Agent:

1. Install the `ddtrace` package:

   ```shell
     pip install ddtrace
   ```

2. Start your application with the following command, enabling agentless mode:

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

2. Install the `ddtrace` package if it isn't installed yet:

   ```shell
     pip install ddtrace
   ```

3. Start your application using the `ddtrace-run` command to automatically enable tracing:

   ```shell
      DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
   ```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

##### If you are running LLM Observability in a serverless environment (AWS Lambda):

1. Install the **Datadog-Python** and **Datadog-Extension** Lambda layers as part of your AWS Lambda setup.
2. Enable LLM Observability by setting the following environment variables:

   ```shell
      DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
   ```

**Note**: In serverless environments, Datadog automatically flushes spans when the Lambda function finishes running.

##### Automatic OpenAI tracing

LLM Observability provides automatic tracing for OpenAI's completion and chat completion methods without requiring manual instrumentation.

The SDK will automatically trace the following OpenAI methods:

- `OpenAI().completions.create()`, `OpenAI().chat.completions.create()`
- For async calls: `AsyncOpenAI().completions.create()`, `AsyncOpenAI().chat.completions.create()`

No additional setup is required to capture latency, input/output messages, and token usage for these traced calls.

##### Validation

Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `ddtrace` integration:

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

This will display detailed information about any errors or issues with tracing.

#### APM: Get Usage Metrics for Python Applications

1. Enable APM and StatsD in your Datadog Agent. For example, in Docker:

   ```shell
   docker run -d
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

2. Install the Datadog APM Python library.

   ```shell
   pip install ddtrace
   ```

3. Prefix your OpenAI Python application command with `ddtrace-run` and the following environment variables as shown below:

   ```shell
   DD_SERVICE="my-service" DD_ENV="staging" ddtrace-run python <your-app>.py
   ```

**Notes**:

<!-- partial
{{% site-region region="us3,us5,eu,gov,ap1" %}}
- Non-US1 customers must set `DD_SITE` on the application command to the correct Datadog site parameter as specified in the table in the <a href="https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site">Datadog Site</a> page (for example, `datadoghq.eu` for EU1 customers).{{% /site-region %}}
partial -->

- If the Agent is using a non-default hostname or port, be sure to also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM Python library documentation][2] for more advanced usage.

##### Configuration

See the [APM Python library documentation][3] for all the available configuration options.

##### Validation

Validate that the APM Python library can communicate with your Agent using:

```shell
ddtrace-run --info
```

You should see the following output:

```
    Agent error: None
```

##### Debug Logging

Pass the `--debug` flag to `ddtrace-run` to enable debug logging.

```shell
ddtrace-run --debug
```

This displays any errors sending data:

```
ERROR:ddtrace.internal.writer.writer:failed to send, dropping 1 traces to intake at http://localhost:8126/v0.5/traces after 3 retries ([Errno 61] Connection refused)
```

<!-- xxz tab xxx -->
<!-- xxx tab "Node.js" xxx -->

**Note**: This setup method does not collect `openai.api.usage.*` metrics. To collect these metrics, also follow the API key setup instructions.

### Installation

#### LLM Observability: Get end-to-end visibility into your LLM application's calls to OpenAI

You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

##### If you do not have the Datadog Agent:

1. Install the `dd-trace` package:

   ```shell
     npm install dd-trace
   ```

2. Start your application with the following command, enabling agentless mode:

   ```shell
     DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> node -r 'dd-trace/init' <your_app>.js
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

2. Install the Datadog APM Python library.

   ```shell
   npm install dd-trace
   ```

3. Start your application using the `-r dd-trace/init` or `NODE_OPTIONS='--require dd-trace/init'` command to automatically enable tracing:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> node -r 'dd-trace/init' <your_app>.js
   ```

**Note**: If the Agent is running on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

##### If you are running LLM Observability in a serverless environment (AWS Lambda):

1. Enable LLM Observability by setting the following environment variables:

   ```shell
   DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME>
   ```

2. Before the lambda finishes, call `llmobs.flush()`:

   ```js
   const llmobs = require('dd-trace').llmobs;
   // or, if dd-trace was not initialized via NODE_OPTIONS
   const llmobs = require('dd-trace').init({
     llmobs: {
       mlApp: <YOUR_ML_APP>,
     }
   }).llmobs; // with DD_API_KEY and DD_SITE being set at the environment level

   async function handler (event, context) {
     ...
     llmobs.flush()
     return ...
   }
   ```

##### Automatic OpenAI tracing

LLM Observability provides automatic tracing for OpenAI's completion, chat completion, and embedding methods without requiring manual instrumentation.

The SDK will automatically trace the following OpenAI methods:

- `client.completions.create()`, `client.chat.completions.create()`, `client.embeddings.create()` (where client is an instance of `OpenAI`)

No additional setup is required to capture latency, input/output messages, and token usage for these traced calls.

##### Debugging

If you encounter issues during setup, enable debug logging by setting `DD_TRACE_DEBUG=1`

This will display detailed information about any errors or issues with tracing.

#### APM: Get Usage Metrics for Node.js Applications

1. Enable APM and StatsD in your Datadog Agent. For example, in Docker:

   ```shell
   docker run -d
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

2. Install the Datadog APM Node.js library.

   ```shell
   npm install dd-trace
   ```

3. Inject the library into your OpenAI Node.js application.

   ```shell
   DD_TRACE_DEBUG=1 DD_TRACE_BEAUTIFUL_LOGS=1 DD_SERVICE="my-service" \
     DD_ENV="staging" DD_API_KEY=<DATADOG_API_KEY> \
     NODE_OPTIONS='-r dd-trace/init' node app.js
   ```

**Note**: If the Agent is using a non-default hostname or port, you must also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM Node.js OpenAI documentation][8] for more advanced usage.

##### Configuration

See the [APM Node.js library documentation][9] for all the available configuration options.

##### Validation

Validate that the APM Node.js library can communicate with your Agent by examining the debugging output from the application process. Within the section titled "Encoding payload," you should see an entry with a `name` field and a correlating value of `openai.request`. See below for a truncated example of this output:

```json
{
  "name": "openai.request",
  "resource": "listModels",
  "meta": {
    "component": "openai",
    "span.kind": "client",
    "openai.api_base": "https://api.openai.com/v1",
    "openai.request.endpoint": "/v1/models",
    "openai.request.method": "GET",
    "language": "javascript"
  },
  "metrics": {
    "openai.response.count": 106
  },
  "service": "my-service",
  "type": "openai"
}
```

[8]: https://datadoghq.dev/dd-trace-js/interfaces/plugins.openai.html
[9]: https://github.com/DataDog/dd-trace-js
[3]: https://ddtrace.readthedocs.io/en/stable/integrations.html#openai

<!-- xxz tab xxx -->
<!-- xxx tab "PHP" xxx -->

**Note**: To collect OpenAI `audio_speeches`, `audio_transcriptions`, `code_interpreter_sessions`, `completions`, `embeddings`, `images`, `moderations`, and `vector_stores` metrics, follow the API key setup instructions.

### Installation

#### APM: Get Usage Metrics for Php Applications

1. Enable APM and StatsD in your Datadog Agent. For example, in Docker:

   ```shell
   docker run -d
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

2. [Install the Datadog APM PHP library][16].

3. The library is automatically injected into your OpenAI PHP application.

**Notes**:

<!-- partial
{{% site-region region="us3,us5,eu,gov,ap1" %}}
- Non-US1 customers must set `DD_SITE` on the application command to the correct Datadog site parameter as specified in the table in the <a href="https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site">Datadog Site</a> page (for example, `datadoghq.eu` for EU1 customers).{{% /site-region %}}
partial -->

- If the Agent is using a non-default hostname or port, set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM PHP library documentation][17] for more advanced usage.

### Configuration

See the [APM PHP library documentation][17] for all the available configuration options.

### Validation

To validate that the APM PHP library can communicate with your Agent, examine the phpinfo output of your service. Under the `ddtrace` section, `Diagnostic checks` should be `passed`.

[16]:https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/php/#install-the-extension
[17]:https://docs.datadoghq.com/tracing/trace_collection/library_config/php/

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

**IMPORTANT**: An **admin-scoped API key is required** to collect the following metrics and Cloud Cost Management data:
- `audio_speeches`
- `audio_transcriptions`
- `code_interpreter_sessions`
- `completions`
- `embeddings`
- `images`
- `moderations`
- `vector_stores`

Without an admin-scoped API key, these metrics and CCM cost data are not ingested.

All remaining metrics below are collected with the APM setup methods.

See [metadata.csv][4] for a list of metrics provided by this integration.

### Events

The OpenAI integration does not include any events.

### Service Checks

The OpenAI integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor your OpenAI usage with Datadog][6]
- [Monitor Azure OpenAI with Datadog][7]
- [OpenAI Monitor Templates][12]

[1]: https://openai.com/
[2]: https://ddtrace.readthedocs.io/en/stable/installation_quickstart.html
[3]: https://ddtrace.readthedocs.io/en/stable/integrations.html#openai
[4]: https://github.com/DataDog/integrations-core/blob/master/openai/metadata.csv
[5]: https://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/monitor-openai-with-datadog/
[7]: https://www.datadoghq.com/blog/monitor-azure-openai-with-datadog/
[10]: https://platform.openai.com/
[11]: /integrations/openai
[12]: /monitors/recommended?q=integration%3AOpenAI&only_installed=false&p=1
[13]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
[14]: /cost
[15]: https://docs.datadoghq.com/cloud_cost_management/saas_costs/?tab=openai#data-collected
[16]: https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max
[17]: https://platform.openai.com/docs/
[18]: https://platform.openai.com/
[19]: https://www.datadoghq.com/product/llm-observability/
[20]: https://platform.openai.com/settings/organization/admin-keys
