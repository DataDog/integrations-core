# CHANGELOG - Datadog-Cluster-Agent

<!-- towncrier release notes start -->

## 6.0.0 / 2025-07-10

***Changed***:

* Update CWS mutating webhook metrics to better track its performance ([#20557](https://github.com/DataDog/integrations-core/pull/20557))
* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 5.5.0 / 2025-02-20 / Agent 7.64.0

***Added***:

* Collect telemetry for autoscaling local fallback ([#19522](https://github.com/DataDog/integrations-core/pull/19522))

## 5.4.0 / 2025-01-25 / Agent 7.63.0

***Added***:

* Add telemetry for checks that are not scheduled. ([#19306](https://github.com/DataDog/integrations-core/pull/19306))

## 5.3.0 / 2025-01-16

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 5.2.0 / 2024-12-26 / Agent 7.62.0

***Added***:

* add telemetry for local load store in dca ([#19229](https://github.com/DataDog/integrations-core/pull/19229))

## 5.1.0 / 2024-10-31 / Agent 7.60.0

***Added***:

* Add telemetry scraping for Validation AdmissionController ([#18867](https://github.com/DataDog/integrations-core/pull/18867))

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

## 3.2.0 / 2024-08-09 / Agent 7.57.0

***Added***:

* Add tagger and workloadmeta metrics ([#18030](https://github.com/DataDog/integrations-core/pull/18030))
* Add telemetry scraping for Autoscaling ([#18265](https://github.com/DataDog/integrations-core/pull/18265))

## 3.1.1 / 2024-05-31 / Agent 7.55.0

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 3.1.0 / 2024-05-07 / Agent 7.54.0

***Added***:

* [datadog-cluster-agent] Add CWS Instrumentation metrics ([#17530](https://github.com/DataDog/integrations-core/pull/17530))

## 3.0.0 / 2024-03-22 / Agent 7.53.0

***Removed***:

* Removed `admission_webhooks.mutation_errors` metric in the `datadog_cluster_agent` integration ([#17195](https://github.com/DataDog/integrations-core/pull/17195))

## 2.11.1 / 2024-02-29 / Agent 7.52.0

***Fixed***:

* Fix process language detection metrics ([#17001](https://github.com/DataDog/integrations-core/pull/17001))

## 2.11.0 / 2024-02-26

***Added***:

* Collect language detection metrics ([#16928](https://github.com/DataDog/integrations-core/pull/16928))

## 2.10.0 / 2024-02-16

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 2.9.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.8.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add `datadog.rate_limit_queries.remaining_min` to default metrics of `datadog_cluster_agent` integration ([#16122](https://github.com/DataDog/integrations-core/pull/16122))

## 2.7.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))

## 2.7.0 / 2023-08-10

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 2.6.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.6.1 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Add DEFAULT_METRIC_LIMIT for OpenMetrics-based checks ([#14527](https://github.com/DataDog/integrations-core/pull/14527))

## 2.6.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Add `external_metrics.api_elapsed` and `external_metrics.api_requests` metrics ([#14369](https://github.com/DataDog/integrations-core/pull/14369))
* Add `admission_webhooks.response_duration` metric ([#14287](https://github.com/DataDog/integrations-core/pull/14287))

## 2.5.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Add rc and patcher metrics ([#13911](https://github.com/DataDog/integrations-core/pull/13911))

## 2.4.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* [datadog_cluster_agent] Add kubernetes_apiserver metrics ([#12935](https://github.com/DataDog/integrations-core/pull/12935))
* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 2.3.0 / 2022-08-05 / Agent 7.39.0

***Added***:

* Collect lib injection metrics ([#12536](https://github.com/DataDog/integrations-core/pull/12536))

## 2.2.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))
* Add endpoint checks and AD metrics ([#11782](https://github.com/DataDog/integrations-core/pull/11782))

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Collect datadog_cluster_agent.cluster_checks.configs_info metric ([#11757](https://github.com/DataDog/integrations-core/pull/11757))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11336](https://github.com/DataDog/integrations-core/pull/11336))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.3.3 / 2022-01-21 / Agent 7.34.0

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 1.3.2 / 2022-01-18

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 1.3.1 / 2022-01-08

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.3.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Collect a metric about valid and invalid DatadogMetrics ([#10525](https://github.com/DataDog/integrations-core/pull/10525))

***Fixed***:

* Add missing metric to datadog_cluster_agent ([#10607](https://github.com/DataDog/integrations-core/pull/10607))

## 1.2.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.1.0 / 2021-08-25

***Added***:

* Add missing metrics ([#9978](https://github.com/DataDog/integrations-core/pull/9978))

## 1.0.0 / 2021-08-22

***Added***:

* Add Datadog Cluster Agent integration ([#9772](https://github.com/DataDog/integrations-core/pull/9772))
