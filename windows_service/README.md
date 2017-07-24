# Agent Check: Windows Service

# Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

# Installation

The Windows Service check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Windows hosts.

# Configuration

Create a file `windows_service.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: . # dot means localhost
#   username: <REMOTESERVER>\<REMOTEUSER> # if 'host' is a remote host
#   password: <PASSWORD>

# list at least one service to monitor
    services:
#     - wmiApSrv
```

You must provide service names as they appear in services.msc's properties field (e.g. wmiApSrv), NOT the display name (e.g. WMI Performance Adapter).

Restart the Agent to start monitoring the services and sending service checks to Datadog.

# Validation

See the info page in the Agent Manager and look for `windows_service` under the Checks section:

```
  Checks
  ======
    [...]

    windows_service
    -------
      - instance #0 [OK]
      - Collected 0 metrics, 0 events & 1 service check

    [...]
```

# Compatibility

The Windows Service check is compatible with all Windows platforms.

# Service Checks

**windows_service.state**:

The Agent submits this service check for each Windows service configured in `services`, tagging the service check with 'service:<service_name>'. The service check takes on the following statuses depending on Windows status:

|Windows status|windows_service.state|
|---|---|
|Stopped|CRITICAL|
|Start Pending|WARNING|
|Stop Pending|WARNING|
|Running|OK|
|Continue Pending|WARNING|
|Pause Pending|WARNING|
|Paused|WARNING|
|Unknown|UNKNOWN|

# Further Reading

See our [series of blog posts](https://www.datadoghq.com/blog/monitoring-windows-server-2012) about monitoring Windows Server 2012 with Datadog.
