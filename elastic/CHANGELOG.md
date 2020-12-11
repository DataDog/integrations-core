# CHANGELOG - elastic

## 1.22.0 / 2020-12-11

* [Added] Submit jvm.gc.collectors metrics as rate. See [#7924](https://github.com/DataDog/integrations-core/pull/7924).
* [Fixed] Update check signature. See [#8114](https://github.com/DataDog/integrations-core/pull/8114).

## 1.21.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.20.1 / 2020-09-28

* [Fixed] Extra debug for missing metrics. See [#7673](https://github.com/DataDog/integrations-core/pull/7673).

## 1.20.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.19.0 / 2020-08-10 / Agent 7.22.0

* [Added] Include Node system stats. See [#6590](https://github.com/DataDog/integrations-core/pull/6590).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.18.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Add config specs. See [#6773](https://github.com/DataDog/integrations-core/pull/6773).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.17.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.16.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.16.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Add OOTB support for AWS Signature Version 4 Signing. See [#5289](https://github.com/DataDog/integrations-core/pull/5289).

## 1.15.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.14.0 / 2019-10-11 / Agent 6.15.0

* [Added] Submit version metadata. See [#4724](https://github.com/DataDog/integrations-core/pull/4724).
* [Added] Add external refresh metrics. See [#4554](https://github.com/DataDog/integrations-core/pull/4554). Thanks [clandry94](https://github.com/clandry94).
* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.13.2 / 2019-08-30 / Agent 6.14.0

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 1.13.1 / 2019-07-18 / Agent 6.13.0

* [Fixed] Add missing HTTP options to example config. See [#4129](https://github.com/DataDog/integrations-core/pull/4129).

## 1.13.0 / 2019-07-13

* [Added] Use the new RequestsWrapper for connecting to services. See [#4100](https://github.com/DataDog/integrations-core/pull/4100).

## 1.12.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3504](https://github.com/DataDog/integrations-core/pull/3504).

## 1.11.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support unicode for Python 3 bindings. See [#2869](https://github.com/DataDog/integrations-core/pull/2869).

## 1.10.0 / 2019-01-04 / Agent 6.9.0

* [Added] Add completed metric for all ES thread pools. See [#2803][1].
* [Added] Capture metrics for ES scroll requests . See [#2687][2].

## 1.9.1 / 2018-11-30 / Agent 6.8.0

* [Fixed] Add elasticsearch-oss as an auto_conf.yaml Elasticsearch identifier. See [#2644][3]. Thanks [jcassee][4].

## 1.9.0 / 2018-10-23

* [Added] Add option to prevent duplicate hostnames. See [#2453][5].
* [Added] Support Python 3. See [#2417][6].
* [Fixed] Move metrics definition and logic into its own module. See [#2381][7].

## 1.8.0 / 2018-10-12 / Agent 6.6.0

* [Fixed] Move config parser to its own module. See [#2370][8].
* [Added] Added delayed_unassigned_shards metric. See [#2361][9].
* [Added] Added inflight_requests metrics (version 5.4 and later).. See [#2360][10].

## 1.7.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add thread write queue to fix Elasticsearch 6.3.x compatibility. See [#1943][11].
* [Fixed] Add data files to the wheel package. See [#1727][12].

## 1.7.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][13].
* [Fixed] [FIXED] Ensure base url path isn't removed when admin_forwarder is used. See [#1202][14].

## 1.6.0 / 2018-05-11

* [FEATURE] Hardcode the 9200 port in the Autodiscovery template. See [#1444][15].
* [FEATURE] adds `index_stats` to collect index level metrics. See [#1312][16].

## 1.5.0 / 2018-02-13

* [IMPROVEMENT] Adds `admin_forwarder` option to keep URL intact when using forwarder. See [#1050][17].
* [BUG] Fixes bug that causes poor failovers when authentication fails. See [#1026][18].
* [IMPROVEMENT] Adds `cluster_name` tag to the `elasticsearch.cluster_health` service check. See [#1038][19].

## 1.4.0 / 2018-01-10

* [BUG] Fix missing fs metrics for elastic >= 5. See [#997][20].

## 1.3.0 / 2018-01-10

* [FEATURE] adds `pshard_graceful_timeout` that will skip pshard_stats if TO. See [#463][21]
* [IMPROVEMENT] get rid of pretty json. See [#893][22].

## 1.2.0 / 2017-11-21

* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860][23]

## 1.1.0 / 2017-11-21

* [BUG] Fixes bug for retreiving indices count. See [#806][24]
* [FEATURE] Added more JVM metrics. See [#695][25]
* [FEATURE] Add metric on the average time spent by tasks in the pending queue. See [#820][26]

## 1.0.1 / 2017-08-28

* [FEATURE] Add metric for index count. See [#617][27]

## 1.0.0 / 2017-03-22

* [FEATURE] adds elastic integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2803
[2]: https://github.com/DataDog/integrations-core/pull/2687
[3]: https://github.com/DataDog/integrations-core/pull/2644
[4]: https://github.com/jcassee
[5]: https://github.com/DataDog/integrations-core/pull/2453
[6]: https://github.com/DataDog/integrations-core/pull/2417
[7]: https://github.com/DataDog/integrations-core/pull/2381
[8]: https://github.com/DataDog/integrations-core/pull/2370
[9]: https://github.com/DataDog/integrations-core/pull/2361
[10]: https://github.com/DataDog/integrations-core/pull/2360
[11]: https://github.com/DataDog/integrations-core/pull/1943
[12]: https://github.com/DataDog/integrations-core/pull/1727
[13]: https://github.com/DataDog/integrations-core/pull/1664
[14]: https://github.com/DataDog/integrations-core/pull/1202
[15]: https://github.com/DataDog/integrations-core/issues/1444
[16]: https://github.com/DataDog/integrations-core/issues/1312
[17]: https://github.com/DataDog/integrations-core/issues/1050
[18]: https://github.com/DataDog/integrations-core/issues/1026
[19]: https://github.com/DataDog/integrations-core/pull/1038
[20]: https://github.com/DataDog/integrations-core/pull/997
[21]: https://github.com/DataDog/integrations-core/issues/463
[22]: https://github.com/DataDog/integrations-core/issues/893
[23]: https://github.com/DataDog/integrations-core/issues/860
[24]: https://github.com/DataDog/integrations-core/issues/806
[25]: https://github.com/DataDog/integrations-core/issues/695
[26]: https://github.com/DataDog/integrations-core/issues/820
[27]: https://github.com/DataDog/integrations-core/issues/617
