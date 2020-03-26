# Databases

-----

What _is_ a database, you may wonder. Well, the answer to that question is [fascinating](https://lmgtfy.com/?q=What+is+a+database%3F&iie=1)!

No matter the database you wish to monitor, the base package provides a standard way to define and collect data from arbitrary queries.

The core premise is that you define a function that accepts a query (usually a `str`) and it returns a sequence of equal length results.

## Interface

All the functionality is exposed by the `Query` and `QueryManager` classes.

::: datadog_checks.base.utils.db.Query
    rendering:
      heading_level: 3

::: datadog_checks.base.utils.db.QueryManager
    rendering:
      heading_level: 3

## Transformers

<br>

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/3RX9sUVwyCFSo/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

::: datadog_checks.base.utils.db.transform.ColumnTransformers
    rendering:
      heading_level: 3

::: datadog_checks.base.utils.db.transform.ExtraTransformers
    rendering:
      heading_level: 3
