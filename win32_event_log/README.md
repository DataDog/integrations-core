# Agent Check: Windows Event Log

## Overview

This check watches for events in the Windows Event Log and forwards them to Datadog.

## Setup
### Installation

The Windows Event Log check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

### Configuration

Create a file `win32_event_log.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
```

This minimal file will capture all events from localhost, but you can configure the check to only collect certain kinds of events. See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/conf.yaml.example) for a comprehensive list and description of options that allow you to do that.

Restart the Agent to start sending Windows events to Datadog.

### Validation

See the info page in the Agent Manager and look for `win32_event_log` under the Checks section:

```
  Checks
  ======
    [...]

    win32_event_log
    -------
      - instance #0 [OK]
      - Collected 0 metrics, 5 events & 0 service checks

    [...]
```

## Compatibility

The win32_event_log check is compatible with all Windows platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/metadata.csv) for a list of metrics provided by this integration.

### Events
All Windows Event are forwarded to your Datadog application

### Service Checks
The Win32 Event log check does not include any service check at this time.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
See our [series of blog posts](https://www.datadoghq.com/blog/monitoring-windows-server-2012) about monitoring Windows Server 2012 with Datadog.
