# Submit Logs from HTTP API

## Getting Started

This tutorial assumes you have done the following:

- [set up your environment](../../index.md#getting-started)
- read the [logs crawler documentation](../../base/logs-crawlers.md)
- read about the [HTTP capabilities](../../base/http.md) of the base class

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
ddev env start acme py3.11 --base
```

## Define an Agent Check

We start by registering an implementation for our integration.
At first it is empty, we will expand it step by step.

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
As [its docs say](../../base/logs-crawlers.md#datadog_checks.base.checks.logs.crawler.base.LogCrawlerCheck.get_log_streams) it must return an iterator over `LogStream` subclasses.
That's what the next section is about.

## Define a Stream of Logs

In the same file let's add a `LogStream` subclass and return it (wrapped in a list) from `AcmeCheck.get_log_streams`:

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

Every time we modify the source code, make sure to restart the environment:

```
ddev env stop acme py3.11 && ddev env start acme py3.11 --base
```

Now running *the check command* will show a new error:

```
TypeError: Can't instantiate abstract class AcmeLogStream with abstract method records
```

Once again we need to define a method, this time [`LogStream.records`](../../base/logs-crawlers.md#datadog_checks.base.checks.logs.crawler.stream.LogStream.records).


```python
from datadog_checks.base.checks.logs.crawler.stream import LogRecord, LogStream

... # Skip AcmeCheck to focus on LogStream.


class AcmeLogStream(LogStream):
    """Stream of Logs from ACME"""

    def records(self):
        return [
            LogRecord(
                data={'message': 'This is a log from ACME.', 'level': 'info'},
                cursor={'timestamp': dt.now().timestamp()},
            )
        ]
```

There are several things going on here.
`AcmeLogStream.records` returns an iterator over `LogRecord` objects.
We discuss these objects first so to keep the method itself simple we return a list with just one record.

### What is a Log Record?

The `LogRecord` class has 2 fields.
In `data` we put any data in here that we want to submit as a log to Datadog.
In `cursor` we store a unique identifier for this specific `LogRecord`.
Some things to consider when defining cursors:

- Use UTC time stamps!
- Only using the timestamp as a unique identifier may not be enough. We can have different records with the same timestamp.
- One popular identifier is the order of the log record in the stream. Whether this works or not depends on the API we are crawling.


### Scraping for Log Records

In our toy example we returned a list with just one record.
In practice we will need to create list or lazy iterator over `LogRecord`s.
We will construct them from data that we collect from the external API, in this case the one from *ACME*.

Below are some tips and considerations when scraping external APIs:

1. The Agent schedules an integration run every 15 seconds. This functions as a retry mechanism, so there is less need for elaborate retry/backoff setups in integrations.
1. The intake won't accept logs that are older than 18 hours. For better performance skip such logs as you generate `LogRecord` items.
