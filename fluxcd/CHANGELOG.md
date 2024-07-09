# CHANGELOG - fluxcd

<!-- towncrier release notes start -->

## 1.2.2 / 2024-07-05

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 1.2.1 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 1.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 1.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Add more metrics and official Fluxcd v2 support. ([#16117](https://github.com/DataDog/integrations-core/pull/16117))

***Fixed***:

* Bump base check dependency version to ensure Pydantic v2 support. ([#16117](https://github.com/DataDog/integrations-core/pull/16117))
* Correct config models for OpenMetrics check. ([#16117](https://github.com/DataDog/integrations-core/pull/16117))

## 1.0.0 / 2023-11-08

***Changed***:

* Config models update - PR [2088](https://github.com/DataDog/integrations-extras/pull/2088)

## 0.0.1

***Added***:

* Initial Fluxcd Integration.
