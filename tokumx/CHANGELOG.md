# CHANGELOG - tokumx

<!-- towncrier release notes start -->

## 3.2.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Add metric_patterns options to filter all metric submission with a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))

## 3.1.1 / 2022-02-23 / Agent 7.35.0

***Fixed***:

* Properly indicate Python constraints ([#11555](https://github.com/DataDog/integrations-core/pull/11555))

## 3.1.0 / 2022-02-19

***Added***:

* Add `pyproject.toml` file ([#11448](https://github.com/DataDog/integrations-core/pull/11448))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 3.0.0 / 2022-01-08 / Agent 7.34.0

***Changed***:

* Add `server` default group for all monitor special cases ([#10976](https://github.com/DataDog/integrations-core/pull/10976))

## 2.3.3 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.3.2 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))
* Use consistent formatting for boolean values ([#7405](https://github.com/DataDog/integrations-core/pull/7405))

## 2.3.1 / 2020-06-29 / Agent 7.21.0

***Fixed***:

* Add config specs and change signature ([#6729](https://github.com/DataDog/integrations-core/pull/6729))

## 2.3.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.2.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 2.2.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 2.1.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3576](https://github.com/DataDog/integrations-core/pull/3576))

## 2.0.0 / 2019-02-18 / Agent 6.10.0

***Changed***:

* Vendor pymongo into tokumx check ([#3001](https://github.com/DataDog/integrations-core/pull/3001))

***Added***:

* Finish Python 3 Support ([#2926](https://github.com/DataDog/integrations-core/pull/2926))

***Fixed***:

* Resolve flake8 issues ([#3060](https://github.com/DataDog/integrations-core/pull/3060))

## 1.3.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* Support Python 3 ([#2832](https://github.com/DataDog/integrations-core/pull/2832))

## 1.2.1 / 2018-09-04 / Agent 6.5.0

***Fixed***:

* Moves Tokumx to pytest ([#2134](https://github.com/DataDog/integrations-core/pull/2134))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.2.0 / 2018-05-11

***Added***:

* Adds custom tag support to service checks.

## 1.1.0 / 2017-11-21

***Added***:

* Upgrading pymongo to version 3.5 ([#842](https://github)com/DataDog/integrations-core/issues/842)

## 1.0.0 / 2017-03-22

***Added***:

* adds tokumx integration.
