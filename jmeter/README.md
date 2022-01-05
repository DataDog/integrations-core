# Agent Check: JMeter

## Overview

Datadog Backend Listener for Apache JMeter is an open source JMeter plugin used to send test results to the Datadog platform. It provides real-time reporting of test metrics like latency, the number of bytes sent and received, and more. You can also send to Datadog complete test results as log entries.

## Setup

### Installation

The Datadog Backend Listener plugin needs to be installed manually. See the latest release and more detailed installation instructions on the [repo release page][1].

### Configuration

The plugin has the following configuration options:

| Name       | Required | Default value | description|
|------------|:--------:|---------------|------------|
|apiKey | true | NA | Your Datadog API key.|
|datadogUrl | false | https://api.datadoghq.com/api/ | You can configure a different endpoint, for instance https://api.datadoghq.eu/api/ if your datadog instance is in the EU|
|logIntakeUrl | false | https://http-intake.logs.datadoghq.com/v1/input/ | You can configure a different endpoint, for instance https://http-intake.logs.datadoghq.eu/v1/input/ if your datadog instance is in the EU.|
|metricsMaxBatchSize|false|200|Metrics are submitted every 10 seconds in batches of size `metricsMaxBatchSize`.|
|logsBatchSize|false|500|Logs are submitted in batches of size `logsBatchSize` as soon as this size is reached.|
|sendResultsAsLogs|false|false|By default only metrics are reported to Datadog. To report individual test results as log events, set this field to `true`.|
|includeSubresults|false|false|A subresult is for instance when an individual HTTP request has to follow redirects. By default subresults are ignored.|
|samplersRegex|false|.*|An optional regex to filter the samplers to monitor.|

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this check.

### Service Checks

JMeter does not include any service checks.

### Events

JMeter does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

## Further Reading

Additional helpful documentation, links, and articles:

  - [Monitor JMeter test results with Datadog][4]

[1]: https://github.com/DataDog/jmeter-datadog-backend-listener/releases
[2]: https://github.com/DataDog/integrations-core/blob/master/jmeter/metadata.csv
[3]: https://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/monitor-jmeter-test-results-datadog/
