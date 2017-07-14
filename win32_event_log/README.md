# Agent Check: Windows Event Log

# Overview

This check watches for events in the Windows Event Log and forwards them to Datadog.

# Installation

The Windows Event Log check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts. If you need the newest version of the check, install the `dd-check-win32-event-log` package.

# Configuration

Create a file `win32_event_log.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
```

This minimal file will capture all events from localhost, but you can configure the check to only collect certain kinds of events. See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/conf.yaml.example) for a comprehensive list and description of options that allow you to do this.

Restart the Agent to start sending Windows events to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `win32_event_log` under the Checks section:

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

# Compatibility

The win32_event_log check is compatible with Windows.

# Further Reading

See our [series of blog posts](https://www.datadoghq.com/blog/monitoring-windows-server-2012) about monitoring Windows Server 2012 with Datadog.