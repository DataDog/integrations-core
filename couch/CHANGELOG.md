# CHANGELOG - couch

## 4.1.0 / 2021-10-04 / Agent 7.32.0

* [Added] Add HTTP option to control the size of streaming responses. See [#10183](https://github.com/DataDog/integrations-core/pull/10183).
* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Fixed] Bump base package dependency. See [#10218](https://github.com/DataDog/integrations-core/pull/10218).
* [Fixed] Fix the description of the `allow_redirects` HTTP option. See [#10195](https://github.com/DataDog/integrations-core/pull/10195).

## 4.0.0 / 2021-08-22 / Agent 7.31.0

* [Changed] Remove messages for integrations for OK service checks. See [#9888](https://github.com/DataDog/integrations-core/pull/9888).

## 3.13.3 / 2021-07-12 / Agent 7.30.0

* [Fixed] Use Agent 8 signature. See [#9522](https://github.com/DataDog/integrations-core/pull/9522).

## 3.13.2 / 2021-03-07 / Agent 7.27.0

* [Fixed] Rename config spec example consumer option `default` to `display_default`. See [#8593](https://github.com/DataDog/integrations-core/pull/8593).
* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 3.13.1 / 2020-11-13 / Agent 7.24.0

* [Fixed] Fix exception message. See [#7912](https://github.com/DataDog/integrations-core/pull/7912).

## 3.13.0 / 2020-10-31

* [Added] Support couch v3. See [#7570](https://github.com/DataDog/integrations-core/pull/7570).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 3.12.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Do not render null defaults for config spec example consumer. See [#7503](https://github.com/DataDog/integrations-core/pull/7503).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 3.11.0 / 2020-08-10 / Agent 7.22.0

* [Added] couch config specs. See [#7160](https://github.com/DataDog/integrations-core/pull/7160).
* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Use inclusive wording. See [#7159](https://github.com/DataDog/integrations-core/pull/7159).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 3.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 3.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 3.8.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 3.8.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add version metadata. See [#5615](https://github.com/DataDog/integrations-core/pull/5615).

## 3.7.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 3.6.0 / 2019-12-02 / Agent 7.16.0

* [Added] Standardize logging format. See [#4904](https://github.com/DataDog/integrations-core/pull/4904).

## 3.5.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 3.4.1 / 2019-08-30 / Agent 6.14.0

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 3.4.0 / 2019-08-24

* [Added] Add RequestsWrapper to couch. See [#4118](https://github.com/DataDog/integrations-core/pull/4118).

## 3.3.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3493](https://github.com/DataDog/integrations-core/pull/3493).

## 3.2.1 / 2019-03-29 / Agent 6.11.0

* [Fixed] Include exception in connection error messages. See [#3262](https://github.com/DataDog/integrations-core/pull/3262).

## 3.2.0 / 2019-02-18 / Agent 6.10.0

* [Added] Finish Python 3 Support. See [#2911](https://github.com/DataDog/integrations-core/pull/2911).

## 3.1.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2721][1].

## 3.0.0 / 2018-11-30 / Agent 6.8.0

* [Removed] Add CouchDB 2.2.0 compatibility by dropping the `purge_seq` metric. See [#2287][2]. Thanks [janl][3].

## 2.6.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Make sure all checks' versions are exposed. See [#1945][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 2.6.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][6].
* [Added] Raise custom exceptions for specific errors instead of a generic `Exception`.

## 2.5.0 / 2018-05-11

* [FEATURE] Hardcode the 5984 port in the Autodiscovery template. See [#1444][7] for more information.

## 2.4.0 / 2018-02-13

* [FEATURE] reduces by db and by dd amplification by distributing the dbs to report on the running agents

## 2.3.0 / 2018-02-13

* [BUGFIX] Handle the case where there is no database. See [#1029][8]
* [IMPROVEMENT] Add custom tags to metrics and service checks. See [#1034][9]

## 2.2.0 / 2018-01-10

* [FEATURE] collects and submits CouchDB design docs metrics. See [#813][10] (Thanks [@calonso][11])
* [FEATURE] collects CouchDB active tasks stats. See [#812][12] (Thanks [@calonso][11])

## 2.1.0 / 2017-11-21

* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860][13]
* [FEATURE] collects Erlang VM stats from the `_system` endpoint. See [#793][14] (Thanks [@calonso][11])

## 2.0.0 / 2017-09-01

* [FEATURE] adds CouchDB 2.x integration.

## 1.0.1 / 2017-04-24

* [BUGFIX] Escape database names. See [#268][15] (Thanks [@bernharduw][16])

## 1.0.0 / 2017-03-22

* [FEATURE] adds couch integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2721
[2]: https://github.com/DataDog/integrations-core/pull/2287
[3]: https://github.com/janl
[4]: https://github.com/DataDog/integrations-core/pull/1945
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1664
[7]: https://github.com/DataDog/integrations-core/pull/1444
[8]: https://github.com/DataDog/integrations-core/pull/1029
[9]: https://github.com/DataDog/integrations-core/pull/1034
[10]: https://github.com/DataDog/integrations-core/pull/813
[11]: https://github.com/calonso
[12]: https://github.com/DataDog/integrations-core/pull/812
[13]: https://github.com/DataDog/integrations-core/issues/860
[14]: https://github.com/DataDog/integrations-core/issues/793
[15]: https://github.com/DataDog/integrations-core/issues/268
[16]: https://github.com/bernharduw
