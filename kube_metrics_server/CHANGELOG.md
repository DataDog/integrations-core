# CHANGELOG - Kube Metrics Server

<!-- towncrier release notes start -->

## 3.3.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 3.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 3.1.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))

## 3.1.0 / 2023-08-10

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 3.0.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.0.1 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Fix setting of default health URL for kube_dns, kube_proxy, kube_metrics_server health checks ([#13571](https://github.com/DataDog/integrations-core/pull/13571))

## 3.0.0 / 2022-12-09 / Agent 7.42.0

***Changed***:

* Add health check to kube_* integrations ([#10668](https://github.com/DataDog/integrations-core/pull/10668))

## 2.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 2.2.0 / 2022-05-15 / Agent 7.37.0

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

* Add `pyproject.toml` file ([#11383](https://github.com/DataDog/integrations-core/pull/11383))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.4.1 / 2022-01-18 / Agent 7.34.0

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 1.4.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Add kube_metrics_server config spec ([#10509](https://github.com/DataDog/integrations-core/pull/10509))

## 1.3.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Support 0.4.0 metrics server renamed metric names ([#9202](https://github.com/DataDog/integrations-core/pull/9202)) Thanks [eatwithforks](https://github.com/eatwithforks).

## 1.2.1 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.2.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.1.1 / 2020-02-22 / Agent 7.18.0

***Fixed***:

* Fix metric validation ([#5581](https://github.com/DataDog/integrations-core/pull/5581))

## 1.1.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))

## 1.0.1 / 2019-08-24 / Agent 6.14.0

***Fixed***:

* Fix prometheus_url conf ([#4175](https://github.com/DataDog/integrations-core/pull/4175))

## 1.0.0 / 2019-06-01 / Agent 6.12.0

***Added***:

* Add Kube metrics server integration ([#3666](https://github.com/DataDog/integrations-core/pull/3666))
