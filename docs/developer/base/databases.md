# Databases

-----

What _is_ a database, you may wonder. Well, the answer to that question is [fascinating](https://lmgtfy.com/?q=What+is+a+database%3F&iie=1)!

No matter the database you wish to monitor, the base package provides a standard way to define and collect data from arbitrary queries.

The core premise is that you define a function that accepts a query (usually a `str`) and it returns a sequence of equal length results.

## Interface

All the functionality is exposed by the `Query` and `QueryManager` classes.

### Query

::: datadog_checks.base.utils.db.Query
    :docstring:
    :members:

### QueryManager

::: datadog_checks.base.utils.db.QueryManager
    :docstring:
    :members:

## Transformers

<br>

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/3RX9sUVwyCFSo/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

### Column

::: datadog_checks.base.utils.db.transform.ColumnTransformers
    :docstring:
    :members:

### Extra

Every column transformer (except `tag`) is supported at this level, the only difference being one must set a `source` to retrieve the desired value.

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

the metric `foo.current` will be sent as a gauge will the value of `foo.bar`.

::: datadog_checks.base.utils.db.transform.ExtraTransformers
    :docstring:
    :members:
