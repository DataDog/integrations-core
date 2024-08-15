# Log Crawlers

## Overview

Some systems expose their logs from HTTP endpoints instead of files that the Logs Agent can tail.
In such cases you can create an agent integration to crawl the endpoints and submit the logs.

This diagram shows how a logs crawler agent integration that fits into the agent.

<div align="center" markdown="1">

```mermaid
graph LR
    subgraph "Agent Integration (you write this)"
    A[Log Stream] -->|Log Records| B(Log Crawler Check)
    end
    subgraph Agent
    B -->|Send Logs| C(RTLoader API)
    C -->|Save Logs| D[(Log File)]
    E(Logs Agent) -->|Tail Logs| D
    end
    E -->|Submit Logs| F(Logs Intake)
```

</div>

## Interface

::: datadog_checks.base.checks.logs.crawler.base.LogCrawlerCheck
    options:
      heading_level: 3
      members:
        - get_log_streams
        - process_streams
        - check

::: datadog_checks.base.checks.logs.crawler.stream.LogStream
    options:
      heading_level: 3
      members:
        - records
        - __init__

::: datadog_checks.base.checks.logs.crawler.stream.LogRecord
    options:
      heading_level: 3
      members: []
