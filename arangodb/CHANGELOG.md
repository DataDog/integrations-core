# CHANGELOG - ArangoDB

<!-- towncrier release notes start -->

## 3.2.0 / 2025-01-16

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 3.1.0 / 2024-10-04 / Agent 7.59.0

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 3.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 2.2.2 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 2.2.1 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 2.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 2.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.4.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.4.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Add DEFAULT_METRIC_LIMIT for OpenMetrics-based checks ([#14527](https://github.com/DataDog/integrations-core/pull/14527))
* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 1.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 1.2.0 / 2022-06-27 / Agent 7.38.0

***Added***:

* Add connectivity metrics ([#12093](https://github.com/DataDog/integrations-core/pull/12093))

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 1.1.0 / 2022-05-27 / Agent 7.37.0

***Added***:

* Add connectivity metrics ([#12093](https://github.com/DataDog/integrations-core/pull/12093))

## 1.0.1 / 2022-05-18

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 1.0.0 / 2022-05-13

***Added***:

* Add ArangoDB integration ([#11292](https://github.com/DataDog/integrations-core/pull/11292))
