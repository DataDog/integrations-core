# CHANGELOG - openstack

<!-- towncrier release notes start -->

## 2.0.0 / 2024-01-05 / Agent 7.51.0

***Changed***:

* Add missing config_models files and update the base check version ([#16299](https://github.com/DataDog/integrations-core/pull/16299))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 1.13.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.13.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 1.13.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 1.12.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11408](https://github.com/DataDog/integrations-core/pull/11408))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.11.1 / 2021-10-04 / Agent 7.32.0

***Fixed***:

* Add server as generic tag ([#10100](https://github.com/DataDog/integrations-core/pull/10100))

## 1.11.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Openstack log support ([#9116](https://github.com/DataDog/integrations-core/pull/9116))

***Fixed***:

* Include missing default config templates ([#9150](https://github.com/DataDog/integrations-core/pull/9150))

## 1.10.3 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.10.2 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 1.10.1 / 2020-06-29 / Agent 7.21.0

***Fixed***:

* Use agent v6 init signature ([#6830](https://github.com/DataDog/integrations-core/pull/6830))

## 1.10.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.9.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 1.9.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.8.3 / 2019-10-11 / Agent 6.15.0

***Fixed***:

* Fix documented default for `use_agent_proxy` ([#4517](https://github.com/DataDog/integrations-core/pull/4517))

## 1.8.2 / 2019-08-24 / Agent 6.14.0

***Fixed***:

* Use utcnow instead of now ([#4192](https://github.com/DataDog/integrations-core/pull/4192))

## 1.8.1 / 2019-06-01 / Agent 6.12.0

***Fixed***:

* Fix code style ([#3838](https://github.com/DataDog/integrations-core/pull/3838))
* Sanitize external host tags ([#3792](https://github.com/DataDog/integrations-core/pull/3792))

## 1.8.0 / 2019-05-14

***Added***:

* Adhere to code style ([#3550](https://github.com/DataDog/integrations-core/pull/3550))

## 1.7.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support Python 3 ([#3035](https://github.com/DataDog/integrations-core/pull/3035))

## 1.6.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* Adds ability to Trace "check" function with DD APM ([#2079](https://github.com/DataDog/integrations-core/pull/2079))

## 1.5.0 / 2018-08-29 / Agent 6.5.0

***Fixed***:

* Remove duplicate project call and reword os_host config option ([#2066](https://github.com/DataDog/integrations-core/pull/2066))
* Use is_affirmative on boolean options ([#2071](https://github.com/DataDog/integrations-core/pull/2071))

## 1.4.0 / 2018-08-17

***Changed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

***Fixed***:

* Only use the short hostname when making "host" queries to Nova ([#2070](https://github.com/DataDog/integrations-core/pull/2070))

## 1.3.0 / 2018-06-06

***Added***:

*  Added support for unscoped access, implemented caching mechanism to reduce API calls to Nova ([#1276](https://github.com/DataDog/integrations-core/pull/1276))

## 1.2.0 / 2018-05-11

***Added***:

* Add custom tag support to service check and metrics.

## 1.1.0 / 2018-02-28

***Added***:

* Adds parameter to collect metrics on all projects in a domain ([#1119](https://github)com/DataDog/integrations-core/issues/1119)
* Added support for Agent >= 6.0 ([#1126](https://github)com/DataDog/integrations-core/issues/1126)

***Fixed***:

* Properly disable the Agent's proxy settings when desired ([#1123](https://github)com/DataDog/integrations-core/issues/1123)

## 1.0.2 / 2017-11-21

***Changed***:

* Don't check on powered off VMs ([#878](https://github)com/DataDog/integrations-core/issues/878)

## 1.0.1 / 2017-08-28

***Added***:

* Adds human friendly "project_name" tag in all cases ([#515](https://github)com/DataDog/integrations-core/issues/515)

## 1.0.0 / 2017-03-22

***Added***:

* adds openstack integration.
