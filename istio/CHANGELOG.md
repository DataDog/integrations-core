# CHANGELOG - istio

## 3.5.0 / 2020-08-10

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 3.4.0 / 2020-06-29

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 3.3.0 / 2020-06-09

* [Added] Enable `send_monotonic_with_gauge` to submit mesh metrics as monotonic counts. See [#5707](https://github.com/DataDog/integrations-core/pull/5707).

## 3.2.1 / 2020-05-22

* [Fixed] Remove `destination_service` and `source_workload` from label blacklist. See [#6712](https://github.com/DataDog/integrations-core/pull/6712).

## 3.2.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add TCP mesh metrics mapping. See [#6466](https://github.com/DataDog/integrations-core/pull/6466).

## 3.1.0 / 2020-04-23

* [Added] Add autodiscovery config and default tag exclusion. See [#6375](https://github.com/DataDog/integrations-core/pull/6375).
* [Added] Support istiod metrics. See [#6426](https://github.com/DataDog/integrations-core/pull/6426).
* [Added] Refactor to support different versions of istio. See [#6360](https://github.com/DataDog/integrations-core/pull/6360).
* [Added] Add configuration template spec. See [#6320](https://github.com/DataDog/integrations-core/pull/6320).
* [Added] Refactor check and support new Agent signature. See [#6341](https://github.com/DataDog/integrations-core/pull/6341).

## 3.0.0 / 2020-04-04

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Do not fail on octet stream content type for OpenMetrics. See [#5843](https://github.com/DataDog/integrations-core/pull/5843).
* [Changed] Blacklist metric `mcp_source.request_acks_total` due to high cardinality. See [#6185](https://github.com/DataDog/integrations-core/pull/6185).

## 2.4.2 / 2019-08-26

* [Fixed] Blacklist `galley_mcp_source_message_size_bytes` histogram. See [#4433](https://github.com/DataDog/integrations-core/pull/4433).

## 2.4.1 / 2019-07-16

* [Fixed] Comment out mixer and mesh by default from configuration. See [#4121](https://github.com/DataDog/integrations-core/pull/4121).

## 2.4.0 / 2019-06-24

* [Added] Support citadel endpoint. See [#3962](https://github.com/DataDog/integrations-core/pull/3962).

## 2.3.1 / 2019-06-19

* [Fixed] Istio Mixer and Mesh endpoints should be optional. See [#3875](https://github.com/DataDog/integrations-core/pull/3875). Thanks [mikekatica](https://github.com/mikekatica).

## 2.3.0 / 2019-05-31

* [Added] Support pilot and galley metrics. See [#3734](https://github.com/DataDog/integrations-core/pull/3734).

## 2.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3522](https://github.com/DataDog/integrations-core/pull/3522).

## 2.1.0 / 2019-02-18

* [Fixed] Update example config to match docs. See [#3046](https://github.com/DataDog/integrations-core/pull/3046).
* [Added] Support Python 3. See [#3014](https://github.com/DataDog/integrations-core/pull/3014).

## 2.0.0 / 2018-09-04

* [Changed] Update istio to use the new OpenMetricsBaseCheck. See [#1979][1].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Added] Update istio mapped metrics. See [#1993][3]. Thanks [bobbytables][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-06-07

* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581][6].

## 1.0.0 / 2018-03-23

* [FEATURE] Adds Istio Integration
[1]: https://github.com/DataDog/integrations-core/pull/1979
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1993
[4]: https://github.com/bobbytables
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1581
