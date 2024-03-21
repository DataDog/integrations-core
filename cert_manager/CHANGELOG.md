# CHANGELOG - cert_manager

<!-- towncrier release notes start -->

## 4.1.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 4.0.0 / 2024-01-05 / Agent 7.51.0

***Changed***:

* Add missing config_models files and update the base check version ([#16300](https://github.com/DataDog/integrations-core/pull/16300))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 3.1.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.1.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 3.0.0 / 2022-09-16 / Agent 7.40.0

***Changed***:

* Migrate to OpenMetrics V2 ([#12344](https://github.com/DataDog/integrations-core/pull/12344))

***Added***:

* Move cert_manager to core ([#12344](https://github.com/DataDog/integrations-core/pull/12344))

## 2.2.0 / 2021-11-03

***Added***:

* Add days to certificate expiration widget to default dashboard ([#1063](https://github.com/DataDog/integrations-extras/pull/1063))

***Fixed***:

* Change cert_manager.clock_time type to gauge ([#1055](https://github.com/DataDog/integrations-extras/pull/1055))

## 2.1.0 / 2021-10-19

***Added***:

* Add 'certmanager_clock_time_seconds' metric collection ([#1031](https://github.com/DataDog/integrations-extras/pull/1031)) Thanks [albertrdixon](https://github.com/albertrdixon).

## 2.0.0 / 2021-03-25

***Added***:

* Overview Dashboard

***Fixed***:

* Fixed ACME related metrics ([#826](https://github.com/DataDog/integrations-extras/pull/826)) This fix breaks backwards compatibility.

## 1.0.0 / 2020-07-27

***Added***:

* First release for cert_manager integration
