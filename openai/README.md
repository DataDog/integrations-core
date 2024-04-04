# OpenAI

## Overview

Get cost estimation, prompt and completion sampling, error tracking, performance metrics, and more out of [OpenAI][1] account-level, Python, and Node.js library requests using Datadog metrics, APM, and logs.

## Setup


<!-- xxx tabs xxx -->
<!-- xxx tab "Python" xxx -->

**Note**: This setup method does not collect `openai.api.usage.*` metrics. To collect these metrics, also follow the API key setup instructions.

### Installation

<!-- NOTE: This section is overwritten by the OpenAI configuration component exported in -->
<!-- web-ui. Make sure to update the markdown / code there to see any changes take -->
<!-- effect on the tile. -->

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


### Configuration

See the [APM Python library documentation][3] for all the available configuration options.


#### Log Prompt & Completion Sampling

To enable log prompt and completion sampling, set the `DD_OPENAI_LOGS_ENABLED="true"` environment variable. By default, 10% of traced requests will emit logs containing the prompts and completions.

To adjust the log sample rate, see the [APM library documentation][3].

**Note**: Logs submission requires `DD_API_KEY` to be specified when running `ddtrace-run`.


### Validation

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
DEBUG:ddtrace.contrib.openai._logging.py:sent 2 logs to 'http-intake.logs.datadoghq.com'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Node.js" xxx -->

**Note**: This setup method does not collect `openai.api.usage.*` metrics. To collect these metrics, also follow the API key setup instructions.

### Installation

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

### Configuration

See the [APM Node.js library documentation][9] for all the available configuration options.


#### Log prompt and completion sampling

To enable log prompt and completion sampling, set the `DD_OPENAI_LOGS_ENABLED=1` environment variable. By default, 10% of traced requests emit logs containing the prompts and completions.

To adjust the log sample rate, see the [APM library documentation][3].

**Note**: Logs submission requires `DD_API_KEY` to be specified.


### Validation

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
<!-- xxx tab "API Key" xxx -->

**Note**: This setup method only collects `openai.api.usage.*` metrics. To collect all metrics provided by this integration, also follow the APM setup instructions.

### Installation

1. Login to your [OpenAI Account][10].
2. Navigate to **View API Keys** under account settings.
3. Click the **Create a new secret key** button.
4. Copy the created API Key to your clipboard.

### Configuration

1. Navigate to the configuration tab inside Datadog [OpenAI integration tile][11].
2. Enter an account name and OpenAI API key copied above in the accounts configuration.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

The `openai.api.usage.*` metrics are only collected with the API key setup method. All remaining metrics below are collected with the APM setup methods.

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
[11]: https://app.datadoghq.com/integrations/openai
[12]: https://app.datadoghq.com/monitors/recommended?q=integration%3AOpenAI&only_installed=false&p=1
[13]: https://docs.datadoghq.com/getting_started/site/#access-the-datadog-site
