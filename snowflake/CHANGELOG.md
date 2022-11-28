# CHANGELOG - Snowflake

## 4.4.5 / 2022-11-28

* [Fixed] Update Snowflake connector and cryptography dependencies. See [#13367](https://github.com/DataDog/integrations-core/pull/13367).
* [Fixed] Remove default_backend parameter from cryptography calls. See [#13333](https://github.com/DataDog/integrations-core/pull/13333).

## 4.4.4 / 2022-09-19 / Agent 7.40.0

* [Fixed] Bump dependencies for 7.40. See [#12896](https://github.com/DataDog/integrations-core/pull/12896).

## 4.4.3 / 2022-08-05 / Agent 7.39.0

* [Fixed] Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).

## 4.4.2 / 2022-07-05 / Agent 7.38.0

* [Fixed] Properly read from `token_path` parameter. See [#12452](https://github.com/DataDog/integrations-core/pull/12452).

## 4.4.1 / 2022-06-28

* [Fixed] Fix organization data transfer query. See [#12420](https://github.com/DataDog/integrations-core/pull/12420).

## 4.4.0 / 2022-06-27

* [Added] Add support for organization level metrics. See [#12375](https://github.com/DataDog/integrations-core/pull/12375).

## 4.3.2 / 2022-06-15

* [Fixed] Fix reading of `token_path` option. See [#12366](https://github.com/DataDog/integrations-core/pull/12366).

## 4.3.1 / 2022-05-15 / Agent 7.37.0

* [Fixed] Properly validate `only_custom_queries`. See [#11992](https://github.com/DataDog/integrations-core/pull/11992).
* [Fixed] Fix small typo in config option. See [#11990](https://github.com/DataDog/integrations-core/pull/11990).
* [Fixed] Add section in docs about private link setup. See [#11883](https://github.com/DataDog/integrations-core/pull/11883).

## 4.3.0 / 2022-04-05 / Agent 7.36.0

* [Added] Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).

## 4.2.1 / 2022-03-10 / Agent 7.35.0

* [Fixed] Convert private key password into string instead of byte. See [#11648](https://github.com/DataDog/integrations-core/pull/11648).

## 4.2.0 / 2022-02-19

* [Added] Add `pyproject.toml` file. See [#11433](https://github.com/DataDog/integrations-core/pull/11433).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).

## 4.1.0 / 2022-01-27

* [Added] Refactor snowflake validators. See [#11208](https://github.com/DataDog/integrations-core/pull/11208).
* [Added] Add key authentication option. See [#11180](https://github.com/DataDog/integrations-core/pull/11180).
* [Added] Add token_path config option. See [#11160](https://github.com/DataDog/integrations-core/pull/11160).
* [Added] Add aggregate_last_24_hours option. See [#11157](https://github.com/DataDog/integrations-core/pull/11157).
* [Fixed] Register private_key_password as secret. See [#11215](https://github.com/DataDog/integrations-core/pull/11215).
* [Fixed] Standardize key and token options behaviour. See [#11214](https://github.com/DataDog/integrations-core/pull/11214).
* [Fixed] Fix configuration error for custom queries. See [#11185](https://github.com/DataDog/integrations-core/pull/11185).

## 4.0.1 / 2021-11-23 / Agent 7.33.0

* [Fixed] Fix default field name of schema. See [#10714](https://github.com/DataDog/integrations-core/pull/10714).

## 4.0.0 / 2021-10-04 / Agent 7.32.0

* [Added] Sync configs with new option and bump base requirement. See [#10315](https://github.com/DataDog/integrations-core/pull/10315).
* [Added] Add runtime configuration validation. See [#8983](https://github.com/DataDog/integrations-core/pull/8983).
* [Added] Disable generic tags. See [#9854](https://github.com/DataDog/integrations-core/pull/9854).
* [Fixed] Bump snowflake_connector_python and requests for Py3. See [#10060](https://github.com/DataDog/integrations-core/pull/10060).
* [Changed] Add test for critical service check and fix namespace. See [#10062](https://github.com/DataDog/integrations-core/pull/10062).
* [Removed] Drop support for Python 2 and bump requests. See [#10105](https://github.com/DataDog/integrations-core/pull/10105).

## 3.1.0 / 2021-08-22 / Agent 7.31.0

* [Added] Pin snowflake-connector and requests. See [#9905](https://github.com/DataDog/integrations-core/pull/9905).
* [Fixed] Revert request bump. See [#9912](https://github.com/DataDog/integrations-core/pull/9912).

## 3.0.3 / 2021-07-12 / Agent 7.30.0

* [Fixed] Bump base package dependency. See [#9666](https://github.com/DataDog/integrations-core/pull/9666).

## 3.0.2 / 2021-03-07 / Agent 7.27.0

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
