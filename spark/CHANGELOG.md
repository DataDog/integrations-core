# CHANGELOG - spark

## 1.19.1 / 2021-01-25

* [Fixed] Update check signature. See [#8259](https://github.com/DataDog/integrations-core/pull/8259).

## 1.19.0 / 2020-12-29

* [Added] Add metrics for structured streams. See [#8078](https://github.com/DataDog/integrations-core/pull/8078).

## 1.18.0 / 2020-11-23 / Agent 7.25.0

* [Added] Add more granular executor metrics. See [#8028](https://github.com/DataDog/integrations-core/pull/8028).

## 1.17.0 / 2020-11-06 / Agent 7.24.0

* [Added] Update HTTP config docs to describe dcos_auth token reader. See [#7953](https://github.com/DataDog/integrations-core/pull/7953).

## 1.16.0 / 2020-10-31

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.15.0 / 2020-09-03 / Agent 7.23.0

* [Added] Add Stage and Job ID tags. See [#7459](https://github.com/DataDog/integrations-core/pull/7459).
* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.14.0 / 2020-08-10 / Agent 7.22.0

* [Added] Add documentation for spark logs. See [#7109](https://github.com/DataDog/integrations-core/pull/7109).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.13.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Add config specs. See [#6921](https://github.com/DataDog/integrations-core/pull/6921).

## 1.12.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.11.4 / 2020-02-22 / Agent 7.18.0

* [Fixed] Update documentation in example config. See [#5508](https://github.com/DataDog/integrations-core/pull/5508).

## 1.11.3 / 2020-01-30

* [Fixed] Handle warning message from proxy. See [#5525](https://github.com/DataDog/integrations-core/pull/5525).

## 1.11.2 / 2020-01-29

* [Fixed] Prevent crash when a single app fails. See [#5552](https://github.com/DataDog/integrations-core/pull/5552).

## 1.11.1 / 2020-01-15 / Agent 7.17.0

* [Fixed] Make sure version collection fails gracefully. See [#5465](https://github.com/DataDog/integrations-core/pull/5465).

## 1.11.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Collect version metadata. See [#5032](https://github.com/DataDog/integrations-core/pull/5032).

## 1.10.1 / 2019-12-06 / Agent 7.16.0

* [Fixed] Remove reference to Kubernetes in the service check message for `spark_driver_mode`. See [#5159](https://github.com/DataDog/integrations-core/pull/5159).

## 1.10.0 / 2019-12-02

* [Added] Add Spark driver support. See [#4631](https://github.com/DataDog/integrations-core/pull/4631). Thanks [mrmuggymuggy](https://github.com/mrmuggymuggy).

## 1.9.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.8.1 / 2019-07-18 / Agent 6.13.0

* [Fixed] Remove unused configs and code for spark check. See [#4133](https://github.com/DataDog/integrations-core/pull/4133).

## 1.8.0 / 2019-07-09

* [Added] Use the new RequestsWrapper for connecting to services. See [#4058](https://github.com/DataDog/integrations-core/pull/4058).

## 1.7.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3566](https://github.com/DataDog/integrations-core/pull/3566).

## 1.6.0 / 2019-01-08 / Agent 6.10.0

* [Added] Allow disabling of streaming metrics. See [#2889][1].
* [Added] Support Kerberos auth. See [#2825][2].

## 1.5.0 / 2018-12-20 / Agent 6.9.0

* [Added] Add streaming statistics metrics to the spark integration. See [#2437][3].

## 1.4.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][4].

## 1.4.0 / 2018-06-07

* [Added] Add support for HTTP authentication. See [#1680][5].

## 1.3.0 / 2018-05-11

* [FEATURE] adds custom tag support to service check.

## 1.2.0 / 2018-02-13

* [IMPROVEMENT] Add configuration options `ssl_verify`, `ssl_cert` and `ssl_key` to allow SSL configuration. See [#1064][6].

## 1.1.0 / [2018-01-10]

* [IMPROVEMENT] Filter Spark frameworks by port. See [#459][7].  (Thanks [@johnjeffers][8])

## 1.0.1 / 2017-07-18

* [BUGFIX] Build proxy-compatible URL . See [#437][9]

## 1.0.0 / 2017-03-22

* [FEATURE] adds spark integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2889
[2]: https://github.com/DataDog/integrations-core/pull/2825
[3]: https://github.com/DataDog/integrations-core/pull/2437
[4]: https://github.com/DataDog/integrations-core/pull/1727
[5]: https://github.com/DataDog/integrations-core/pull/1680
[6]: https://github.com/DataDog/integrations-core/pull/1064
[7]: https://github.com/DataDog/integrations-core/pull/459
[8]: https://github.com/johnjeffers
[9]: https://github.com/DataDog/integrations-core/issues/437
