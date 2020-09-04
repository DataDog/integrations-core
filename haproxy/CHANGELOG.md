# CHANGELOG - haproxy

## 2.10.1 / 2020-08-10

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 2.10.0 / 2020-06-29

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix version parsing with haproxy enterprise version. See [#6774](https://github.com/DataDog/integrations-core/pull/6774).

## 2.9.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.8.1 / 2020-05-05

* [Fixed] Handle empty response from show table. See [#6579](https://github.com/DataDog/integrations-core/pull/6579).

## 2.8.0 / 2020-04-04

* [Added] Gather stick-table metrics. See [#6158](https://github.com/DataDog/integrations-core/pull/6158).
* [Fixed] Revert `to_native_string` to `to_string` for integrations. See [#6238](https://github.com/DataDog/integrations-core/pull/6238).

## 2.7.2 / 2020-03-24

* [Fixed] Fix event submission on Python 3. See [#6138](https://github.com/DataDog/integrations-core/pull/6138).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Rename `to_string()` utility to `to_native_string()`. See [#5996](https://github.com/DataDog/integrations-core/pull/5996).

## 2.7.1 / 2020-02-25

* [Fixed] Document disable_legacy_service_tag and bump checks_base requirement. See [#5835](https://github.com/DataDog/integrations-core/pull/5835).

## 2.7.0 / 2020-02-22

* [Added] Add an option to skip reporting during restarts. See [#5571](https://github.com/DataDog/integrations-core/pull/5571). Thanks [dd-adn](https://github.com/dd-adn).
* [Deprecated] Deprecate `service` tag. See [#5550](https://github.com/DataDog/integrations-core/pull/5550).

## 2.6.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.5.1 / 2019-12-13

* [Fixed] Handle failure on version endpoint. See [#5208](https://github.com/DataDog/integrations-core/pull/5208).

## 2.5.0 / 2019-12-02

* [Added] Submit version metadata. See [#4851](https://github.com/DataDog/integrations-core/pull/4851).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 2.4.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 2.3.0 / 2019-08-24

* [Added] Add requests wrapper to haproxy. See [#4219](https://github.com/DataDog/integrations-core/pull/4219).

## 2.2.0 / 2019-06-01

* [Added] Add `requests.tot_rate`, `connections.rate`, `connections.tot_rate`, and `requests.intercepted`. See [#3797](https://github.com/DataDog/integrations-core/pull/3797).
* [Added] `collect_aggregates_only` now collects all values when set to `false`. See [#3797](https://github.com/DataDog/integrations-core/pull/3797).

## 2.1.0 / 2019-05-14

* [Added] Adhere to code style. See [#3513](https://github.com/DataDog/integrations-core/pull/3513).

## 2.0.0 / 2019-02-18

* [Changed] Only send 'haproxy.backend_hosts' metrics for backend. See [#3073](https://github.com/DataDog/integrations-core/pull/3073).
* [Changed] Put service check behind a flag, false by default. See [#3083](https://github.com/DataDog/integrations-core/pull/3083).
* [Added] Support unicode for Python 3 bindings. See [#2869](https://github.com/DataDog/integrations-core/pull/2869).

## 1.4.0 / 2019-01-04

* [Added] Support Python 3. See [#2849][1].
* [Added] tcp scheme support for stats socket. See [#2731][2].
* [Added] Add server_address tag when available. See [#2727][3].

## 1.3.2 / 2018-11-30

* [Fixed] Use raw string literals when \ is present. See [#2465][4].

## 1.3.1 / 2018-09-04

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
[10]:
[11]: https://github.com/DataDog/integrations-core/issues/462
[12]: https://github.com/DataDog/integrations-core/issues/379
[13]: https://github.com/DataDog/integrations-core/issues/281
