# CHANGELOG - SAP HANA

<!-- towncrier release notes start -->

## 5.1.0 / 2025-01-16 / Agent 7.63.0

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 5.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

## 4.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 3.3.0 / 2024-08-09 / Agent 7.57.0

***Added***:

* Collect audit logs ([#18193](https://github.com/DataDog/integrations-core/pull/18193))

## 3.2.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))

***Fixed***:

* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 3.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 3.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 2.2.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.2.1 / 2022-09-16 / Agent 7.40.0

***Fixed***:

* Change docker image / Do not emit message on OK service check ([#12826](https://github.com/DataDog/integrations-core/pull/12826))

## 2.2.0 / 2022-08-01 / Agent 7.39.0

***Added***:

* Add retries to test and emit warnings when connections fail ([#12528](https://github.com/DataDog/integrations-core/pull/12528))
* Add an option to set the tenant databases schema ([#12492](https://github.com/DataDog/integrations-core/pull/12492))

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* *BREAKING CHANGE* Remove pyhdb ([#11469](https://github.com/DataDog/integrations-core/pull/11469))

***Added***:

* Add `pyproject.toml` file ([#11428](https://github.com/DataDog/integrations-core/pull/11428))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.10.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.10.0 / 2021-11-24

***Added***:

* Add support for only_custom_queries ([#10695](https://github.com/DataDog/integrations-core/pull/10695))

## 1.9.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Support the `hdbcli` client library ([#10595](https://github.com/DataDog/integrations-core/pull/10595))

***Fixed***:

* Resolve unexpected errors when statuses other than 'running' or 'idle' are received ([#10333](https://github.com/DataDog/integrations-core/pull/10333))

## 1.8.2 / 2021-10-15 / Agent 7.32.0

***Fixed***:

* Ensure `persist_db_connections` is read from init_config ([#10417](https://github.com/DataDog/integrations-core/pull/10417))
* Bump base package requirements ([#10390](https://github.com/DataDog/integrations-core/pull/10390))

## 1.8.1 / 2021-10-12

***Fixed***:

* Bump base package requirements ([#10390](https://github.com/DataDog/integrations-core/pull/10390))

## 1.8.0 / 2021-10-04

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))

## 1.7.0 / 2021-09-20

***Added***:

* Add option to disable persistent database connections ([#10023](https://github.com/DataDog/integrations-core/pull/10023))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Add server as generic tag ([#10100](https://github.com/DataDog/integrations-core/pull/10100))

## 1.6.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

## 1.5.0 / 2021-07-12 / Agent 7.30.0

***Added***:

* Add runtime configuration validation ([#8981](https://github.com/DataDog/integrations-core/pull/8981))

## 1.4.1 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Catch exception when closing lost connection ([#8630](https://github.com/DataDog/integrations-core/pull/8630))
* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.4.0 / 2021-01-25 / Agent 7.26.0

***Added***:

* Add SSL support for connection ([#8098](https://github.com/DataDog/integrations-core/pull/8098))

## 1.3.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Add config spec ([#7715](https://github.com/DataDog/integrations-core/pull/7715))

## 1.2.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.1.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.0.0 / 2019-11-11 / Agent 7.16.1

***Added***:

* Add SAP HANA integration ([#4502](https://github.com/DataDog/integrations-core/pull/4502))
