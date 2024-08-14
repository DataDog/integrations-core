# Submit Logs from HTTP API

Some systems expose their logs from HTTP endpoints rather than files that the Logs Agent can tail.
In such cases we write an agent integration to crawl the endpoints and submit the logs.

## Getting Started

This tutorial assumes you have done the following:

- [set up your environment](../../index.md#getting-started)
- read about the [base check](../../base/basics.md) paying special attention to its [HTTP capabilities](../../base/http.md)


Let's say you are building an integration for an API provided by *ACME Inc.*
Run the following command to create the scaffolding for your integration:

```
ddev create ACME
```

This adds a folder called `acme` in your `integrations-core` folder.
The rest of the tutorial we will spend in that `acme` folder.

!!! warning "Non-working Example"
    In this tutorial we use a concrete example.
    Note that this example code doesn't work, it only illustrates the concepts.

## Define a Stream of Logs

In order to submit logs to Datadog we must first get them from *ACME*'s API.

Open `datadog_checks/acme/check.py` in your editor and add the following:

```python
from datadog_checks.base.logs.crawler.stream import LogRecord, LogStream

class AcmeLogStream(LogStream):
    def records(self):
        return []
```

You need to implement the [`records`](../../base/logs.md#datadog_checks.base.checks.logs.crawler.stream.LogStream.records) method to return a sequence of log records.
Use the [`AgentCheck.http` property](../../base/api.md#datadog_checks.base.checks.base.AgentCheck.http) to make your requests.

## Register Streams with the Agent

Once we have streams of logs, we can plug them into the `AgentCheck` machinery.
In the same file add:

```python
from datadog_checks.base.logs.crawler.base import LogCrawlerCheck

...

class MyCrawlerCheck(LogCrawlerCheck):
    def get_log_streams(self):
        return [AcmeLogStream(check=self, name="ACME log stream")]
```
