# Submit Logs from HTTP API

## Getting Started

This tutorial assumes you have done the following:

- [Set up your environment](../../index.md#getting-started).
- Read the [logs crawler documentation](../../base/logs-crawlers.md).
- Read about the [HTTP capabilities](../../base/http.md) of the base class.

Let's say we are building an integration for an API provided by *ACME Inc.*
Run the following command to create the scaffolding for our integration:

```
ddev create ACME
```

This adds a folder called `acme` in our `integrations-core` folder.
The rest of the tutorial we will spend in the `acme` folder.
```
cd acme
```

In order to spin up the integration in our scaffolding, if we add the following to `tests/conftest.py`:

```python
@pytest.fixture(scope='session')
def dd_environment():
    yield {'tags': ['tutorial:acme']}
```

Then run:
```
ddev env start acme py3.11 --dev
```

## Define an Agent Check

We start by registering an implementation for our integration.
At first it is empty, we will expand on it step by step.

Open `datadog_checks/acme/check.py` in our editor and put the following there:

```python
from datadog_checks.base.checks.logs.crawler.base import LogCrawlerCheck


class AcmeCheck(LogCrawlerCheck):
    __NAMESPACE__ = 'acme'
```

Now we'll run something we will refer to as *the check command*:
```
ddev env agent acme py3.11 check
```

We'll see the following error:
```
Can't instantiate abstract class AcmeCheck with abstract method get_log_streams
```

We need to define the `get_log_streams` method.
As [stated in the docs](../../base/logs-crawlers.md#datadog_checks.base.checks.logs.crawler.base.LogCrawlerCheck.get_log_streams), it must return an iterator over `LogStream` subclasses.
The next section describes this further.

## Define a Stream of Logs

In the same file, add a `LogStream` subclass and return it (wrapped in a list) from `AcmeCheck.get_log_streams`:

```python
from datadog_checks.base.checks.logs.crawler.base import LogCrawlerCheck
from datadog_checks.base.checks.logs.crawler.stream import LogStream

class AcmeCheck(LogCrawlerCheck):
    __NAMESPACE__ = 'acme'

    def get_log_streams(self):
        return [AcmeLogStream(check=self, name='ACME log stream')]

class AcmeLogStream(LogStream):
    """Stream of Logs from ACME"""
```

Now running *the check command* will show a new error:

```
TypeError: Can't instantiate abstract class AcmeLogStream with abstract method records
```

Once again we need to define a method, this time [`LogStream.records`](../../base/logs-crawlers.md#datadog_checks.base.checks.logs.crawler.stream.LogStream.records).
This method accepts a `cursor` argument.
We ignore this argument for now and explain it later.


```python
from datadog_checks.base.checks.logs.crawler.stream import LogRecord, LogStream
from datadog_checks.base.utils.time import get_timestamp

... # Skip AcmeCheck to focus on LogStream.


class AcmeLogStream(LogStream):
    """Stream of Logs from ACME"""

    def records(self, cursor=None):
        return [
            LogRecord(
                data={'message': 'This is a log from ACME.', 'level': 'info'},
                cursor={'timestamp': get_timestamp()},
            )
        ]
```

There are several things going on here.
`AcmeLogStream.records` returns an iterator over `LogRecord` objects.
For simplicity here we return a list with just one record.
After we understand what each `LogRecord` looks like we can discuss how to generate multiple records.

### What is a Log Record?

The `LogRecord` class has 2 fields.
In `data` we put any data in here that we want to submit as a log to Datadog.
In `cursor` we store a unique identifier for this specific `LogRecord`.

We use the `cursor` field to checkpoint our progress as we scrape the external API.
In other words, every time our integration completes its run we save the last cursor we submitted.
We can then resume scraping from this cursor.
That's what the `cursor` argument to the `records` method is for.
The very first time the integration runs this `cursor` is `None` because we have no checkpoints.
For every subsequent integration run, the `cursor` will be set to the `LogRecord.cursor` of the last `LogRecord` yielded or returned from `records`.

Some things to consider when defining cursors:

- Use UTC time stamps!
- Only using the timestamp as a unique identifier may not be enough. We can have different records with the same timestamp.
- One popular identifier is the order of the log record in the stream. Whether this works or not depends on the API we are crawling.


### Scraping for Log Records

In our toy example we returned a list with just one record.
In practice we will need to create a list or lazy iterator over `LogRecord`s.
We will construct them from data that we collect from the external API, in this case the one from *ACME*.

Below are some tips and considerations when scraping external APIs:

1. Use the `cursor` argument to checkpoint your progress.
1. The Agent schedules an integration run approximately every 10-15 seconds.
1. The intake won't accept logs that are older than 18 hours. For better performance skip such logs as you generate `LogRecord` items.
