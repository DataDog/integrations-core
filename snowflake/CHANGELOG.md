# CHANGELOG - Snowflake

<!-- towncrier release notes start -->

## 5.5.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))
* Update dependencies ([#16963](https://github.com/DataDog/integrations-core/pull/16963))

***Fixed***:

* Stop reading the private key file and use the `private_key_file` and `private_key_file_pwd` options ([#16926](https://github.com/DataDog/integrations-core/pull/16926))
* Document the `metric_prefix` option for custom queries ([#17061](https://github.com/DataDog/integrations-core/pull/17061))
* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 5.4.0 / 2024-03-08 / Agent 7.52.0

***Added***:

* Bump snowflake-connector-python to 3.7.1 ([#17099](https://github.com/DataDog/integrations-core/pull/17099))

## 5.3.0 / 2024-02-16

***Added***:

* Update dependencies ([#16788](https://github.com/DataDog/integrations-core/pull/16788))

## 5.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Added `schema` and `database` tags to snowpipe metrics. ([#16222](https://github.com/DataDog/integrations-core/pull/16222))
* Bump the snowflake version to 3.5.0 ([#16324](https://github.com/DataDog/integrations-core/pull/16324))
* Update dependencies ([#16394](https://github.com/DataDog/integrations-core/pull/16394))

## 5.1.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Updated dependencies. ([#16154](https://github.com/DataDog/integrations-core/pull/16154))

## 5.0.1 / 2023-10-18

***Fixed***:

* Fixed bug where setting the `aggregate_last_24_hours` option to `true` was not honored when other instances had it set to `false` (the default) ([#16033](https://github.com/DataDog/integrations-core/pull/16033))

## 5.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 4.5.4 / 2023-07-18

***Fixed***:

* Process query rows one at a time to reduce memory footprint ([#15268](https://github.com/DataDog/integrations-core/pull/15268))

## 4.5.3 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump snowflake connector python to 3.0.4 ([#14675](https://github.com/DataDog/integrations-core/pull/14675))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 4.5.2 / 2023-04-14 / Agent 7.45.0

***Fixed***:

* Fix a typo in the `disable_generic_tags` option description ([#14246](https://github.com/DataDog/integrations-core/pull/14246))
* Update snowflake-connector-python to 3.0.0 ([#13926](https://github.com/DataDog/integrations-core/pull/13926))

# 4.5.1 / 2023-03-02

***Fixed***:

* Bump dependency `snowflake-connector-python` to 3.0.1 ([#14073](https://github.com/DataDog/integrations-core/pull/14073))

## 4.5.0 / 2023-01-20 / Agent 7.43.0

***Added***:

* Bump snowflake to 2.8.3 ([#13756](https://github.com/DataDog/integrations-core/pull/13756))

***Fixed***:

* Bump the base check dependency ([#13641](https://github.com/DataDog/integrations-core/pull/13641))

## 4.4.6 / 2023-01-27 / Agent 7.42.1

***Fixed***:

* Bump base check dependency ([#13824](https://github.com/DataDog/integrations-core/pull/13824))
* Backport snowflake-connector-python bump 2.8.3 to 7.42.x ([#13794](https://github.com/DataDog/integrations-core/pull/13794))

## 4.4.5 / 2022-11-28 / Agent 7.42.0

***Fixed***:

* Update Snowflake connector and cryptography dependencies ([#13367](https://github.com/DataDog/integrations-core/pull/13367))
* Remove `default_backend` parameter from cryptography calls ([#13333](https://github.com/DataDog/integrations-core/pull/13333))

## 4.4.4 / 2022-09-19 / Agent 7.40.0

***Fixed***:

* Bump dependencies for 7.40 ([#12896](https://github.com/DataDog/integrations-core/pull/12896))

## 4.4.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 4.4.2 / 2022-07-05 / Agent 7.38.0

***Fixed***:

* Properly read from `token_path` parameter ([#12452](https://github.com/DataDog/integrations-core/pull/12452))

## 4.4.1 / 2022-06-28

***Fixed***:

* Fix organization data transfer query ([#12420](https://github.com/DataDog/integrations-core/pull/12420))

## 4.4.0 / 2022-06-27

***Added***:

* Add support for organization level metrics ([#12375](https://github.com/DataDog/integrations-core/pull/12375))

## 4.3.2 / 2022-06-15

***Fixed***:

* Fix reading of `token_path` option ([#12366](https://github.com/DataDog/integrations-core/pull/12366))

## 4.3.1 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Properly validate `only_custom_queries` ([#11992](https://github.com/DataDog/integrations-core/pull/11992))
* Fix small typo in config option ([#11990](https://github.com/DataDog/integrations-core/pull/11990))
* Add section in docs about private link setup ([#11883](https://github.com/DataDog/integrations-core/pull/11883))

## 4.3.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 4.2.1 / 2022-03-10 / Agent 7.35.0

***Fixed***:

* Convert private key password into string instead of byte ([#11648](https://github.com/DataDog/integrations-core/pull/11648))

## 4.2.0 / 2022-02-19

***Added***:

* Add `pyproject.toml` file ([#11433](https://github.com/DataDog/integrations-core/pull/11433))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 4.1.0 / 2022-01-27

***Added***:

* Refactor snowflake validators ([#11208](https://github.com/DataDog/integrations-core/pull/11208))
* Add key authentication option ([#11180](https://github.com/DataDog/integrations-core/pull/11180))
* Add token_path config option ([#11160](https://github.com/DataDog/integrations-core/pull/11160))
* Add aggregate_last_24_hours option ([#11157](https://github.com/DataDog/integrations-core/pull/11157))

***Fixed***:

* Register private_key_password as secret ([#11215](https://github.com/DataDog/integrations-core/pull/11215))
* Standardize key and token options behaviour ([#11214](https://github.com/DataDog/integrations-core/pull/11214))
* Fix configuration error for custom queries ([#11185](https://github.com/DataDog/integrations-core/pull/11185))

## 4.0.1 / 2021-11-23 / Agent 7.33.0

***Fixed***:

* Fix default field name of schema ([#10714](https://github.com/DataDog/integrations-core/pull/10714))

## 4.0.0 / 2021-10-04 / Agent 7.32.0

***Removed***:

* Drop support for Python 2 and bump requests ([#10105](https://github.com/DataDog/integrations-core/pull/10105))

***Changed***:

* Add test for critical service check and fix namespace ([#10062](https://github.com/DataDog/integrations-core/pull/10062))

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Add runtime configuration validation ([#8983](https://github.com/DataDog/integrations-core/pull/8983))
* Disable generic tags ([#9854](https://github.com/DataDog/integrations-core/pull/9854))

***Fixed***:

* Bump snowflake_connector_python and requests for Py3 ([#10060](https://github.com/DataDog/integrations-core/pull/10060))

## 3.1.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Pin snowflake-connector and requests ([#9905](https://github.com/DataDog/integrations-core/pull/9905))

***Fixed***:

* Revert request bump ([#9912](https://github.com/DataDog/integrations-core/pull/9912))

## 3.0.3 / 2021-07-12 / Agent 7.30.0

***Fixed***:

* Bump base package dependency ([#9666](https://github.com/DataDog/integrations-core/pull/9666))

## 3.0.2 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))

## 3.0.1 / 2021-01-14 / Agent 7.26.0

***Fixed***:

* Do not throw configuration error for missing password when using OAuth ([#8363](https://github.com/DataDog/integrations-core/pull/8363))

## 3.0.0 / 2020-12-11 / Agent 7.25.0

***Changed***:

* Make role configuration step more explicit ([#8092](https://github.com/DataDog/integrations-core/pull/8092))

***Added***:

* Support proxy settings ([#8019](https://github.com/DataDog/integrations-core/pull/8019))

***Fixed***:

* Document Snowflake connector proxy configuration and support proxy connection options ([#8181](https://github.com/DataDog/integrations-core/pull/8181))

## 2.1.2 / 2020-11-06 / Agent 7.24.0

***Fixed***:

* Add workaround for issue in platform.platform() on python 3.8 or later ([#7932](https://github.com/DataDog/integrations-core/pull/7932)) Thanks [kurochan](https://github.com/kurochan).

## 2.1.1 / 2020-11-06

***Fixed***:

* Override the default `min_collection_interval` ([#7949](https://github.com/DataDog/integrations-core/pull/7949))

## 2.1.0 / 2020-10-31

***Added***:

* Make improvements to documentation ([#7902](https://github.com/DataDog/integrations-core/pull/7902))

***Fixed***:

* Properly pin base package version for new QueryManager feature ([#7832](https://github.com/DataDog/integrations-core/pull/7832))

## 2.1.0 / 2020-10-21

***Added***:

* Added bytes_spilled metrics ([#7810](https://github)com/DataDog/integrations-core/pull/7810)

## 2.0.1 / 2020-10-21

***Fixed***:

* Fixed Snowflake 2.0.0 release to remove unreleased QueryManager breaking change.

## 2.0.0 / 2020-10-13

***Changed***:

* QueryManager - Prevent queries leaking between check instances ([#7750](https://github.com/DataDog/integrations-core/pull/7750))

***Added***:

* Add OAuth authentication option and use new connection on check run ([#7703](https://github.com/DataDog/integrations-core/pull/7703))

## 1.0.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* New Integration: Snowflake ([#7043](https://github.com/DataDog/integrations-core/pull/7043))
