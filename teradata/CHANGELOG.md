# CHANGELOG - Teradata

<!-- towncrier release notes start -->

## 4.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 3.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 2.2.1 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 2.2.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))

***Fixed***:

* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 2.1.1 / 2024-01-15 / Agent 7.51.0

***Fixed***:

* Fix incompatibility issues with Python 3.9 and lower ([#16608](https://github.com/DataDog/integrations-core/pull/16608))

## 2.1.0 / 2024-01-05

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.1.2 / 2023-07-13 / Agent 7.47.0

***Fixed***:

* Bump the minimum datadog-checks-base version ([#15217](https://github.com/DataDog/integrations-core/pull/15217))

## 1.1.1 / 2023-07-10

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.1.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Refactor tooling for getting the current env name ([#12939](https://github.com/DataDog/integrations-core/pull/12939))

## 1.0.1 / 2022-06-27 / Agent 7.38.0

***Fixed***:

* Refactor util method signatures ([#12063](https://github.com/DataDog/integrations-core/pull/12063))
* Add error handling when collecting version ([#12062](https://github.com/DataDog/integrations-core/pull/12062))

## 1.0.0 / 2022-05-13 / Agent 7.37.0

***Added***:

* Add Teradata integration ([#11701](https://github.com/DataDog/integrations-core/pull/11701))
