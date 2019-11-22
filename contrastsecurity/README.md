# Contrast Security Integration

## Overview

The Datadog-Constrant integration allows you to get your Contrast logs into Datadog.

## Setup

### Set up Contrast Protect logs collection

Enable logs collection for Datadog Agent in `/etc/datadog-agent/datadog.yaml` on Linux platforms. On other platforms, refer to the [Agent Configuration Files guide](https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6) for the location of your configuration file:
```
logs_enabled: true
```

* Create a new folder `java.d` in the `conf.d/` directory of DataDog configuration directory.
* Create a new `conf.yaml` file.
* Add a custom log collection configuration group.
```
logs:
  - type: file
    path: /path/to/contrast/security.log
    service: contrast
    source: java
```

* [Restart the Datadog Agent](https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#restart-the-agent).

For more information, consult the [Logs Collection documentation](https://docs.datadoghq.com/logs/log_collection/?tab=tailexistingfiles#getting-started-with-the-agent).

### Create a Logs Processing Pipeline

* Create a new pipeline in Datadog (*Logs* -> *Configuration* - > *New Pipeline*) 
* Expand the new pipeline and click *Add Processor*.
* Add a Grok parser to the pipeline with the following parsing rule:
```
ContrastSecurityLogRule %{data:data}pri=%{data:pri} src=%{ip:src} spt=%{number:spt} request=%{data:request} requestMethod=%{word:requestMethod} app=%{data:app} outcome=%{word:outcome}
```

### Import Contrast Security dashboard into Datadog
You can find your API key and application keys in *Integrations* -> *APIs*.

```bash
api_key=<YOUR_API_KEY>
app_key=<YOUR_APPLICATION_KEY>

curl  -X POST -H "Content-type: application/json" -d @contrast_security_protect.json "https://api.datadoghq.com/api/v1/dashboard?api_key=${api_key}&application_key=${app_key}"
```

For more information, refer to the [Datadog API documentation for creating a dashboard](https://docs.datadoghq.com/api/?lang=bash#create-a-dashboard).

## Data Collected

### Metrics

The Contrast integration does not include any metrics.

### Events

The Contrast integration does not send any events.

### Service Checks

The Contrast integration does not include any service checks.
