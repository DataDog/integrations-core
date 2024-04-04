# CHANGELOG - Kube_controller_manager

<!-- towncrier release notes start -->

## 5.1.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 5.0.0 / 2024-01-05 / Agent 7.51.0

***Changed***:

* Add missing config_models files and update the base check version ([#16297](https://github.com/DataDog/integrations-core/pull/16297))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.6.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add support for kube_controller_manager SLI metrics ([#15914](https://github.com/DataDog/integrations-core/pull/15914))

## 4.5.0 / 2023-09-29 / Agent 7.49.0

***Added***:

* Capture node_collector_evictions_total metric in kube controller manager ([#15737](https://github.com/DataDog/integrations-core/pull/15737))

## 4.4.0 / 2023-08-10 / Agent 7.48.0

***Added***:

* Add job_controller_terminated_pods_tracking_finalizer_total metric to kube controller manager check ([#15425](https://github.com/DataDog/integrations-core/pull/15425))

## 4.3.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 4.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 4.2.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

## 4.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 4.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11381](https://github.com/DataDog/integrations-core/pull/11381))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 3.0.1 / 2022-01-18 / Agent 7.34.0

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 3.0.0 / 2022-01-08

***Changed***:

* Update the default value of the `bearer_token` parameter to send the bearer token only to secure https endpoints by default ([#10708](https://github.com/DataDog/integrations-core/pull/10708))

***Added***:

* Add kube_controller_manager config spec ([#10505](https://github.com/DataDog/integrations-core/pull/10505))

***Fixed***:

* Sync configuration spec ([#10938](https://github.com/DataDog/integrations-core/pull/10938))

## 2.0.1 / 2021-08-25 / Agent 7.31.0

***Fixed***:

* Correctly use SSL options for health checks ([#9977](https://github.com/DataDog/integrations-core/pull/9977))

## 2.0.0 / 2021-08-22

***Changed***:

* Add service check for K8s API Server components ([#9773](https://github.com/DataDog/integrations-core/pull/9773))

## 1.9.0 / 2021-07-12 / Agent 7.30.0

***Added***:

* Fix auto-discovery for latest versions on Kubernetes ([#9575](https://github.com/DataDog/integrations-core/pull/9575))

## 1.8.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Add support for Kubernetes leader election based on Lease objects ([#8535](https://github.com/DataDog/integrations-core/pull/8535))

***Fixed***:

* Bump minimum base package version ([#8770](https://github.com/DataDog/integrations-core/pull/8770) and [#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.7.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.6.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 1.6.0 / 2020-02-22 / Agent 7.18.0

***Added***:

* Add auto_conf.yaml files ([#5678](https://github.com/DataDog/integrations-core/pull/5678))

## 1.5.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))

***Fixed***:

* Fix logger method bug ([#5395](https://github.com/DataDog/integrations-core/pull/5395))

## 1.4.0 / 2019-07-19 / Agent 6.13.0

***Added***:

* Add telemetry metrics counter by ksm collector ([#4125](https://github.com/DataDog/integrations-core/pull/4125))

## 1.3.0 / 2019-07-04

***Added***:

* Add support for new metrics introduced in kubernetes v1.14 ([#3905](https://github.com/DataDog/integrations-core/pull/3905))

## 1.2.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3527](https://github.com/DataDog/integrations-core/pull/3527))

***Fixed***:

* Fix the list of default rate limiters ([#3724](https://github.com/DataDog/integrations-core/pull/3724))

## 1.1.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Track leader election status ([#3101](https://github.com/DataDog/integrations-core/pull/3101))

***Fixed***:

* Resolve flake8 issues ([#3060](https://github.com/DataDog/integrations-core/pull/3060))
