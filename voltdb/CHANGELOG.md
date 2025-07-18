# CHANGELOG - VoltDB

<!-- towncrier release notes start -->

## 6.0.0 / 2025-07-10

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 5.1.0 / 2025-01-16 / Agent 7.63.0

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 5.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 4.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 3.2.1 / 2024-05-31 / Agent 7.55.0

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 3.2.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))

***Fixed***:

* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 3.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 3.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 2.1.3 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.1.2 / 2022-06-27 / Agent 7.38.0

***Fixed***:

* Fix mapping of columns and use delta=1 where required ([#11775](https://github.com/DataDog/integrations-core/pull/11775)) Thanks [kjmadscience](https://github.com/kjmadscience).

## 2.1.1 / 2022-04-14 / Agent 7.36.0

***Fixed***:

* Fix mapping of columns and use delta=1 where required ([#11775](https://github.com/DataDog/integrations-core/pull/11775)) Thanks [kjmadscience](https://github.com/kjmadscience).

## 2.1.0 / 2022-04-05

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

## 2.0.1 / 2022-03-15

***Fixed***:

* Pass Delta flag to calls to Statistics ([#11655](https://github.com/DataDog/integrations-core/pull/11655)) Thanks [ssomagani](https://github.com/ssomagani).
* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11455](https://github.com/DataDog/integrations-core/pull/11455))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.4.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.4.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Echo warning for unnecessary params used ([#10053](https://github.com/DataDog/integrations-core/pull/10053))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.3.1 / 2021-06-01 / Agent 7.29.0

***Fixed***:

* Bump minimum base package requirement ([#9449](https://github.com/DataDog/integrations-core/pull/9449))

## 1.3.0 / 2021-05-28

***Added***:

* Add runtime configuration validation ([#9004](https://github.com/DataDog/integrations-core/pull/9004))

## 1.2.0 / 2021-04-28

***Added***:

* New voltdb metrics ([#9233](https://github.com/DataDog/integrations-core/pull/9233))

## 1.1.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Remove code for legacy workaround ([#8451](https://github.com/DataDog/integrations-core/pull/8451))

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.0.0 / 2021-01-22 / Agent 7.26.0

***Added***:

* Add VoltDB integration ([#7973](https://github.com/DataDog/integrations-core/pull/7973))
