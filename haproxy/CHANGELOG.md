# CHANGELOG - haproxy

## 2.16.0 / 2021-01-24

* [Added] Revert "Update base package pin (#8426)". See [#8436](https://github.com/DataDog/integrations-core/pull/8436).
* [Fixed] Remove class substitution logic for new OpenMetrics base class. See [#8435](https://github.com/DataDog/integrations-core/pull/8435).

## 2.15.0 / 2021-01-22

* [Added] Update base package pin. See [#8426](https://github.com/DataDog/integrations-core/pull/8426).
* [Fixed] Adding support for v2.3. See [#8325](https://github.com/DataDog/integrations-core/pull/8325). Thanks [wdauchy](https://github.com/wdauchy).

## 2.14.2 / 2021-01-11

* [Fixed] Fix typo for ssl reuse metric. See [#8203](https://github.com/DataDog/integrations-core/pull/8203). Thanks [wdauchy](https://github.com/wdauchy).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 2.14.1 / 2020-11-24 / Agent 7.25.0

* [Fixed] Increase robustness of parsing of Unix socket responses in legacy implementation. See [#8080](https://github.com/DataDog/integrations-core/pull/8080).

## 2.14.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 2.13.0 / 2020-10-06

* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Added] Send bytes.in/out.total metrics to legacy implementation. See [#7722](https://github.com/DataDog/integrations-core/pull/7722).

## 2.12.0 / 2020-09-30

* [Added] Add new implementation to support Prometheus endpoint. See [#7620](https://github.com/DataDog/integrations-core/pull/7620).

## 2.11.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add config spec. See [#7625](https://github.com/DataDog/integrations-core/pull/7625).
* [Added] Refactor check to support new implementation. See [#7587](https://github.com/DataDog/integrations-core/pull/7587).
* [Added] Do not use instance in check method. See [#7534](https://github.com/DataDog/integrations-core/pull/7534).
* [Fixed] Extract version utils. See [#7533](https://github.com/DataDog/integrations-core/pull/7533).

## 2.10.2 / 2020-09-09

* [Fixed] Add regex tags in status metrics. See [#7524](https://github.com/DataDog/integrations-core/pull/7524).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 2.10.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 2.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix version parsing with haproxy enterprise version. See [#6774](https://github.com/DataDog/integrations-core/pull/6774).

## 2.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.8.1 / 2020-05-05 / Agent 7.19.2

* [Fixed] Handle empty response from show table. See [#6579](https://github.com/DataDog/integrations-core/pull/6579).

## 2.8.0 / 2020-04-04 / Agent 7.19.0

* [Added] Gather stick-table metrics. See [#6158](https://github.com/DataDog/integrations-core/pull/6158).
* [Fixed] Revert `to_native_string` to `to_string` for integrations. See [#6238](https://github.com/DataDog/integrations-core/pull/6238).

## 2.7.2 / 2020-03-24

* [Fixed] Fix event submission on Python 3. See [#6138](https://github.com/DataDog/integrations-core/pull/6138).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Rename `to_string()` utility to `to_native_string()`. See [#5996](https://github.com/DataDog/integrations-core/pull/5996).

## 2.7.1 / 2020-02-25 / Agent 7.18.0

* [Fixed] Document disable_legacy_service_tag and bump checks_base requirement. See [#5835](https://github.com/DataDog/integrations-core/pull/5835).

## 2.7.0 / 2020-02-22

* [Added] Add an option to skip reporting during restarts. See [#5571](https://github.com/DataDog/integrations-core/pull/5571). Thanks [dd-adn](https://github.com/dd-adn).
* [Deprecated] Deprecate `service` tag. See [#5550](https://github.com/DataDog/integrations-core/pull/5550).

## 2.6.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.5.1 / 2019-12-13 / Agent 7.16.0

* [Fixed] Handle failure on version endpoint. See [#5208](https://github.com/DataDog/integrations-core/pull/5208).

## 2.5.0 / 2019-12-02

* [Added] Submit version metadata. See [#4851](https://github.com/DataDog/integrations-core/pull/4851).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 2.4.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 2.3.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add requests wrapper to haproxy. See [#4219](https://github.com/DataDog/integrations-core/pull/4219).

## 2.2.0 / 2019-06-01 / Agent 6.12.0

* [Added] Add `requests.tot_rate`, `connections.rate`, `connections.tot_rate`, and `requests.intercepted`. See [#3797](https://github.com/DataDog/integrations-core/pull/3797).
* [Added] `collect_aggregates_only` now collects all values when set to `false`. See [#3797](https://github.com/DataDog/integrations-core/pull/3797).

## 2.1.0 / 2019-05-14

* [Added] Adhere to code style. See [#3513](https://github.com/DataDog/integrations-core/pull/3513).

## 2.0.0 / 2019-02-18 / Agent 6.10.0

* [Changed] Only send 'haproxy.backend_hosts' metrics for backend. See [#3073](https://github.com/DataDog/integrations-core/pull/3073).
* [Changed] Put service check behind a flag, false by default. See [#3083](https://github.com/DataDog/integrations-core/pull/3083).
* [Added] Support unicode for Python 3 bindings. See [#2869](https://github.com/DataDog/integrations-core/pull/2869).

## 1.4.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2849][1].
* [Added] tcp scheme support for stats socket. See [#2731][2].
* [Added] Add server_address tag when available. See [#2727][3].

## 1.3.2 / 2018-11-30 / Agent 6.8.0

* [Fixed] Use raw string literals when \ is present. See [#2465][4].

## 1.3.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Make sure all checks' versions are exposed. See [#1945][5].
* [Fixed] Fix error in case of empty stat info. See [#1944][6].
* [Fixed] Add data files to the wheel package. See [#1727][7].

## 1.3.0 / 2018-06-04

* [Added] Add optional 'active' tag to metrics. See [#1478][8].
* [Changed] Upgrade requests dependency to 2.18.4. See [#1264][9].

## 1.2.1 / 2018-02-13

* [DOC] Adding configuration for log collection in `conf.yaml`

## 1.2.0 / 2018-02-13

* [FEATURE] allows the use of custom HTTP headers when requesting stats. See [#1019][10]

## 1.1.0 / 2018-01-10

* [FEATURE] Enable tagging metrics based on a user-submitted named regex. See [#462][11]

## 1.0.2 / 2017-05-11

* [BUGFIX] Sanitize bogus evil CSV with with linebreak in field. See [#379][12]

## 1.0.1 / 2017-04-24

* [BUGFIX] handle comma in fields. See [#281][13]

## 1.0.0 / 2017-03-22

* [FEATURE] adds haproxy integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2849
[2]: https://github.com/DataDog/integrations-core/pull/2731
[3]: https://github.com/DataDog/integrations-core/pull/2727
[4]: https://github.com/DataDog/integrations-core/pull/2465
[5]: https://github.com/DataDog/integrations-core/pull/1945
[6]: https://github.com/DataDog/integrations-core/pull/1944
[7]: https://github.com/DataDog/integrations-core/pull/1727
[8]: https://github.com/DataDog/integrations-core/pull/1478
[9]: https://github.com/DataDog/integrations-core/pull/1264
[10]: https://github.com/DataDog/integrations-core/pull/1019
[11]: https://github.com/DataDog/integrations-core/issues/462
[12]: https://github.com/DataDog/integrations-core/issues/379
[13]: https://github.com/DataDog/integrations-core/issues/281
