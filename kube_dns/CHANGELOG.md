 - Kube-dns

<!-- towncrier release notes start -->

## 4.4.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

***Fixed***:

* Remove the direct dependency to `protobuf` ([#16572](https://github.com/DataDog/integrations-core/pull/16572))

## 4.3.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.2.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))

## 4.2.0 / 2023-08-10

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 4.1.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 4.0.2 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Revert protobuf dependency update ([#14618](https://github.com/DataDog/integrations-core/pull/14618))
* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))

## 4.0.1 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Fix setting of default health URL for kube_dns, kube_proxy, kube_metrics_server health checks ([#13571](https://github.com/DataDog/integrations-core/pull/13571))

## 4.0.0 / 2022-12-09 / Agent 7.42.0

***Changed***:

* Add health check to kube_* integrations ([#10668](https://github.com/DataDog/integrations-core/pull/10668))

***Fixed***:

* Update protobuf ([#13262](https://github.com/DataDog/integrations-core/pull/13262))

## 3.3.1 / 2022-11-07 / Agent 7.40.1

***Fixed***:

* Bump protobuf version to 3.20.2 ([#13269](https://github.com/DataDog/integrations-core/pull/13269))

## 3.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 3.2.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 3.2.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

***Fixed***:

* Upgrade dependencies ([#11958](https://github.com/DataDog/integrations-core/pull/11958))

## 3.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 3.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11382](https://github.com/DataDog/integrations-core/pull/11382))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Add k8s-dns-kube-dns as default AD identifier ([#11269](https://github.com/DataDog/integrations-core/pull/11269))

## 2.5.1 / 2022-01-18 / Agent 7.34.0

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 2.5.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Add kube_dns config spec ([#10508](https://github.com/DataDog/integrations-core/pull/10508))

## 2.4.2 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.4.1 / 2020-06-29 / Agent 7.21.0

***Fixed***:

* Use agent 6 signature ([#6907](https://github.com/DataDog/integrations-core/pull/6907))

## 2.4.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.3.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 2.3.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3528](https://github.com/DataDog/integrations-core/pull/3528))

## 2.2.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Upgrade protobuf to 3.7.0 ([#3272](https://github.com/DataDog/integrations-core/pull/3272))

## 2.1.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support Python 3 ([#2896](https://github.com/DataDog/integrations-core/pull/2896))

***Fixed***:

* Fix growing CPU and memory usage ([#3066](https://github.com/DataDog/integrations-core/pull/3066))

## 2.0.1 / 2018-10-12 / Agent 6.6.0

***Fixed***:

* Submit metrics with instance tags ([#2299](https://github.com/DataDog/integrations-core/pull/2299))

## 2.0.0 / 2018-09-04 / Agent 6.5.0

***Changed***:

* Update kube_dns to use the new OpenMetricsBaseCheck ([#1980](https://github.com/DataDog/integrations-core/pull/1980))

***Added***:

* Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default ([#2093](https://github.com/DataDog/integrations-core/pull/2093))
* Make HTTP request timeout configurable in prometheus checks ([#1790](https://github.com/DataDog/integrations-core/pull/1790))

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.4.0 / 2018-06-13 / Agent 6.4.0

***Added***:

* Package `auto_conf.yaml` for appropriate integrations ([#1664](https://github.com/DataDog/integrations-core/pull/1664))

## 1.3.0 / 2018-05-11

***Added***:

* Add metrics `kubedns.request_count.count`, `kubedns.error_count.count` and `cachemiss_count.count`, alternative metrics submitted as monotonic\_counts ([#1341](https://github)com/DataDog/integrations-core/issues/1341)

## 1.2.0 / 2018-01-10

***Added***:

* Bumping protobuf to version 3.5.1 ([#965](https://github)com/DataDog/integrations-core/issues/965)

## 1.1.0 / 2017-11-21

***Added***:

* Update auto\_conf template to support agent 6 and 5.20+ ([#860](https://github)com/DataDog/integrations-core/issues/860)

## 1.0.0 / 2017-07-18

***Added***:

* Add kube-dns integration, based on new PrometheusCheck class ([#410](https://github.com/DataDog/integrations-core/issues/410) and [#451](https://github.com/DataDog/integrations-core/issues/451), thanks [@aerostitch](https://github)com/aerostitch)
