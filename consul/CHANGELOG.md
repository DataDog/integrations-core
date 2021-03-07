# CHANGELOG - consul

## 1.18.0 / 2021-03-07

* [Added] Adding services_exclude config option. See [#8377](https://github.com/DataDog/integrations-core/pull/8377).
* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.17.1 / 2020-12-11 / Agent 7.25.0

* [Fixed] Add consul 1.9.0 metrics. See [#8095](https://github.com/DataDog/integrations-core/pull/8095).

## 1.17.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Fixed] Add missing default HTTP headers: Accept, Accept-Encoding. See [#7725](https://github.com/DataDog/integrations-core/pull/7725).

## 1.16.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Support prometheus endpoint. See [#7098](https://github.com/DataDog/integrations-core/pull/7098).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).
* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 1.15.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.15.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.14.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add config spec. See [#6317](https://github.com/DataDog/integrations-core/pull/6317).

## 1.13.0 / 2020-04-04 / Agent 7.19.0

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Added] Add new metric to count services. See [#5992](https://github.com/DataDog/integrations-core/pull/5992).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.12.2 / 2020-02-25 / Agent 7.18.0

* [Fixed] Change new added tag. See [#5856](https://github.com/DataDog/integrations-core/pull/5856).

## 1.12.1 / 2020-02-25

* [Fixed] Bump minimun agent version. See [#5834](https://github.com/DataDog/integrations-core/pull/5834).

## 1.12.0 / 2020-02-22

* [Added] Create `consul_service` tag. See [#5519](https://github.com/DataDog/integrations-core/pull/5519). Thanks [nicbono](https://github.com/nicbono).
* [Deprecated] Deprecate `service` tag. See [#5540](https://github.com/DataDog/integrations-core/pull/5540).

## 1.11.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add version metadata. See [#4944](https://github.com/DataDog/integrations-core/pull/4944).
* [Added] Standardize logging format. See [#4903](https://github.com/DataDog/integrations-core/pull/4903).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.10.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.9.1 / 2019-08-30 / Agent 6.14.0

* [Fixed] Fix RequestsWrapper options. See [#4476](https://github.com/DataDog/integrations-core/pull/4476).

## 1.9.0 / 2019-08-24

* [Added] Add support for proxy options. See [#3363](https://github.com/DataDog/integrations-core/pull/3363).
* [Fixed] Fix Consul event timestamp. See [#4173](https://github.com/DataDog/integrations-core/pull/4173).

## 1.8.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3491](https://github.com/DataDog/integrations-core/pull/3491).

## 1.7.0 / 2019-02-18 / Agent 6.10.0

* [Added] Add `consul.can_connect` service check for every HTTP request to consul. See [#3003](https://github.com/DataDog/integrations-core/pull/3003).
* [Added] Finish supporting Py3. See [#2906](https://github.com/DataDog/integrations-core/pull/2906).

## 1.6.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add option to run the full check on any node. See [#2461][1].
* [Added] Support Python 3. See [#2446][2].

## 1.5.2 / 2018-10-12 / Agent 6.6.0

* [Fixed] Update consul timestamp to use supported python functions. See [#2199][3]. Thanks [hhansell][4].

## 1.5.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Accept more standard boolean values for instance config options. See [#1954][5].
* [Fixed] Add data files to the wheel package. See [#1727][6].

## 1.5.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][7].
* [Added] Include consul_datacenter tag in service checks. See [#1526][8]. Thanks [TylerLubeck][9].
* [Added] Add a check to count all nodes in a consul cluster. See [#1479][10]. Thanks [TylerLubeck][9].

## 1.4.0 / 2018-05-11

* [FEATURE] Hardcode the 8500 port in the Autodiscovery template. See [#1444][11] for more information.
* [FEATURE] Include consul_datacenter tag in service checks

## 1.3.0 / 2018-01-10

* [IMPROVEMENT] Add support for Consul 1.0. See [#876][12], thanks [@byronwolfman][13]
* [BUG FIX] Fixes TypeError if/when services are culled. See [#968][14]

## 1.2.0 2017-11-21

* [FEATURE] Add service tags to metrics
* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860][15]

## 1.1.0 / 2017-07-18

* [Fix] Fix duplicate service check with same tags but different status being sent (one per Node). See [#460][16]
* [FEATURE] Support ACL token for authentication. See [#521][17]

## 1.0.0 / 2017-03-22

* [FEATURE] adds consul integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2461
[2]: https://github.com/DataDog/integrations-core/pull/2446
[3]: https://github.com/DataDog/integrations-core/pull/2199
[4]: https://github.com/hhansell
[5]: https://github.com/DataDog/integrations-core/pull/1954
[6]: https://github.com/DataDog/integrations-core/pull/1727
[7]: https://github.com/DataDog/integrations-core/pull/1664
[8]: https://github.com/DataDog/integrations-core/pull/1526
[9]: https://github.com/TylerLubeck
[10]: https://github.com/DataDog/integrations-core/pull/1479
[11]: https://github.com/DataDog/integrations-core/pull/1444
[12]: https://github.com/DataDog/integrations-core/pull/876
[13]: https://github.com/byronwolfman
[14]: https://github.com/DataDog/integrations-core/pull/968
[15]: https://github.com/DataDog/integrations-core/issues/860
[16]: https://github.com/DataDog/integrations-core/issues/460
[17]: https://github.com/DataDog/integrations-core/issues/521
