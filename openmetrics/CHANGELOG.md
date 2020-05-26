# CHANGELOG - OpenMetrics

## 1.7.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add default template to openmetrics & jmx config. See [#6328](https://github.com/DataDog/integrations-core/pull/6328).
* [Fixed] Hide openmetrics template options that are typically overridden. See [#6338](https://github.com/DataDog/integrations-core/pull/6338).

## 1.6.1 / 2020-04-07

* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 1.6.0 / 2020-04-04

* [Added] Add OpenMetrics config spec template. See [#6142](https://github.com/DataDog/integrations-core/pull/6142).
* [Added] Allow option to submit histogram/summary sum metric as monotonic count. See [#6127](https://github.com/DataDog/integrations-core/pull/6127).
* [Fixed] Sync OpenMetrics config. See [#6250](https://github.com/DataDog/integrations-core/pull/6250).
* [Fixed] Add `send_distribution_sums_as_monotonic` to openmetrics config spec. See [#6247](https://github.com/DataDog/integrations-core/pull/6247).
* [Fixed] Update prometheus_client. See [#6200](https://github.com/DataDog/integrations-core/pull/6200).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.5.0 / 2020-02-22

* [Added] Make `ignore_metrics` support `*` wildcard for OpenMetrics. See [#5759](https://github.com/DataDog/integrations-core/pull/5759).

## 1.4.0 / 2020-01-13

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 1.3.0 / 2019-10-11

* [Added] Add an option to send histograms/summary counts as monotonic counters. See [#4629](https://github.com/DataDog/integrations-core/pull/4629).

## 1.2.0 / 2019-06-01

* [Added] Use Kube service account bearer token for authentication. See [#3829](https://github.com/DataDog/integrations-core/pull/3829).

## 1.1.0 / 2019-05-14

* [Fixed] Fix type override values in example config. See [#3717](https://github.com/DataDog/integrations-core/pull/3717).
* [Added] Adhere to code style. See [#3549](https://github.com/DataDog/integrations-core/pull/3549).

## 1.0.0 / 2018-10-13

* [Added] Add OpenMetrics integration. See [#2148][1].

[1]: https://github.com/DataDog/integrations-core/pull/2148
