# CHANGELOG - ESXi

<!-- towncrier release notes start -->

## 1.2.0 / 2024-07-05

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
