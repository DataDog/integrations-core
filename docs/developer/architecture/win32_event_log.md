# Windows Event Log

-----

## Overview

Users set a `path` with which to collect events from that is the name of a channel
like `System`, `Application`, etc.

There are 3 ways to select filter criteria rather than collecting all events:

- `query` - A raw XPath or structured XML query used to filter events. This overrides any selected `filters`.
- `filters` - A mapping of properties to allowed values. Every filter (equivalent to the `and` operator) must match
  any value (equivalent to the `or` operator). This option is a convenience for a `query` that is relatively basic.

    Rather than collect all events and perform filtering within the check, the filters are converted to an XPath
    expression. This approach offloads all filtering to the kernel (like `query`), which increases performance
    and reduces bandwidth usage when connecting to a remote machine.

- `included_messages`/`excluded_messages` - These are regular expression patterns used to filter by events' messages
  specifically (if a message is found), with the exclude list taking precedence. These may be used in place of or
  with `query`/`filters`, as there exists no query construct by which to select a message attribute.

A [pull subscription model](https://docs.microsoft.com/en-us/windows/win32/wes/subscribing-to-events#pull-subscriptions)
is used. At every check run, the cached event log handle waits to be signaled for a configurable number
of seconds. If signaled, the check then polls all available events in batches of a configurable size.

At configurable intervals, the most recently encountered event is saved to the filesystem. This is useful for preventing
duplicate events being sent as a consequence of Agent restarts, especially when the `start` option is set to `oldest`.

## Logs

Events may alternatively be configured to be submitted as logs. The code for that resides
[here](https://github.com/DataDog/datadog-agent/tree/main/pkg/logs/internal/tailers/windowsevent).

Only a subset of the check's functionality is available. Namely, each log configuration
will collect all events of the given channel without filtering, tagging, nor remote
connection options.

This implementation uses the [push subscription model](https://docs.microsoft.com/en-us/windows/win32/wes/subscribing-to-events#push-subscriptions).
There is a bit of C in charge of rendering the relevant data and registering the Go tailer
callback that ultimately sends the log to the backend.

## Legacy mode

Setting `legacy_mode` to `true` in the check will use WMI to collect events, which is significantly
more resource intensive. This mode has entirely different configuration options and will
be removed in a future release.

Agent 6 can only use this mode as Python 2 [does not support](https://github.com/mhammond/pywin32/issues/1546) the new implementation.
