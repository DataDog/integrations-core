# LangChain

## Overview
Monitor, troubleshoot, and evaluate your LLM-powered applications (e.g. chatbot, data extraction tool, etc) built using LangChain.

Use LLM Observability to investigate the root cause of issues, monitor operational performance, and evaluate the quality, privacy, and safety of your LLM applications.

See the [LLM Observability tracing view video](https://imgix.datadoghq.com/video/products/llm-observability/expedite-troubleshooting.mp4?fm=webm&fit=max) for an example of how you can investigate a trace.

Get cost estimation, prompt and completion sampling, error tracking, performance metrics, and more out of [LangChain][1] Python library requests using Datadog metrics, APM, and logs.

## Setup

### LLM Observability: Get end-to-end visibility into your LLM application using LangChain
You can enable LLM Observability in different environments. Follow the appropriate setup based on your scenario:

#### Installation for Python

##### If you do not have the Datadog Agent:
1. Install the `ddtrace` package:

   ```shell
   pip install ddtrace
   ```

2. Start your application with the following command, enabling Agentless mode:

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

##### Automatic LangChain Tracing

LangChain integration is automatically enabled when LLM Observability is configured. This captures latency, errors, input/output messages, and token usage for LangChain operations.

The following methods are traced for both synchronous and asynchronous LangChain operations:

- LLMs: `llm.invoke()`, `llm.ainvoke()`
- Chat Models: `chat_model.invoke()`, `chat_model.ainvoke()`
- Chains/LCEL: `chain.invoke()`, `chain.ainvoke()`, `chain.batch()`, `chain.abatch()`
- Embeddings: `OpenAIEmbeddings.embed_documents()`, `OpenAIEmbeddings.embed_query()`

No additional setup is required for these methods.

##### Validation

Validate that LLM Observability is properly capturing spans by checking your application logs for successful span creation. You can also run the following command to check the status of the `ddtrace` integration:

   ```shell
   ddtrace-run --info
   ```

Look for the following message to confirm the setup:

   ```
   Agent error: None
   ```

##### Debugging
If you encounter issues during setup, enable debug logging by passing the `--debug` flag:

   ```shell
   ddtrace-run --debug
   ```

This will display any errors related to data transmission or instrumentation, including issues with LangChain traces.

### APM: Get Usage Metrics for your python Applications

1. Enable APM and StatsD in your Datadog Agent. For example, in Docker:

   ```shell
   docker run -d --cgroupns host \
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
   pip install ddtrace>=1.17
   ```

3. Prefix your LangChain Python application command with `ddtrace-run`.

   ```shell
   DD_SERVICE="my-service" DD_ENV="staging" DD_API_KEY=<DATADOG_API_KEY> ddtrace-run python <your-app>.py
   ```

**Note**: If the Agent is using a non-default hostname or port, be sure to also set `DD_AGENT_HOST`, `DD_TRACE_AGENT_PORT`, or `DD_DOGSTATSD_PORT`.

See the [APM Python library documentation][2] for more advanced usage.

#### Configuration

See the [APM Python library documentation][3] for all the available configuration options.

#### Log Prompt & Completion Sampling

To enable log prompt and completion sampling, set the `DD_LANGCHAIN_LOGS_ENABLED=1` environment variable. By default, 10% of traced requests will emit logs containing the prompts and completions.

To adjust the log sample rate, see the [APM library documentation][3].

**Note**: Logs submission requires `DD_API_KEY` to be specified when running `ddtrace-run`.

#### Validation

Validate that the APM Python library can communicate with your Agent using:

   ```shell
   ddtrace-run --info
   ```

You should see the following output:

   ```
       Agent error: None
   ```

#### Debug Logging

Pass the `--debug` flag to `ddtrace-run` to enable debug logging.

   ```shell
   ddtrace-run --debug
   ```

This displays any errors sending data:

   ```
   ERROR:ddtrace.internal.writer.writer:failed to send, dropping 1 traces to intake at http://localhost:8126/v0.5/traces after 3 retries ([Errno 61] Connection refused)
   WARNING:ddtrace.vendor.dogstatsd:Error submitting packet: [Errno 61] Connection refused, dropping the packet and closing the socket
   DEBUG:ddtrace.contrib._trace_utils_llm.py:sent 2 logs to 'http-intake.logs.datadoghq.com'
   ```

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

### Events

The LangChain integration does not include any events.

### Service Checks

The LangChain integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: https://docs.langchain.com/docs/
[2]: https://ddtrace.readthedocs.io/en/stable/installation_quickstart.html
[3]: https://ddtrace.readthedocs.io/en/stable/integrations.html#langchain
[4]: https://github.com/DataDog/integrations-core/blob/master/langchain/metadata.csv
[5]: https://docs.datadoghq.com/help/