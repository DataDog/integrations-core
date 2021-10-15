# CHANGELOG - Amazon MSK

## 2.0.1 / 2021-10-12

* [Fixed] Account for errors in boto client creation. See [#10386](https://github.com/DataDog/integrations-core/pull/10386).

## 2.0.0 / 2021-10-04

* [Added] Update dependencies. See [#10228](https://github.com/DataDog/integrations-core/pull/10228).
* [Added] Add proxy support in client initialization. See [#10188](https://github.com/DataDog/integrations-core/pull/10188).
* [Added] Add HTTP option to control the size of streaming responses. See [#10183](https://github.com/DataDog/integrations-core/pull/10183).
* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).
* [Fixed] Fix the description of the `allow_redirects` HTTP option. See [#10195](https://github.com/DataDog/integrations-core/pull/10195).
* [Changed] Update Amazon MSK documentation to the new implementation. See [#9993](https://github.com/DataDog/integrations-core/pull/9993).

## 1.8.1 / 2021-07-16 / Agent 7.30.0

* [Fixed] Describe py3 requirement of use_openmetrics option. See [#9714](https://github.com/DataDog/integrations-core/pull/9714).

## 1.8.0 / 2021-07-12

* [Added] Add metrics from label IDs. See [#9643](https://github.com/DataDog/integrations-core/pull/9643).
* [Added] Upgrade some core dependencies. See [#9499](https://github.com/DataDog/integrations-core/pull/9499).
* [Fixed] Raise exception if attempting to use new style openmetrics with py2. See [#9613](https://github.com/DataDog/integrations-core/pull/9613).

## 1.7.0 / 2021-05-28 / Agent 7.29.0

* [Added] Support "ignore_tags" configuration. See [#9392](https://github.com/DataDog/integrations-core/pull/9392).
* [Fixed] Fix `metrics` option type for legacy OpenMetrics config spec. See [#9318](https://github.com/DataDog/integrations-core/pull/9318). Thanks [jejikenwogu](https://github.com/jejikenwogu).

## 1.6.0 / 2021-04-19 / Agent 7.28.0

* [Added] Allow the use of the new OpenMetrics implementation. See [#9082](https://github.com/DataDog/integrations-core/pull/9082).
* [Added] Add runtime configuration validation. See [#8883](https://github.com/DataDog/integrations-core/pull/8883).
* [Fixed] Bump minimum base package. See [#9107](https://github.com/DataDog/integrations-core/pull/9107).

## 1.5.0 / 2021-03-24

* [Added] Add `kafka_consumer_group_ConsumerLagMetrics_Value` metric. See [#9027](https://github.com/DataDog/integrations-core/pull/9027). Thanks [idarlington](https://github.com/idarlington).
* [Added] Allow prometheus metrics path to be configurable. See [#9028](https://github.com/DataDog/integrations-core/pull/9028).

## 1.4.1 / 2021-01-25 / Agent 7.26.0

* [Fixed] Hide auto-populated prometheus_url from config spec. See [#8330](https://github.com/DataDog/integrations-core/pull/8330).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.4.0 / 2020-12-11 / Agent 7.25.0

* [Added] Add ability to assume a specified role when retrieving MSK metadata. See [#8118](https://github.com/DataDog/integrations-core/pull/8118). Thanks [garrett528](https://github.com/garrett528).

## 1.3.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.2.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Add config specs. See [#7291](https://github.com/DataDog/integrations-core/pull/7291).

## 1.1.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.0.0 / 2019-12-03 / Agent 7.16.1

* [Added] Add Amazon MSK integration. See [#5127](https://github.com/DataDog/integrations-core/pull/5127).

