# CHANGELOG - Argo CD

<!-- towncrier release notes start -->

## 4.0.0 / 2025-07-10

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 3.4.0 / 2025-06-12 / Agent 7.68.0

***Added***:

* Add functionality to collect metrics from [commit server](https://argo-cd.readthedocs.io/en/latest/operator-manual/metrics/#commit-server-metrics) ([#20412](https://github.com/DataDog/integrations-core/pull/20412))

## 3.3.0 / 2025-01-16 / Agent 7.63.0

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 3.2.0 / 2024-11-28 / Agent 7.61.0

***Added***:

* Add new Application Set metrics ([#18961](https://github.com/DataDog/integrations-core/pull/18961))

## 3.1.0 / 2024-10-04 / Agent 7.59.0

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 3.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 2.4.3 / 2024-08-09 / Agent 7.57.0

***Fixed***:

* Fix collection of 2 appset counters ([#18018](https://github.com/DataDog/integrations-core/pull/18018))

## 2.4.2 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 2.4.1 / 2024-05-31

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 2.4.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Collect 'argocd_app_labels' for ArgoCD metric ([#16897](https://github.com/DataDog/integrations-core/pull/16897))

***Fixed***:

* Rename Go inuse_use metric to the correct inuse_bytes name ([#17252](https://github.com/DataDog/integrations-core/pull/17252))

## 2.3.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 2.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.1.0 / 2023-09-29 / Agent 7.49.0

***Added***:

* Collect metrics for ArgoCD ApplicationSet ([#15308](https://github.com/DataDog/integrations-core/pull/15308)) Thanks [smartfin](https://github.com/smartfin).

## 2.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.2.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Add ArgoCD notifications controller metrics ([#14690](https://github.com/DataDog/integrations-core/pull/14690)) Thanks [maxknee](https://github.com/maxknee).

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.1.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 1.0.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Fix error that was triggered by including configuration parameters not ending in `_endpoint` ([#13409](https://github.com/DataDog/integrations-core/pull/13409))

## 1.0.0 / 2022-11-16

***Added***:

* Argo CD Integration ([#13223](https://github.com/DataDog/integrations-core/pull/13223))
