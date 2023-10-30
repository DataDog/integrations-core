# Databases

-----

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/dIBLtolI6axTGIGopo/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

No matter the database you wish to monitor, the base package provides a standard way to define and collect data from arbitrary queries.

The core premise is that you define a function that accepts a query (usually a `str`) and it returns a sequence of equal length results.

## Interface

All the functionality is exposed by the `Query` and `QueryManager` classes.

::: datadog_checks.base.utils.db.query.Query
    options:
      heading_level: 3
      members:
        - __init__
        - compile

::: datadog_checks.base.utils.db.core.QueryManager
    options:
      heading_level: 3
      members:
        - __init__
        - execute

## Transformers

<br>

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/3RX9sUVwyCFSo/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

### Column

#### match

::: datadog_checks.base.utils.db.transform.get_match
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### temporal_percent

::: datadog_checks.base.utils.db.transform.get_temporal_percent
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### time_elapsed

::: datadog_checks.base.utils.db.transform.get_time_elapsed
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### monotonic_gauge

::: datadog_checks.base.utils.db.transform.get_monotonic_gauge
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### service_check

::: datadog_checks.base.utils.db.transform.get_service_check
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### tag

::: datadog_checks.base.utils.db.transform.get_tag
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### tag_list

::: datadog_checks.base.utils.db.transform.get_tag_list
    options:
      show_root_heading: false
      show_root_toc_entry: false

### Extra

Every column transformer (except `tag`) is supported at this level, the only
difference being one must set a `source` to retrieve the desired value.

So for example here:

```yaml
columns:
  - name: foo.bar
    type: rate
extras:
  - name: foo.current
    type: gauge
    source: foo.bar
```

the metric `foo.current` will be sent as a gauge with the value of `foo.bar`.

#### percent

::: datadog_checks.base.utils.db.transform.get_percent
    options:
      show_root_heading: false
      show_root_toc_entry: false

#### expression

::: datadog_checks.base.utils.db.transform.get_expression
    options:
      show_root_heading: false
      show_root_toc_entry: false
