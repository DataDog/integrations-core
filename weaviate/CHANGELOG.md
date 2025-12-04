# CHANGELOG - Weaviate

<!-- towncrier release notes start -->

## 4.2.0 / 2025-11-26

***Added***:

* Bump minimum version of datadog-checks-base to 37.24.0 ([#21945](https://github.com/DataDog/integrations-core/pull/21945))

## 4.1.1 / 2025-10-31

***Fixed***:

* Add allowed values list on kerberos_auth field ([#20879](https://github.com/DataDog/integrations-core/pull/20879))

## 4.1.0 / 2025-10-02 / Agent 7.72.0

***Added***:

* Bump Python to 3.13 ([#21161](https://github.com/DataDog/integrations-core/pull/21161))
* Bump datadog-checks-base to 37.21.0 ([#21477](https://github.com/DataDog/integrations-core/pull/21477))

## 4.0.1 / 2025-08-07 / Agent 7.70.0

***Fixed***:

* Improve descriptions and examples in example configuration file ([#20878](https://github.com/DataDog/integrations-core/pull/20878))

## 4.0.0 / 2025-07-10 / Agent 7.69.0

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 3.2.0 / 2025-01-16 / Agent 7.63.0

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

## 2.3.3 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 2.3.2 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 2.3.1 / 2024-03-22 / Agent 7.53.0

***Fixed***:

* Rename Go inuse_use metric to the correct inuse_bytes name ([#17252](https://github.com/DataDog/integrations-core/pull/17252))

## 2.3.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 2.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.1.0 / 2023-08-18 / Agent 7.48.0

***Added***:

* Add weaviate.requests metric ([#15583](https://github.com/DataDog/integrations-core/pull/15583))

## 2.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.0.0 / 2023-07-07 / Agent 7.47.0

***Added***:

* Add the Weaviate integration ([#15081](https://github.com/DataDog/integrations-core/pull/15081))
