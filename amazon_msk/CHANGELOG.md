# CHANGELOG - Amazon MSK

<!-- towncrier release notes start -->

## 4.7.0 / 2024-04-26

***Added***:

* Update dependencies ([#17319](https://github.com/DataDog/integrations-core/pull/17319))
* Upgrade boto dependencies ([#17332](https://github.com/DataDog/integrations-core/pull/17332))

## 4.6.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update dependencies ([#16899](https://github.com/DataDog/integrations-core/pull/16899)), ([#16963](https://github.com/DataDog/integrations-core/pull/16963))

## 4.5.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update dependencies ([#16788](https://github.com/DataDog/integrations-core/pull/16788))
* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))
* Bump dependencies ([#16858](https://github.com/DataDog/integrations-core/pull/16858))

## 4.4.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Update dependencies ([#16394](https://github.com/DataDog/integrations-core/pull/16394)), ([#16448](https://github.com/DataDog/integrations-core/pull/16448)), ([#16502](https://github.com/DataDog/integrations-core/pull/16502))

***Fixed***:

* Fix TypeError when tags are undefined ([#16496](https://github.com/DataDog/integrations-core/pull/16496))

## 4.3.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Updated dependencies. ([#16154](https://github.com/DataDog/integrations-core/pull/16154))

## 4.2.0 / 2023-09-29 / Agent 7.49.0

***Added***:

* Update Boto3 dependency to 1.28.55 ([#15922](https://github.com/DataDog/integrations-core/pull/15922))

## 4.1.0 / 2023-08-18 / Agent 7.48.0

***Added***:

* Update dependencies for Agent 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))

## 4.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 3.5.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.4.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))
* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 3.3.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Update dependencies ([#14357](https://github.com/DataDog/integrations-core/pull/14357))

## 3.2.4 / 2023-03-03 / Agent 7.44.0

***Fixed***:

* Switch count method to monotonic count, that's correct for OM counts ([#13972](https://github.com/DataDog/integrations-core/pull/13972))
* Submit count versions of metrics that we mistakenly submit as gauges ([#13886](https://github.com/DataDog/integrations-core/pull/13886))

## 3.2.3 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))

## 3.2.2 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))

## 3.2.1 / 2022-10-28 / Agent 7.41.0

***Fixed***:

* Update dependencies ([#13205](https://github.com/DataDog/integrations-core/pull/13205))

## 3.2.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

***Fixed***:

* Bump dependencies for 7.40 ([#12896](https://github.com/DataDog/integrations-core/pull/12896))

## 3.1.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 3.1.2 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 3.1.1 / 2022-05-15

***Fixed***:

* Upgrade dependencies ([#11958](https://github.com/DataDog/integrations-core/pull/11958))

## 3.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 3.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Allow disabling querying an exporter ([#11306](https://github.com/DataDog/integrations-core/pull/11306))
* Add `pyproject.toml` file ([#11313](https://github.com/DataDog/integrations-core/pull/11313))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 2.1.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 2.1.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))
* Update dependencies ([#10580](https://github.com/DataDog/integrations-core/pull/10580))

## 2.0.2 / 2021-10-15 / Agent 7.32.0

***Fixed***:

* [OpenMetricsV2] Allow empty namespaces ([#10420](https://github.com/DataDog/integrations-core/pull/10420))

## 2.0.1 / 2021-10-12

***Fixed***:

* Account for errors in boto client creation ([#10386](https://github.com/DataDog/integrations-core/pull/10386))

## 2.0.0 / 2021-10-04

***Changed***:

* Update Amazon MSK documentation to the new implementation ([#9993](https://github.com/DataDog/integrations-core/pull/9993))

***Added***:

* Update dependencies ([#10228](https://github.com/DataDog/integrations-core/pull/10228))
* Add proxy support in client initialization ([#10188](https://github.com/DataDog/integrations-core/pull/10188))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.8.1 / 2021-07-16 / Agent 7.30.0

***Fixed***:

* Describe py3 requirement of use_openmetrics option ([#9714](https://github.com/DataDog/integrations-core/pull/9714))

## 1.8.0 / 2021-07-12

***Added***:

* Add metrics from label IDs ([#9643](https://github.com/DataDog/integrations-core/pull/9643))
* Upgrade some core dependencies ([#9499](https://github.com/DataDog/integrations-core/pull/9499))

***Fixed***:

* Raise exception if attempting to use new style openmetrics with py2 ([#9613](https://github.com/DataDog/integrations-core/pull/9613))

## 1.7.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))

***Fixed***:

* Fix `metrics` option type for legacy OpenMetrics config spec ([#9318](https://github.com/DataDog/integrations-core/pull/9318)) Thanks [jejikenwogu](https://github.com/jejikenwogu).

## 1.6.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Allow the use of the new OpenMetrics implementation ([#9082](https://github.com/DataDog/integrations-core/pull/9082))
* Add runtime configuration validation ([#8883](https://github.com/DataDog/integrations-core/pull/8883))

***Fixed***:

* Bump minimum base package ([#9107](https://github.com/DataDog/integrations-core/pull/9107))

## 1.5.0 / 2021-03-24

***Added***:

* Add `kafka_consumer_group_ConsumerLagMetrics_Value` metric ([#9027](https://github.com/DataDog/integrations-core/pull/9027)) Thanks [idarlington](https://github.com/idarlington).
* Allow prometheus metrics path to be configurable ([#9028](https://github.com/DataDog/integrations-core/pull/9028))

## 1.4.1 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Hide auto-populated prometheus_url from config spec ([#8330](https://github.com/DataDog/integrations-core/pull/8330))
* Update prometheus_metrics_prefix documentation ([#8236](https://github.com/DataDog/integrations-core/pull/8236))

## 1.4.0 / 2020-12-11 / Agent 7.25.0

***Added***:

* Add ability to assume a specified role when retrieving MSK metadata ([#8118](https://github.com/DataDog/integrations-core/pull/8118)) Thanks [garrett528](https://github.com/garrett528).

## 1.3.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Sync openmetrics config specs with new option ignore_metrics_by_labels ([#7823](https://github.com/DataDog/integrations-core/pull/7823))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))

## 1.2.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))
* Add config specs ([#7291](https://github.com/DataDog/integrations-core/pull/7291))

## 1.1.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.0.0 / 2019-12-03 / Agent 7.16.1

***Added***:

* Add Amazon MSK integration ([#5127](https://github.com/DataDog/integrations-core/pull/5127))
