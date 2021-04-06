# CHANGELOG - Snowflake

## 3.0.2 / 2021-03-07

* [Fixed] Rename config spec example consumer option `default` to `display_default`. See [#8593](https://github.com/DataDog/integrations-core/pull/8593).

## 3.0.1 / 2021-01-14 / Agent 7.26.0

* [Fixed] Do not throw configuration error for missing password when using OAuth. See [#8363](https://github.com/DataDog/integrations-core/pull/8363).

## 3.0.0 / 2020-12-11 / Agent 7.25.0

* [Added] Support proxy settings. See [#8019](https://github.com/DataDog/integrations-core/pull/8019).
* [Fixed] Document Snowflake connector proxy configuration and support proxy connection options. See [#8181](https://github.com/DataDog/integrations-core/pull/8181).
* [Changed] Make role configuration step more explicit. See [#8092](https://github.com/DataDog/integrations-core/pull/8092).

## 2.1.2 / 2020-11-06 / Agent 7.24.0

* [Fixed] Add workaround for issue in platform.platform() on python 3.8 or later. See [#7932](https://github.com/DataDog/integrations-core/pull/7932). Thanks [kurochan](https://github.com/kurochan).

## 2.1.1 / 2020-11-06

* [Fixed] Override the default `min_collection_interval`. See [#7949](https://github.com/DataDog/integrations-core/pull/7949).

## 2.1.0 / 2020-10-31

* [Added] Make improvements to documentation. See [#7902](https://github.com/DataDog/integrations-core/pull/7902).
* [Fixed] Properly pin base package version for new QueryManager feature. See [#7832](https://github.com/DataDog/integrations-core/pull/7832).

## 2.1.0 / 2020-10-21

* [Added] Added bytes_spilled metrics. See [#7810](https://github.com/DataDog/integrations-core/pull/7810)

## 2.0.1 / 2020-10-21

* [Fixed] Fixed Snowflake 2.0.0 release to remove unreleased QueryManager breaking change.

## 2.0.0 / 2020-10-13

* [Added] Add OAuth authentication option and use new connection on check run. See [#7703](https://github.com/DataDog/integrations-core/pull/7703).
* [Changed] QueryManager - Prevent queries leaking between check instances. See [#7750](https://github.com/DataDog/integrations-core/pull/7750).

## 1.0.0 / 2020-09-21 / Agent 7.23.0

* [Added] New Integration: Snowflake. See [#7043](https://github.com/DataDog/integrations-core/pull/7043).
