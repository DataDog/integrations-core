# Logs

::: datadog_checks.base.checks.logs.crawler.stream.LogRecord
    options:
      heading_level: 2
      members:
        - cursor
        - data

::: datadog_checks.base.checks.logs.crawler.stream.LogStream
    options:
      heading_level: 2
      filters: ["!^_[^_]?", "^__.+__$"]

::: datadog_checks.base.checks.logs.crawler.base.LogCrawlerCheck
    options:
      heading_level: 2
      filters: ["!^_[^_]?", "^__.+__$"]
