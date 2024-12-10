# CHANGELOG - ESXi

<!-- towncrier release notes start -->

## 3.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

## 2.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 1.2.0 / 2024-07-05 / Agent 7.56.0

***Added***:

* Update dependencies ([#17953](https://github.com/DataDog/integrations-core/pull/17953))

***Fixed***:

* Properly submit percent metrics ([#17745](https://github.com/DataDog/integrations-core/pull/17745))
* Maintain a long lived connection to ESXi host. ([#17919](https://github.com/DataDog/integrations-core/pull/17919))

## 1.1.0 / 2024-05-31 / Agent 7.55.0

***Added***:

* Add option to use configured host as hostname. ([#17544](https://github.com/DataDog/integrations-core/pull/17544))
* Add socks proxy support. ([#17622](https://github.com/DataDog/integrations-core/pull/17622))

***Fixed***:

* Remove invalid host tags ([#17549](https://github.com/DataDog/integrations-core/pull/17549))
* Enable empty_default_hostname by default ([#17595](https://github.com/DataDog/integrations-core/pull/17595))

## 1.0.0 / 2024-04-26 / Agent 7.54.0

***Added***:

* Add ESXi integration ([#17027](https://github.com/DataDog/integrations-core/pull/17027))

***Fixed***:

* Lower log level for missing metric ([#17459](https://github.com/DataDog/integrations-core/pull/17459))
