# CHANGELOG - gitlab

## 4.2.0 / 2020-08-10

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 4.1.0 / 2020-06-29

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 4.0.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add config spec. See [#6151](https://github.com/DataDog/integrations-core/pull/6151).
* [Changed] Remove duplicates in metadata and assert metrics with metadata. See [#6516](https://github.com/DataDog/integrations-core/pull/6516).

## 3.0.0 / 2020-04-04

* [Added] Add new gitlab metrics. See [#6166](https://github.com/DataDog/integrations-core/pull/6166).
* [Added] Include gitlab host and port tag for all metrics. See [#6177](https://github.com/DataDog/integrations-core/pull/6177).
* [Added] Add version metadata. See [#5786](https://github.com/DataDog/integrations-core/pull/5786).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Changed] Remap gitlab metrics. See [#6150](https://github.com/DataDog/integrations-core/pull/6150).
* [Changed] Gitlab revamp. See [#5971](https://github.com/DataDog/integrations-core/pull/5971).

## 2.8.1 / 2020-02-22

* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 2.8.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 2.7.0 / 2019-12-02

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 2.6.1 / 2019-10-17

* [Fixed] Add missing go_memstats_stack_sys_bytes metric in conf file. See [#4800](https://github.com/DataDog/integrations-core/pull/4800).

## 2.6.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 2.5.1 / 2019-08-30

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 2.5.0 / 2019-08-24

* [Added] Add requests wrapper to gitlab. See [#4216](https://github.com/DataDog/integrations-core/pull/4216).

## 2.4.0 / 2019-07-04

* [Added] Add logs. See [#3948](https://github.com/DataDog/integrations-core/pull/3948).

## 2.3.0 / 2019-05-14

* [Added] Adhere to code style. See [#3509](https://github.com/DataDog/integrations-core/pull/3509).

## 2.2.0 / 2019-03-29

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 2.1.0 / 2019-01-04

* [Added] Support Python 3. See [#2751][1].

## 2.0.0 / 2018-10-12

* [Changed] Update gitlab to use the new OpenMetricsBaseCheck. See [#1977][2].

## 1.2.0 / 2018-09-04

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][3].
* [Fixed] Add data files to the wheel package. See [#1727][4].

## 1.1.0 / 2018-03-23

* [FEATURE] Add support for instance level checks in service check.

## 1.0.0 / 2018-01-10

* [FEATURE] Add integration for Gitlab.
[1]: https://github.com/DataDog/integrations-core/pull/2751
[2]: https://github.com/DataDog/integrations-core/pull/1977
[3]: https://github.com/DataDog/integrations-core/pull/2093
[4]: https://github.com/DataDog/integrations-core/pull/1727
