# Agent Check: Windows Event Log

# Overview

This check watches for events in the Windows Event Log and forwards them to Datadog.

# Installation

The Windows Event Log check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

# Configuration

Create a file `win32_event_log.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
```

This minimal file will capture all events from localhost, but you can configure the check to only collect certain kinds of events. See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/win32_event_log/conf.yaml.example) for a comprehensive list and description of options that allow you to do that.

Restart the Agent to start sending Windows events to Datadog.

# Validation

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

# Compatibility

The win32_event_log check is compatible with all Windows platforms.

# Further Reading

See our [series of blog posts](https://www.datadoghq.com/blog/monitoring-windows-server-2012) about monitoring Windows Server 2012 with Datadog.