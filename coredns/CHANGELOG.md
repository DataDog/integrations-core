# CHANGELOG - CoreDNS

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

## 3.2.3 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 3.2.2 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 3.2.1 / 2024-03-22 / Agent 7.53.0

***Fixed***:

* Fix a typo in the configuration file ([#17227](https://github.com/DataDog/integrations-core/pull/17227))

## 3.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

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

## 2.4.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.4.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Add DEFAULT_METRIC_LIMIT for OpenMetrics-based checks ([#14527](https://github.com/DataDog/integrations-core/pull/14527))
* Fix coredns documentation ([#14401](https://github.com/DataDog/integrations-core/pull/14401))
* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 2.3.1 / 2023-04-14 / Agent 7.45.0

***Fixed***:

* Fix the url descriptions in the config file ([#14280](https://github.com/DataDog/integrations-core/pull/14280))

## 2.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 2.2.1 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 2.2.0 / 2022-05-15

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11332](https://github.com/DataDog/integrations-core/pull/11332))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Fix License Header Dates ([#11200](https://github.com/DataDog/integrations-core/pull/11200))
* Enable prometheus_url option in auto_conf.yaml ([#11146](https://github.com/DataDog/integrations-core/pull/11146))
* Enable openmetrics_endpoint in auto_conf.yaml ([#11133](https://github.com/DataDog/integrations-core/pull/11133))
* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))
* Fix example config ([#11109](https://github.com/DataDog/integrations-core/pull/11109))

## 1.11.4 / 2022-01-27 / Agent 7.34.0

***Fixed***:

* Fix license header dates ([#11200](https://github.com/DataDog/integrations-core/pull/11200))

## 1.11.3 / 2022-01-21

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 1.11.2 / 2022-01-18

***Fixed***:

* Enable prometheus_url option in auto_conf.yaml ([#11146](https://github.com/DataDog/integrations-core/pull/11146))
* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 1.11.1 / 2022-01-13

***Fixed***:

* Enable openmetrics_endpoint in auto_conf.yaml ([#11133](https://github.com/DataDog/integrations-core/pull/11133))
* Fix example config ([#11109](https://github.com/DataDog/integrations-core/pull/11109))

## 1.11.0 / 2022-01-08

***Added***:

* Add support for OpenMetricsBaseCheckV2 ([#11024](https://github.com/DataDog/integrations-core/pull/11024))

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.10.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Add runtime configuration validation ([#8900](https://github.com/DataDog/integrations-core/pull/8900))
* Update coredns check with v1.8.5 metrics ([#10187](https://github.com/DataDog/integrations-core/pull/10187)) Thanks [vxcodes](https://github.com/vxcodes).

## 1.9.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.8.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))

***Fixed***:

* Fix `metrics` option type for legacy OpenMetrics config spec ([#9318](https://github.com/DataDog/integrations-core/pull/9318)) Thanks [jejikenwogu](https://github.com/jejikenwogu).

## 1.7.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Update defaults for legacy OpenMetrics config spec template ([#9065](https://github.com/DataDog/integrations-core/pull/9065))

## 1.6.2 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.6.1 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Update prometheus_metrics_prefix documentation ([#8236](https://github.com/DataDog/integrations-core/pull/8236))

## 1.6.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Sync openmetrics config specs with new option ignore_metrics_by_labels ([#7823](https://github.com/DataDog/integrations-core/pull/7823))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))
* Add config specs ([#7444](https://github.com/DataDog/integrations-core/pull/7444))

## 1.5.0 / 2020-07-16 / Agent 7.22.0

***Added***:

* Adding new metrics for version 1.7.0 of CoreDNS ([#6973](https://github.com/DataDog/integrations-core/pull/6973))

## 1.4.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

***Fixed***:

* Agent 6 signature ([#6444](https://github.com/DataDog/integrations-core/pull/6444))

## 1.3.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Do not fail on octet stream content type for OpenMetrics ([#5843](https://github.com/DataDog/integrations-core/pull/5843))

## 1.3.0 / 2019-10-29 / Agent 7.16.0

***Added***:

* Add forward metrics ([#4850](https://github.com/DataDog/integrations-core/pull/4850)) Thanks [therc](https://github.com/therc).

## 1.2.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3492](https://github.com/DataDog/integrations-core/pull/3492))

## 1.1.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Add panic_count_total metric to CoreDNS integration ([#2594][1]) Thanks [woopstar][2].

## 1.0.0 / 2018-10-13 / Agent 6.6.0

***Added***:

* Add CoreDNS integration ([#2091][3]) Thanks [shraykay][4].

[1]: https://github.com/DataDog/integrations-core/pull/2594
[2]: https://github.com/woopstar
[3]: https://github.com/DataDog/integrations-core/pull/2091
[4]: https://github.com/shraykay
