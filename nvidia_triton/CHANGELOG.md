# CHANGELOG - Nvidia Triton

<!-- towncrier release notes start -->

## 2.0.0 / 2024-10-01

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

## 1.2.2 / 2024-07-05 / Agent 7.55.0

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

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Nvidia Triton supports log collection:
  - Add configuration section for logs.
  - Add documentation section about logs.
  - Add classifier for log collection. ([#16438](https://github.com/DataDog/integrations-core/pull/16438))

## 1.0.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add Nvidia Triton integration. ([#15918](https://github.com/DataDog/integrations-core/pull/15918))
