# Datadog Plugin for Apache JMeter

## Overview

Datadog Backend Listener for Apache JMeter is a JMeter plugin used to send test results to the Datadog platform. It includes the following features:

- Real time reporting of test metrics (latency, bytes sent and more). See the [Metrics](#metrics) section.
- Real time reporting of test results as Datadog log events.
- Ability to include sub results.

## Setup

### Installation

The Datadog Backend Listener plugin needs to be installed manually. See the latest release and more up-to-date installation instructions on its [GitHub repository][1].

You can install the plugin either manually or with JMeter Plugins Manager.

No Datadog Agent is necessary.

#### Manual installation

1. Download the Datadog plugin JAR file from the [release page][5].
2. Place the JAR in the `lib/ext` directory within your JMeter installation.
3. Launch JMeter (or quit and re-open the application).

#### JMeter plugins Manager

1. If not already configured, download the [JMeter Plugins Manager JAR][6].
2. Once you've completed the download, place the `.jar` in the `lib/ext` directory within your JMeter installation.
3. Launch JMeter (or quit and re-open the application).
4. Go to `Options > Plugins Manager > Available Plugins`.
5. Search for "Datadog Backend Listener".
6. Click the checbox next to the Datadog Backend Listener plugin.
7. Click "Apply Changes and Restart JMeter".

### Configuration

To start reporting metrics to Datadog:

1. Right click on the thread group or the test plan for which you want to send metrics to Datadog.
2. Go to `Add > Listener > Backend Listener`.
3. Modify the `Backend Listener Implementation` and select `org.datadog.jmeter.plugins.DatadogBackendClient` from the drop-down.
4. Set the `apiKey` variable to [your Datadog API key][7].
5. Run your test and validate that metrics have appeared in Datadog.

The plugin has the following configuration options:

| Name       | Required | Default value | description|
|------------|:--------:|---------------|------------|
|apiKey | true | NA | Your Datadog API key.|
|datadogUrl | false | https://api.datadoghq.com/api/ | You can configure a different endpoint, for instance https://api.datadoghq.eu/api/ if your datadog instance is in the EU|
|logIntakeUrl | false | https://http-intake.logs.datadoghq.com/v1/input/ | You can configure a different endpoint, for instance https://http-intake.logs.datadoghq.eu/v1/input/ if your datadog instance is in the EU|
|metricsMaxBatchSize|false|200|Metrics are submitted every 10 seconds in batches of size `metricsMaxBatchSize`|
|logsBatchSize|false|500|Logs are submitted in batches of size `logsBatchSize` as soon as this size is reached.|
|sendResultsAsLogs|false|true|By default, individual test results are reported as log events. Set to `false` to disable log reporting.|
|includeSubresults|false|false|A subresult is for instance when an individual HTTP request has to follow redirects. By default subresults are ignored.|
|excludeLogsResponseCodeRegex|false|`""`| Setting `sendResultsAsLogs` will submit all results as logs to Datadog by default. This option lets you exclude results whose response code matches a given regex. For example, you may set this option to `[123][0-5][0-9]` to only submit errors.|
|samplersRegex|false|`""`|Regex to filter which samplers to include. By default all samplers are included.|
|customTags|false|`""`|Comma-separated list of tags to add to every metric.|
|statisticsCalculationMode|false|`ddsketch`|Algorithm for percentile calculation: `ddsketch` (default), `aggregate_report` (matches JMeter Aggregate Reports), or `dashboard` (matches JMeter HTML Dashboards).|

#### Statistics Calculation Modes

- **ddsketch** (default): Uses Datadog's [DDSketch algorithm][8]. It provides approximate percentiles with a 1% error guarantee (relative to the theoretical value) and has a low memory footprint. Note that when comparing with `aggregate_report`, the difference might be greater because `aggregate_report` uses the "nearest rank" method, which introduces its own divergence due to quantization (especially with sparse values).
- **aggregate_report**: Matches JMeter's "Aggregate Reports" listener. It stores all response times in memory and calculates percentiles using the "nearest rank" method (nearest exact value from the dataset).
- **dashboard**: Uses a sliding window and interpolation (by default) to calculate percentiles, matching [JMeter's HTML Dashboards][9]. This mode may diverge significantly from the others when the limit of the sliding window is reached (default 20,000, but [configurable][10]).

#### Test Run Tagging

The plugin automatically adds a `test_run_id` tag to all metrics, logs, and events (Test Started/Ended) to help you isolate and filter specific test executions in Datadog.

- **Format**: `{hostname}-{ISO-8601 timestamp}-{random8chars}`
  - Example: `myhost-2026-01-24T14:30:25Z-a1b2c3d4`
  - In distributed mode, the `hostname` prefix becomes the `runner_id` (the JMeter distributed prefix) when present.

You can override this by providing your own `test_run_id` in the `customTags` configuration (e.g., `test_run_id:my-custom-run-id`). Any additional tags you add to `customTags` will also be included alongside the `test_run_id`.

#### Assertion Failures vs Errors

JMeter distinguishes between assertion failures and assertion errors. A failure means the assertion evaluated and did not pass. An error means the assertion could not be evaluated (for example, a null response or a script error). These map to `jmeter.assertions.failed` and `jmeter.assertions.error`.

#### Getting Final Results in Datadog Notebooks

To match JMeter's Aggregate Reports in a Datadog notebook, set `statisticsCalculationMode=aggregate_report` and query the `jmeter.final_result.*` metrics. These are emitted once at test end, so they are ideal for a single, authoritative snapshot.

**Note**: Since these metrics are emitted only once at the end of the test, ensure your selected time interval includes the test completion time.

Example queries (adjust tags as needed):

```text
avg:jmeter.final_result.response_time.p95{sample_label:total,test_run_id:YOUR_RUN_ID}
avg:jmeter.final_result.responses.error_percent{sample_label:total,test_run_id:YOUR_RUN_ID}
avg:jmeter.final_result.throughput.rps{sample_label:total,test_run_id:YOUR_RUN_ID}
```

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this check.

The plugin emits three types of metrics:
- **Interval metrics** (`jmeter.*`): Real-time metrics reset each reporting interval, useful for monitoring during test execution.
- **Cumulative metrics** (`jmeter.cumulative.*`): Aggregate statistics over the entire test duration, similar to JMeter's Aggregate Reports. These include a `final_result` tag (`true` at test end, `false` during execution).
- **Final result metrics** (`jmeter.final_result.*`): Emitted only once at test completion, providing an unambiguous way to query final test results without filtering by tag.

### Service Checks

JMeter does not include any service checks.

### Events

The plugin sends Datadog Events at the start and end of each test run:
- **JMeter Test Started**: Sent when the test begins
- **JMeter Test Ended**: Sent when the test completes

These events appear in the Datadog Event Explorer and can be used to correlate metrics with test execution windows.

## Troubleshooting

If for whatever reason you are not seeing JMeter metrics in Datadog, check your `jmeter.log` file, which should be in the `/bin` folder of your JMeter installation.

#### Not Seeing `runner_id`?

This is normal in local mode. The `runner_id` tag is only emitted in **distributed** tests, where JMeter provides a distributed prefix. In local runs, use `runner_host` or `runner_mode:local` for filtering instead.

Need help? Contact [Datadog support][3].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor JMeter test results with Datadog][4]

[1]: https://github.com/DataDog/jmeter-datadog-backend-listener
[2]: https://github.com/DataDog/integrations-core/blob/master/jmeter/metadata.csv
[3]: https://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/monitor-jmeter-test-results-datadog/
[5]: https://github.com/DataDog/jmeter-datadog-backend-listener/releases
[6]: https://jmeter-plugins.org/wiki/PluginsManager/
[7]: /account/settings#api
[8]: https://www.datadoghq.com/blog/engineering/computing-accurate-percentiles-with-ddsketch/
[9]: https://jmeter.apache.org/usermanual/generating-dashboard.html
[10]: https://jmeter.apache.org/usermanual/properties_reference.html#reporting
