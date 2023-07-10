# CHANGELOG - cert_manager

## 3.1.1 / 2023-07-10

***Fixed***:

* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).

## 3.1.0 / 2023-05-26

***Added***: 

* Add an ignore_connection_errors option to the openmetrics check. See [#14504](https://github.com/DataDog/integrations-core/pull/14504).

***Fixed***: 

* Update minimum datadog base package version. See [#14463](https://github.com/DataDog/integrations-core/pull/14463).
* Deprecate `use_latest_spec` option. See [#14446](https://github.com/DataDog/integrations-core/pull/14446).


## 3.0.0 / 2022-09-16 / Agent 7.40.0

***Changed***: 

* Migrate to OpenMetrics V2. See [#12344](https://github.com/DataDog/integrations-core/pull/12344).

***Added***: 

* Move cert_manager to core. See [#12344](https://github.com/DataDog/integrations-core/pull/12344).


## 2.2.0 / 2021-11-03

***Added***: 

* Add days to certificate expiration widget to default dashboard. See [#1063](https://github.com/DataDog/integrations-extras/pull/1063).

***Fixed***: 

* Change cert_manager.clock_time type to gauge. See [#1055](https://github.com/DataDog/integrations-extras/pull/1055).


## 2.1.0 / 2021-10-19

***Added***: 

* Add 'certmanager_clock_time_seconds' metric collection. See [#1031](https://github.com/DataDog/integrations-extras/pull/1031). Thanks [albertrdixon](https://github.com/albertrdixon).


## 2.0.0 / 2021-03-25

***Added***: 

* Overview Dashboard

***Fixed***: 

* Fixed ACME related metrics. See [#826](https://github.com/DataDog/integrations-extras/pull/826). This fix breaks backwards compatibility.


## 1.0.0 / 2020-07-27

***Added***: 

* First release for cert_manager integration

 