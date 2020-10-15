# CHANGELOG - Hive

## 1.3.3 / 2020-09-21 / Agent 7.23.0

* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 1.3.2 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] Add new_gc_metrics to all jmx integrations. See [#7073](https://github.com/DataDog/integrations-core/pull/7073).

## 1.3.1 / 2020-06-29 / Agent 7.21.0

* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Adjust jmxfetch config. See [#6864](https://github.com/DataDog/integrations-core/pull/6864).

## 1.3.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add rmi_connection_timeout & rmi_client_timeout to config spec. See [#6459](https://github.com/DataDog/integrations-core/pull/6459).
* [Added] Add default template to openmetrics & jmx config. See [#6328](https://github.com/DataDog/integrations-core/pull/6328).

## 1.2.0 / 2020-04-04 / Agent 7.19.0

* [Added] Add `service_check_prefix` config to jmx. See [#6163](https://github.com/DataDog/integrations-core/pull/6163).
* [Added] Use config spec. See [#5979](https://github.com/DataDog/integrations-core/pull/5979).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Fix JMX spec doc. See [#6074](https://github.com/DataDog/integrations-core/pull/6074).
* [Fixed] Remove examples from jmx template. See [#6006](https://github.com/DataDog/integrations-core/pull/6006).

## 1.1.2 / 2019-12-04 / Agent 7.16.0

* [Fixed] Fix bean name of directsql_errors metric. See [#5141](https://github.com/DataDog/integrations-core/pull/5141).

## 1.1.1 / 2019-12-02

* [Fixed] Fix directsql_error metric bean in config. See [#5074](https://github.com/DataDog/integrations-core/pull/5074).

## 1.1.0 / 2019-06-19 / Agent 6.13.0

* [Added] Add log section. See [#3891](https://github.com/DataDog/integrations-core/pull/3891).

## 1.0.2 / 2019-06-18

* [Fixed] Fix metric type. See [#3885](https://github.com/DataDog/integrations-core/pull/3885).
* [Fixed] Fix Hive metadatas. See [#3851](https://github.com/DataDog/integrations-core/pull/3851).

## 1.0.1 / 2019-06-05 / Agent 6.12.0

* [Fixed] Fix init file. See [#3855](https://github.com/DataDog/integrations-core/pull/3855).

## 1.0.0 / 2019-06-01

* [Added] Hive integration. See [#3723](https://github.com/DataDog/integrations-core/pull/3723).
