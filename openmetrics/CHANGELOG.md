# CHANGELOG - OpenMetrics

<!-- towncrier release notes start -->

## 7.0.0 / 2025-07-10

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 6.1.0 / 2025-01-16 / Agent 7.63.0

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 6.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 5.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 4.2.2 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 4.2.1 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 4.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 4.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))
* Bump minimum base package version ([#15303](https://github.com/DataDog/integrations-core/pull/15303))
* Revert to requesting Prometheus format by default ([#15292](https://github.com/DataDog/integrations-core/pull/15292))

## 3.0.2 / 2023-07-13 / Agent 7.47.0

***Fixed***:

* Bump the minimum datadog-checks-base version ([#15219](https://github.com/DataDog/integrations-core/pull/15219))

## 3.0.1 / 2023-07-10

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.0.0 / 2023-05-26 / Agent 7.46.0

***Changed***:

* Implement automatic exposition format detection ([#14445](https://github.com/DataDog/integrations-core/pull/14445))

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Fix bug on empty openmetrics scrape response ([#14508](https://github.com/DataDog/integrations-core/pull/14508))
* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 2.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

***Fixed***:

* Bumps base check requirement to v25.4.0 ([#12734](https://github.com/DataDog/integrations-core/pull/12734))

## 2.2.2 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Hide `extra_metrics` in example config ([#12470](https://github.com/DataDog/integrations-core/pull/12470))

## 2.2.1 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 2.2.0 / 2022-05-15

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

***Fixed***:

* Don't tag by endpoint on default config ([#11966](https://github.com/DataDog/integrations-core/pull/11966))
* Fix incorrect OpenMetrics V2 check exposition format HTTP header ([#11899](https://github.com/DataDog/integrations-core/pull/11899)) Thanks [jalaziz](https://github.com/jalaziz).

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11407](https://github.com/DataDog/integrations-core/pull/11407))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.16.3 / 2022-01-21 / Agent 7.34.0

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 1.16.2 / 2022-01-18

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 1.16.1 / 2022-01-08

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.16.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))

## 1.15.2 / 2021-10-15 / Agent 7.32.0

***Fixed***:

* [OpenMetricsV2] Allow empty namespaces ([#10420](https://github.com/DataDog/integrations-core/pull/10420))

## 1.15.1 / 2021-10-08

***Fixed***:

* Allow entire config templates to be hidden and include Openmetrics legacy config option in models ([#10348](https://github.com/DataDog/integrations-core/pull/10348))

## 1.15.0 / 2021-10-04

***Added***:

* Add runtime configuration validation ([#8965](https://github.com/DataDog/integrations-core/pull/8965))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Update documentation for v2 ([#10068](https://github.com/DataDog/integrations-core/pull/10068))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.14.1 / 2021-08-22 / Agent 7.31.0

***Fixed***:

* Update `metrics` option in legacy OpenMetrics example config ([#9891](https://github.com/DataDog/integrations-core/pull/9891))

## 1.14.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))

***Fixed***:

* Fix `metrics` option type for legacy OpenMetrics config spec ([#9318](https://github.com/DataDog/integrations-core/pull/9318)) Thanks [jejikenwogu](https://github.com/jejikenwogu).

## 1.13.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Update defaults for legacy OpenMetrics config spec template ([#9065](https://github.com/DataDog/integrations-core/pull/9065))

## 1.12.1 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.12.0 / 2021-01-25 / Agent 7.26.0

***Added***:

* Allow the use of the new OpenMetrics implementation ([#8440](https://github.com/DataDog/integrations-core/pull/8440))

***Fixed***:

* Update prometheus_metrics_prefix documentation ([#8236](https://github.com/DataDog/integrations-core/pull/8236))

## 1.11.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Sync openmetrics config specs with new option ignore_metrics_by_labels ([#7823](https://github.com/DataDog/integrations-core/pull/7823))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))

## 1.10.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 1.9.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* Support "*" wildcard in type_overrides configuration ([#7071](https://github.com/DataDog/integrations-core/pull/7071))

***Fixed***:

* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 1.8.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 1.7.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Add default template to openmetrics & jmx config ([#6328](https://github.com/DataDog/integrations-core/pull/6328))

***Fixed***:

* Hide openmetrics template options that are typically overridden ([#6338](https://github.com/DataDog/integrations-core/pull/6338))

## 1.6.1 / 2020-04-07 / Agent 7.19.0

***Fixed***:

* Add `kerberos_cache` to HTTP config options ([#6279](https://github.com/DataDog/integrations-core/pull/6279))

## 1.6.0 / 2020-04-04

***Added***:

* Add OpenMetrics config spec template ([#6142](https://github.com/DataDog/integrations-core/pull/6142))
* Allow option to submit histogram/summary sum metric as monotonic count ([#6127](https://github.com/DataDog/integrations-core/pull/6127))

***Fixed***:

* Sync OpenMetrics config ([#6250](https://github.com/DataDog/integrations-core/pull/6250))
* Add `send_distribution_sums_as_monotonic` to openmetrics config spec ([#6247](https://github.com/DataDog/integrations-core/pull/6247))
* Update prometheus_client ([#6200](https://github.com/DataDog/integrations-core/pull/6200))
* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 1.5.0 / 2020-02-22 / Agent 7.18.0

***Added***:

* Make `ignore_metrics` support `*` wildcard for OpenMetrics ([#5759](https://github.com/DataDog/integrations-core/pull/5759))

## 1.4.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))

## 1.3.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Add an option to send histograms/summary counts as monotonic counters ([#4629](https://github.com/DataDog/integrations-core/pull/4629))

## 1.2.0 / 2019-06-01 / Agent 6.12.0

***Added***:

* Use Kube service account bearer token for authentication ([#3829](https://github.com/DataDog/integrations-core/pull/3829))

## 1.1.0 / 2019-05-14

***Added***:

* Adhere to code style ([#3549](https://github.com/DataDog/integrations-core/pull/3549))

***Fixed***:

* Fix type override values in example config ([#3717](https://github.com/DataDog/integrations-core/pull/3717))

## 1.0.0 / 2018-10-13 / Agent 6.6.0

***Added***:

* Add OpenMetrics integration ([#2148](https://github.com/DataDog/integrations-core/pull/2148))
