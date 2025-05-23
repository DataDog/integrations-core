# CHANGELOG - mapr

<!-- towncrier release notes start -->

## 3.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 2.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 1.11.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 1.10.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))

## 1.10.0 / 2023-08-10

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.9.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.9.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 1.9.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 1.8.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11392](https://github.com/DataDog/integrations-core/pull/11392))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.7.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.7.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

## 1.6.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Disable generic tags ([#9791](https://github.com/DataDog/integrations-core/pull/9791))

***Fixed***:

* Fix typos in log lines ([#9907](https://github.com/DataDog/integrations-core/pull/9907))
* Bump base package requirement ([#9838](https://github.com/DataDog/integrations-core/pull/9838))

## 1.5.0 / 2021-07-12 / Agent 7.30.0

***Added***:

* More precise errors ([#9453](https://github.com/DataDog/integrations-core/pull/9453))

## 1.4.1 / 2021-05-20 / Agent 7.29.0

***Fixed***:

* Fix init failure when auth_ticket is not provided ([#9390](https://github.com/DataDog/integrations-core/pull/9390))
* Fixup for an AttributeError ([#9343](https://github.com/DataDog/integrations-core/pull/9343))

## 1.4.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Add runtime configuration validation ([#8950](https://github.com/DataDog/integrations-core/pull/8950))

## 1.3.1 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.3.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.2.0 / 2020-02-10 / Agent 7.18.0

***Added***:

* Improve logging and documentation ([#5644](https://github.com/DataDog/integrations-core/pull/5644))

***Fixed***:

* Fix service check "topic" tag ([#5679](https://github.com/DataDog/integrations-core/pull/5679))

## 1.1.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.0.1 / 2019-12-02 / Agent 7.16.0

***Fixed***:

* Fix use of format in logging ([#4973](https://github.com/DataDog/integrations-core/pull/4973))

## 1.0.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* New MapR integration ([#4380](https://github.com/DataDog/integrations-core/pull/4380))
