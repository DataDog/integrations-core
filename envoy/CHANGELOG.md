# CHANGELOG - Envoy

## 1.20.1 / 2021-01-25

* [Fixed] Update check signature. See [#8258](https://github.com/DataDog/integrations-core/pull/8258).

## 1.20.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add newly documented metrics. See [#7765](https://github.com/DataDog/integrations-core/pull/7765).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.19.0 / 2020-10-07

* [Added] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Fixed] Update Watchdog metrics. See [#7740](https://github.com/DataDog/integrations-core/pull/7740).
* [Fixed] Properly handle a parsing edge case. See [#7717](https://github.com/DataDog/integrations-core/pull/7717).

## 1.18.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Do not render null defaults for config spec example consumer. See [#7503](https://github.com/DataDog/integrations-core/pull/7503).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.17.0 / 2020-08-10 / Agent 7.22.0

* [Added] envoy config specs. See [#7157](https://github.com/DataDog/integrations-core/pull/7157).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Use inclusive naming. See [#7156](https://github.com/DataDog/integrations-core/pull/7156).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.16.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 1.15.2 / 2020-05-26 / Agent 7.20.0

* [Fixed] Handle server info for envoy <= 1.8. See [#6740](https://github.com/DataDog/integrations-core/pull/6740).

## 1.15.1 / 2020-05-19

* [Fixed] Safer metadata error handling. See [#6685](https://github.com/DataDog/integrations-core/pull/6685).

## 1.15.0 / 2020-05-17

* [Added] Collect version metadata. See [#6595](https://github.com/DataDog/integrations-core/pull/6595).
* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Fixed] Fix style to account for new flake8 rules. See [#6620](https://github.com/DataDog/integrations-core/pull/6620).

## 1.14.0 / 2020-04-04 / Agent 7.19.0

* [Added] Update doc about whitelist and blacklist. See [#5875](https://github.com/DataDog/integrations-core/pull/5875).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.13.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add support for more metrics in Envoy integration. See [#5537](https://github.com/DataDog/integrations-core/pull/5537). Thanks [csssuf](https://github.com/csssuf).

## 1.12.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.11.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add new metrics for Redis. See [#4946](https://github.com/DataDog/integrations-core/pull/4946). Thanks [tony612](https://github.com/tony612).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.10.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add xDS-related metrics. See [#4634](https://github.com/DataDog/integrations-core/pull/4634). Thanks [csssuf](https://github.com/csssuf).
* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.9.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add RequestsWrapper to envoy. See [#4120](https://github.com/DataDog/integrations-core/pull/4120).

## 1.8.0 / 2019-07-04 / Agent 6.13.0

* [Added] Add cluster.ssl metrics to Envoy integration. See [#3976](https://github.com/DataDog/integrations-core/pull/3976). Thanks [csssuf](https://github.com/csssuf).
* [Added] Add Envoy upstream_rq_completed cluster metrics. See [#3955](https://github.com/DataDog/integrations-core/pull/3955). Thanks [csssuf](https://github.com/csssuf).

## 1.7.0 / 2019-06-19

* [Added] Add more listener metrics. See [#3922](https://github.com/DataDog/integrations-core/pull/3922).

## 1.6.0 / 2019-06-18

* [Added] Add logs config to envoy. See [#3918](https://github.com/DataDog/integrations-core/pull/3918).

## 1.5.0 / 2019-03-29 / Agent 6.11.0

* [Added] Adhere to style. See [#3366](https://github.com/DataDog/integrations-core/pull/3366).

## 1.4.0 / 2018-09-05 / Agent 6.5.0

* [Changed] Change order of precedence of whitelist and blacklist for pattern filtering. See [#2174][1].

## 1.3.0 / 2018-08-06

* [Added] Add ability to whitelist/blacklist metrics. See [#1975][2].
* [Changed] Add data files to the wheel package. See [#1727][3].

## 1.2.1 / 2018-06-14 / Agent 6.4.0

* [Fixed] properly send tags for histograms. See [#1741][4].

## 1.2.0 / 2018-06-07

* [Added] support histograms, fix count submission. See [#1616][5].

## 1.1.0 / 2018-05-11

* [FEATURE] add newly-documented metrics. See #1326
* [IMPROVEMENT] tags can now contain the dot metric delimiter itself. See #1404

## 1.0.0 / 2018-03-23

* [FEATURE] add Envoy integration. See #1156

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2174
[2]: https://github.com/DataDog/integrations-core/pull/1975
[3]: https://github.com/DataDog/integrations-core/pull/1727
[4]: https://github.com/DataDog/integrations-core/pull/1741
[5]: https://github.com/DataDog/integrations-core/pull/1616
