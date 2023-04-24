# OpenAI

## Overview

Get cost estimation, prompt and completion sampling, error tracking,
performance metrics and more of [OpenAI][1] Python library requests using
Datadog metrics, APM and logs.

## Setup

### Installation

1. Enable APM in the Agent using the instructions [here][11].

2. Install the Datadog APM Python library.

```
pip install ddtrace
```


3. Prefix your Python application command with `ddtrace-run`.

```
DD_SERVICE="my-openai-service" DD_ENV="staging" DD_API_KEY=<DATADOG_API_KEY> ddtrace-run python <your-app>.py
```

Note: if the Agent is using a specified hostname/port, set `DD_AGENT_HOST` and `DD_TRACE_AGENT_PORT`.

See the [APM Python library documentation][12] for more advanced usage.


### Configuration

See the [APM Python library documentation][10] for all the available configuration options.


#### Log Prompt & Completion Sampling

To enable log prompt and completion sampling set the environment variable
`DD_OPENAI_LOGS_ENABLED=1`. By default, 10% of requests will emit logs
containing the prompts and completions.

To adjust the log sample rate see the [APM library documentation][10].

Note: logs submission requires `DD_API_KEY` to be specified when running
`ddtrace-run`.

### Validation

Validate that the APM Python library can communicate with the Agent using:

```
ddtrace-run --info
```

Should show

```
    Agent error: None
```

#### Debug Logging

Pass the `--debug` flag to `ddtrace-run` to enable debug logging.

```
ddtrace-run --debug
```

This will show any errors sending data:

```
ERROR:ddtrace.internal.writer.writer:failed to send, dropping 1 traces to intake at http://localhost:8126/v0.5/traces after 3 retries ([Errno 61] Connection refused)
WARNING:ddtrace.vendor.dogstatsd:Error submitting packet: [Errno 61] Connection refused, dropping the packet and closing the socket
DEBUG:ddtrace.contrib.openai._logging.py:sent 2 logs to 'http-intake.logs.datadoghq.com'
```

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The OpenAI integration does not include any events.

### Service Checks

The OpenAI integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://openai.com/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/openai/datadog_checks/openai/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/openai/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/openai/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://ddtrace.readthedocs.io/en/stable/integrations.html#openai
[11]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/python/?tab=containers#configure-the-datadog-agent-for-apm
[12]: https://ddtrace.readthedocs.io/en/stable/installation_quickstart.html
