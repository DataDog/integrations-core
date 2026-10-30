### Agent Observability Configuration

Get end-to-end visibility into your LLM application's calls to OpenAI with a Datadog tracing library. Completion and chat completion methods are traced automatically, capturing latency, input and output messages, and token usage without manual instrumentation.

**Step 1: Install the tracing library**

For Python:

```shell
pip install ddtrace
```

For Node.js, follow the [tracing library setup][1].

**Step 2: Start your application with Agent Observability enabled**

If you do not run the Datadog Agent, use agentless mode:

```shell
DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_AGENTLESS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
```

If the Datadog Agent is already running with APM and StatsD enabled:

```shell
DD_SITE=<YOUR_DATADOG_SITE> DD_API_KEY=<YOUR_API_KEY> DD_LLMOBS_ENABLED=1 DD_LLMOBS_ML_APP=<YOUR_ML_APP_NAME> ddtrace-run python <YOUR_APP>.py
```

In a serverless environment (AWS Lambda), install the **Datadog-Python** and **Datadog-Extension** Lambda layers, then set `DD_SITE`, `DD_API_KEY`, `DD_LLMOBS_ENABLED`, and `DD_LLMOBS_ML_APP` as environment variables. Datadog flushes spans automatically when the function finishes running.

**Note**: If the Agent runs on a custom host or port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT` accordingly.

### Validation

Check your application logs for successful span creation, or confirm the tracing library can reach your Agent:

```shell
ddtrace-run --info
```

Look for `Agent error: None` in the output.

### Troubleshooting

Pass the `--debug` flag to `ddtrace-run` to enable debug logging and surface tracing errors.

[1]: https://docs.datadoghq.com/llm_observability/setup/sdk/
