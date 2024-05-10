# CHANGELOG - elastic

<!-- towncrier release notes start -->

## 6.3.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 6.2.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 6.1.0 / 2023-08-18 / Agent 7.48.0

***Added***:

* Support inflight_requests stats since v8 ([#15259](https://github.com/DataDog/integrations-core/pull/15259))

***Fixed***:

* Correct checking instance type of get data response ([#15554](https://github.com/DataDog/integrations-core/pull/15554))
* Avoid collecting template metrics on unsupported ES versions. ([#15550](https://github.com/DataDog/integrations-core/pull/15550))

## 6.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Lower logging level if there's an error scraping the template endpoint to DEBUG ([#15381](https://github.com/DataDog/integrations-core/pull/15381))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 5.5.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Add support for list value paths in Elastic custom metrics ([#14718](https://github.com/DataDog/integrations-core/pull/14718)) Thanks [CayvonH](https://github.com/CayvonH).

***Fixed***:

* Catch only requests-related exceptions ([#15089](https://github.com/DataDog/integrations-core/pull/15089))
* Do not stop collecting metrics if the templates endpoint is not reachable ([#15050](https://github.com/DataDog/integrations-core/pull/15050))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Correctly compute the `templates.count` metric ([#14636](https://github.com/DataDog/integrations-core/pull/14636))

## 5.4.2 / 2023-06-27 / Agent 7.46.0

* [Fixed] Do not stop collecting metrics if the templates endpoint is not reachable ([#15054](https://github.com/DataDog/integrations-core/pull/15054))

## 5.4.1 / 2023-05-31

***Fixed***:

* Correctly compute the `templates.count` metric ([#14636](https://github.com/DataDog/integrations-core/pull/14636))

## 5.4.0 / 2023-05-26

***Added***:

* Add new ES metric for templates count ([#14569](https://github.com/DataDog/integrations-core/pull/14569))
* Allow disabling event submission ([#14511](https://github.com/DataDog/integrations-core/pull/14511))
* Add 2 index search stats metrics ([#14507](https://github.com/DataDog/integrations-core/pull/14507))
* Add indexing pressure metrics ([#14466](https://github.com/DataDog/integrations-core/pull/14466))

***Fixed***:

* Document that data_path in custom queries cannot contain wildcards ([#14551](https://github.com/DataDog/integrations-core/pull/14551))
* Improve description of config field ([#14524](https://github.com/DataDog/integrations-core/pull/14524))
* More metrics match metadata ([#14506](https://github.com/DataDog/integrations-core/pull/14506))

## 5.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 5.2.0 / 2022-06-27 / Agent 7.38.0

***Added***:

* Collect the count version of certain rate metrics ([#12352](https://github.com/DataDog/integrations-core/pull/12352))

## 5.1.1 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Update metrics ([#11783](https://github.com/DataDog/integrations-core/pull/11783))

## 5.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))
* Add new Elastic metric indexing-pressure ([#10758](https://github.com/DataDog/integrations-core/pull/10758))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 5.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11344](https://github.com/DataDog/integrations-core/pull/11344))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 4.0.1 / 2022-01-13 / Agent 7.34.0

***Fixed***:

* Validate custom query column type ([#11106](https://github.com/DataDog/integrations-core/pull/11106))
* Continue other custom queries when one fails ([#11105](https://github.com/DataDog/integrations-core/pull/11105))

## 4.0.0 / 2022-01-08

***Changed***:

* Add `server` default group for all monitor special cases ([#10976](https://github.com/DataDog/integrations-core/pull/10976))

***Added***:

* Bump base dependency ([#11064](https://github.com/DataDog/integrations-core/pull/11064))
* Add support for custom queries ([#10894](https://github.com/DataDog/integrations-core/pull/10894))
* Add detailed_index_stats parameter to pull index-level metrics ([#10766](https://github.com/DataDog/integrations-core/pull/10766))

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Bump base package dependency ([#10930](https://github.com/DataDog/integrations-core/pull/10930))
* Lower log level for expected condition ([#10825](https://github.com/DataDog/integrations-core/pull/10825))

## 3.3.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 3.2.0 / 2021-09-10

***Added***:

* Support opensearch ([#10093](https://github.com/DataDog/integrations-core/pull/10093))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

## 3.1.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

## 3.0.1 / 2021-07-20

***Fixed***:

* Fix log line  ([#9621](https://github.com/DataDog/integrations-core/pull/9621))

## 3.0.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add .count monotonic_count metrics ([#9354](https://github.com/DataDog/integrations-core/pull/9354))

## 2.2.0 / 2021-05-17

***Added***:

* Update version supported for Cat Allocation metrics ([#9339](https://github.com/DataDog/integrations-core/pull/9339))

## 2.1.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Add runtime configuration validation ([#8911](https://github.com/DataDog/integrations-core/pull/8911))

***Fixed***:

* Sync config models ([#9168](https://github.com/DataDog/integrations-core/pull/9168))

## 2.0.0 / 2021-04-09

***Changed***:

* Normalize memory stats to mebibytes ([#9128](https://github.com/DataDog/integrations-core/pull/9128))

***Added***:

* Support Cat allocation metrics ([#8861](https://github.com/DataDog/integrations-core/pull/8861))

## 1.24.0 / 2021-02-10 / Agent 7.27.0

***Added***:

* Rename cluster_name tag to elastic_cluster ([#8526](https://github.com/DataDog/integrations-core/pull/8526))

***Fixed***:

* Disable SLM metrics by default ([#8511](https://github.com/DataDog/integrations-core/pull/8511))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.23.0 / 2021-01-15

***Added***:

* Add SLM metrics ([#8335](https://github.com/DataDog/integrations-core/pull/8335))
* Add index.health.reverse metric ([#8362](https://github.com/DataDog/integrations-core/pull/8362))
* Add additional node metrics to monitor cpu throttling ([#8290](https://github.com/DataDog/integrations-core/pull/8290)) Thanks [onurdialpad](https://github.com/onurdialpad).

## 1.22.1 / 2020-12-17 / Agent 7.25.0

***Fixed***:

* Fix tags memory leak ([#8213](https://github.com/DataDog/integrations-core/pull/8213))

## 1.22.0 / 2020-12-11

***Added***:

* Submit jvm.gc.collectors metrics as rate ([#7924](https://github.com/DataDog/integrations-core/pull/7924))

***Fixed***:

* Update check signature ([#8114](https://github.com/DataDog/integrations-core/pull/8114))

## 1.21.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

## 1.20.1 / 2020-09-28

***Fixed***:

* Extra debug for missing metrics ([#7673](https://github.com/DataDog/integrations-core/pull/7673))

## 1.20.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 1.19.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* Include Node system stats ([#6590](https://github.com/DataDog/integrations-core/pull/6590))

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))
* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 1.18.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))
* Add config specs ([#6773](https://github.com/DataDog/integrations-core/pull/6773))

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 1.17.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.16.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))

## 1.16.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))
* Add OOTB support for AWS Signature Version 4 Signing ([#5289](https://github.com/DataDog/integrations-core/pull/5289))

## 1.15.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Add auth type to RequestsWrapper ([#4708](https://github.com/DataDog/integrations-core/pull/4708))

## 1.14.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Submit version metadata ([#4724](https://github.com/DataDog/integrations-core/pull/4724))
* Add external refresh metrics ([#4554](https://github.com/DataDog/integrations-core/pull/4554)) Thanks [clandry94](https://github.com/clandry94).
* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

## 1.13.2 / 2019-08-30 / Agent 6.14.0

***Fixed***:

* Update class signature to support the RequestsWrapper ([#4469](https://github.com/DataDog/integrations-core/pull/4469))

## 1.13.1 / 2019-07-18 / Agent 6.13.0

***Fixed***:

* Add missing HTTP options to example config ([#4129](https://github.com/DataDog/integrations-core/pull/4129))

## 1.13.0 / 2019-07-13

***Added***:

* Use the new RequestsWrapper for connecting to services ([#4100](https://github.com/DataDog/integrations-core/pull/4100))

## 1.12.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3504](https://github.com/DataDog/integrations-core/pull/3504))

## 1.11.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support unicode for Python 3 bindings ([#2869](https://github.com/DataDog/integrations-core/pull/2869))

## 1.10.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* Add completed metric for all ES thread pools ([#2803](https://github.com/DataDog/integrations-core/pull/2803))
* Capture metrics for ES scroll requests  ([#2687](https://github.com/DataDog/integrations-core/pull/2687))

## 1.9.1 / 2018-11-30 / Agent 6.8.0

***Fixed***:

* Add elasticsearch-oss as an auto_conf.yaml Elasticsearch identifier ([#2644](https://github.com/DataDog/integrations-core/pull/2644)) Thanks [jcassee](https://github.com/jcassee).

## 1.9.0 / 2018-10-23

***Added***:

* Add option to prevent duplicate hostnames ([#2453](https://github.com/DataDog/integrations-core/pull/2453))
* Support Python 3 ([#2417](https://github.com/DataDog/integrations-core/pull/2417))

***Fixed***:

* Move metrics definition and logic into its own module ([#2381](https://github.com/DataDog/integrations-core/pull/2381))

## 1.8.0 / 2018-10-12 / Agent 6.6.0

***Added***:

* Added delayed_unassigned_shards metric ([#2361](https://github.com/DataDog/integrations-core/pull/2361))
* Added inflight_requests metrics (version 5.4 and later). ([#2360](https://github.com/DataDog/integrations-core/pull/2360))

***Fixed***:

* Move config parser to its own module ([#2370](https://github.com/DataDog/integrations-core/pull/2370))

## 1.7.1 / 2018-09-04 / Agent 6.5.0

***Fixed***:

* Add thread write queue to fix Elasticsearch 6.3.x compatibility ([#1943](https://github.com/DataDog/integrations-core/pull/1943))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.7.0 / 2018-06-07

***Added***:

* Package `auto_conf.yaml` for appropriate integrations ([#1664](https://github.com/DataDog/integrations-core/pull/1664))

***Fixed***:

* [FIXED] Ensure base url path isn't removed when admin_forwarder is used ([#1202](https://github.com/DataDog/integrations-core/pull/1202))

## 1.6.0 / 2018-05-11

***Added***:

* Hardcode the 9200 port in the Autodiscovery template ([#1444](https://github.com/DataDog/integrations-core/issues/1444))
* adds `index_stats` to collect index level metrics ([#1312](https://github.com/DataDog/integrations-core/issues/1312))

## 1.5.0 / 2018-02-13

***Added***:

* Adds `admin_forwarder` option to keep URL intact when using forwarder ([#1050](https://github.com/DataDog/integrations-core/issues/1050))
* Adds `cluster_name` tag to the `elasticsearch.cluster_health` service check ([#1038](https://github.com/DataDog/integrations-core/pull/1038))

***Fixed***:

* Fixes bug that causes poor failovers when authentication fails ([#1026](https://github.com/DataDog/integrations-core/issues/1026))

## 1.4.0 / 2018-01-10

***Fixed***:

* Fix missing fs metrics for elastic >= 5 ([#997](https://github.com/DataDog/integrations-core/pull/997))

## 1.3.0 / 2018-01-10

***Added***:

* adds `pshard_graceful_timeout` that will skip pshard_stats if TO ([#463](https://github)com/DataDog/integrations-core/issues/463)

***Fixed***:

* get rid of pretty json ([#893](https://github.com/DataDog/integrations-core/issues/893))

## 1.2.0 / 2017-11-21

***Added***:

* Update auto_conf template to support agent 6 and 5.20+ ([#860](https://github)com/DataDog/integrations-core/issues/860)

## 1.1.0 / 2017-11-21

***Added***:

* Added more JVM metrics ([#695](https://github)com/DataDog/integrations-core/issues/695)
* Add metric on the average time spent by tasks in the pending queue ([#820](https://github)com/DataDog/integrations-core/issues/820)

***Fixed***:

* Fixes bug for retreiving indices count ([#806](https://github)com/DataDog/integrations-core/issues/806)

## 1.0.1 / 2017-08-28

***Added***:

* Add metric for index count ([#617](https://github)com/DataDog/integrations-core/issues/617)

## 1.0.0 / 2017-03-22

***Added***:

* adds elastic integration.
