# CHANGELOG - Argo CD

## Unreleased

## 1.2.0 / 2023-07-10

***Added***:

* Add ArgoCD notifications controller metrics. See [#14690](https://github.com/DataDog/integrations-core/pull/14690). Thanks [maxknee](https://github.com/maxknee).

***Fixed***:

* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).

## 1.1.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check. See [#14504](https://github.com/DataDog/integrations-core/pull/14504).

***Fixed***:

* Update minimum datadog base package version. See [#14463](https://github.com/DataDog/integrations-core/pull/14463).
* Deprecate `use_latest_spec` option. See [#14446](https://github.com/DataDog/integrations-core/pull/14446).

## 1.0.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Fix error that was triggered by including configuration parameters not ending in `_endpoint`. See [#13409](https://github.com/DataDog/integrations-core/pull/13409).

## 1.0.0 / 2022-11-16

***Added***:

* Argo CD Integration. See [#13223](https://github.com/DataDog/integrations-core/pull/13223).
