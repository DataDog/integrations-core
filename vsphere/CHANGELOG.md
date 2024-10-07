# CHANGELOG - vsphere

<!-- towncrier release notes start -->

## 8.0.0 / 2024-09-25

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18207](https://github.com/DataDog/integrations-core/pull/18207))
* Added the hostname_transform config option ([#18652](https://github.com/DataDog/integrations-core/pull/18652))

***Fixed***:

* Fixed excluded host tags for property metrics ([#18601](https://github.com/DataDog/integrations-core/pull/18601))
* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 7.7.0 / 2024-10-01 / 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

## 7.6.0 / 2024-07-05 / Agent 7.56.0

***Added***:

* Adding an include_events config option to vSphere ([#17855](https://github.com/DataDog/integrations-core/pull/17855))
* Added more events/resource to be filtered in vSphere with event_resource_filters ([#17917](https://github.com/DataDog/integrations-core/pull/17917))
* Update dependencies ([#17953](https://github.com/DataDog/integrations-core/pull/17953))

## 7.5.3 / 2024-05-31 / Agent 7.55.0

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))

## 7.5.2 / 2024-04-26 / Agent 7.54.0

***Fixed***:

* Only collect property metrics for resources that support it and lower level for log line ([#17446](https://github.com/DataDog/integrations-core/pull/17446))

## 7.5.1 / 2024-04-17

***Fixed***:

* Add additional tags on events for non-host resources. ([#17403](https://github.com/DataDog/integrations-core/pull/17403))

## 7.5.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Collect a new vSphere metric: cpu.usage.vcpus.avg ([#17087](https://github.com/DataDog/integrations-core/pull/17087))

***Fixed***:

* Add `ssl_cafile` config. ([#16903](https://github.com/DataDog/integrations-core/pull/16903))

## 7.4.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update pyvmomi to 8.0.2.0.1 ([#16542](https://github.com/DataDog/integrations-core/pull/16542))
* Update dependencies ([#16788](https://github.com/DataDog/integrations-core/pull/16788))
* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 7.3.0 / 2023-12-11 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

***Fixed***:

* Fix error in property metric collection when an intermediate attribute is not defined ([#16296](https://github.com/DataDog/integrations-core/pull/16296))
* Fix typo in log line ([#16314](https://github.com/DataDog/integrations-core/pull/16314))
* Submit boolean properties as metric values ([#16315](https://github.com/DataDog/integrations-core/pull/16315))
* Use correct size parameters when creating batches ([#16380](https://github.com/DataDog/integrations-core/pull/16380))

## 7.2.0 / 2023-11-07 / Agent 7.50.0

***Added***:

* Add support for configuring what resources to collect events for. ([#15992](https://github.com/DataDog/integrations-core/pull/15992))

## 7.1.0 / 2023-09-29 / Agent 7.49.0

***Added***:

* Decouple resource groups and collection type ([#15670](https://github.com/DataDog/integrations-core/pull/15670))
    * _Note:_ When updating to this version, note that VMs are now considered historical entities. If you are using an instance to only collect historical entities, review your configuration to ensure you are handling VMs.

***Fixed***:

* Add ability to filter property metrics ([#15474](https://github.com/DataDog/integrations-core/pull/15474))

## 7.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Add support for datastore property metrics ([#15389](https://github.com/DataDog/integrations-core/pull/15389))
* Add cluster property metrics ([#15361](https://github.com/DataDog/integrations-core/pull/15361))
* Add support for host property metrics  ([#15347](https://github.com/DataDog/integrations-core/pull/15347))
* Add support for VM property metrics ([#14787](https://github.com/DataDog/integrations-core/pull/14787))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 6.3.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))
* Add ability to choose tag to append to VM hostname ([#14657](https://github.com/DataDog/integrations-core/pull/14657))
* Add new performance counter metrics ([#14625](https://github.com/DataDog/integrations-core/pull/14625))

***Fixed***:

* Always filter tags when constructing tags recursively and add improve testing  ([#14583](https://github.com/DataDog/integrations-core/pull/14583))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Handle None return value from RetrievePropertiesEx ([#14699](https://github.com/DataDog/integrations-core/pull/14699))

## 6.2.2 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Add error handling when getting tags from API ([#14566](https://github.com/DataDog/integrations-core/pull/14566))

## 6.2.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))

## 6.2.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Add connection refresh option ([#11507](https://github.com/DataDog/integrations-core/pull/11507))
* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 6.1.2 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Fix uncommented parent options ([#12013](https://github.com/DataDog/integrations-core/pull/12013))

## 6.1.1 / 2022-04-11 / Agent 7.36.0

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11800](https://github.com/DataDog/integrations-core/pull/11800))

## 6.1.0 / 2022-04-05

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 6.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11456](https://github.com/DataDog/integrations-core/pull/11456))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 5.12.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 5.12.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 5.11.2 / 2021-08-30

***Fixed***:

* Fix crash when some permissions are missing ([#10012](https://github.com/DataDog/integrations-core/pull/10012))

## 5.11.1 / 2021-08-25 / Agent 7.31.0

***Fixed***:

* Fix collect_events default ([#9979](https://github.com/DataDog/integrations-core/pull/9979))

## 5.11.0 / 2021-08-22

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

***Fixed***:

* Fix typos in log lines ([#9907](https://github.com/DataDog/integrations-core/pull/9907))
* Check if rest_api_options is empty ([#9798](https://github.com/DataDog/integrations-core/pull/9798))
* Fix config validation ([#9781](https://github.com/DataDog/integrations-core/pull/9781))

## 5.10.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add runtime configuration validation ([#9005](https://github.com/DataDog/integrations-core/pull/9005))
* Use new REST API when possible ([#9293](https://github.com/DataDog/integrations-core/pull/9293))

***Fixed***:

* Upgrade pyvmomi to 7.0.2 ([#9287](https://github.com/DataDog/integrations-core/pull/9287))

## 5.9.0 / 2021-04-01 / Agent 7.28.0

***Added***:

* Add rest_api_options to expose all RequestsWrapper options ([#9070](https://github.com/DataDog/integrations-core/pull/9070))

***Fixed***:

* Tag collection only available from vSphere 6.5 ([#8864](https://github.com/DataDog/integrations-core/pull/8864))

## 5.8.1 / 2021-02-23 / Agent 7.27.0

***Fixed***:

* Add `vsphere_cluster` tag from host parent ([#8674](https://github.com/DataDog/integrations-core/pull/8674))

## 5.8.0 / 2021-02-12

***Added***:

* Support filtering by tags set by integration ([#8603](https://github.com/DataDog/integrations-core/pull/8603))

***Fixed***:

* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 5.7.1 / 2020-10-31 / Agent 7.24.0

***Fixed***:

* Re-add empty_default_hostname to configuration by default ([#7732](https://github.com/DataDog/integrations-core/pull/7732))

## 5.7.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add datastore cluster tag ([#7603](https://github.com/DataDog/integrations-core/pull/7603))

***Fixed***:

* Better trace log ([#7608](https://github.com/DataDog/integrations-core/pull/7608))

## 5.6.0 / 2020-09-16

***Added***:

* Add hostname to vsphere debug metrics ([#7580](https://github.com/DataDog/integrations-core/pull/7580))

***Fixed***:

* Use server time to compute startTime ([#7586](https://github.com/DataDog/integrations-core/pull/7586))

## 5.5.0 / 2020-09-15

***Added***:

* Add debug logs to help support ([#7577](https://github.com/DataDog/integrations-core/pull/7577))
* Add config spec for vsphere ([#7537](https://github.com/DataDog/integrations-core/pull/7537))

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 5.4.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* Collect and submit vSphere attributes ([#7180](https://github.com/DataDog/integrations-core/pull/7180))

## 5.3.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))
* Add collect events fallback ([#6658](https://github.com/DataDog/integrations-core/pull/6658))
* Filter by allowed events ([#6659](https://github.com/DataDog/integrations-core/pull/6659))

***Fixed***:

* Provide helpful error message when releasing a project with missing or improper tags ([#6861](https://github.com/DataDog/integrations-core/pull/6861))
* Move event to non legacy folder ([#6751](https://github.com/DataDog/integrations-core/pull/6751))
* Avoid calling get_latest_event_timestamp ([#6656](https://github.com/DataDog/integrations-core/pull/6656))

## 5.2.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Add version metadata ([#6364](https://github.com/DataDog/integrations-core/pull/6364))

***Fixed***:

* Properly error when filtering resources by the `tag` property but `collect_tags` is disabled ([#6638](https://github.com/DataDog/integrations-core/pull/6638))

## 5.1.2 / 2020-04-14 / Agent 7.19.0

***Fixed***:

* Renew REST API session on failure ([#6330](https://github.com/DataDog/integrations-core/pull/6330))
* Fix vsphere capitalization ([#6278](https://github.com/DataDog/integrations-core/pull/6278))

## 5.1.1 / 2020-04-10

***Fixed***:

* Fix tags race conditions with filtering ([#6297](https://github.com/DataDog/integrations-core/pull/6297))

## 5.1.0 / 2020-04-04

***Added***:

* resource filters: allow blacklist and tag filtering ([#6194](https://github.com/DataDog/integrations-core/pull/6194))
* Add type annotations ([#6036](https://github.com/DataDog/integrations-core/pull/6036))

***Fixed***:

* Limit tags collection logic to the monitored resources only ([#6248](https://github.com/DataDog/integrations-core/pull/6248))
* Revert `to_native_string` to `to_string` for integrations ([#6238](https://github.com/DataDog/integrations-core/pull/6238))
* Deprecating the legacy implementation ([#6215](https://github.com/DataDog/integrations-core/pull/6215))
* Fix hostname resolution ([#6190](https://github.com/DataDog/integrations-core/pull/6190))
* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Fix ssl context ([#6075](https://github.com/DataDog/integrations-core/pull/6075))
* Rename `to_string()` utility to `to_native_string()` ([#5996](https://github.com/DataDog/integrations-core/pull/5996))
* Improve logging of the legacy implementation ([#5993](https://github.com/DataDog/integrations-core/pull/5993))

## 5.0.2 / 2020-02-29 / Agent 7.18.0

***Fixed***:

* Disconnect vSphere connection to the server on refresh ([#5929](https://github.com/DataDog/integrations-core/pull/5929))

## 5.0.1 / 2020-02-28

***Fixed***:

* Remove some unnecessary warnings ([#5916](https://github.com/DataDog/integrations-core/pull/5916))
* Add tags section in conf.yaml ([#5911](https://github.com/DataDog/integrations-core/pull/5911))

## 5.0.0 / 2020-02-22

***Changed***:

* vSphere new implementation ([#5251](https://github.com/DataDog/integrations-core/pull/5251))

***Added***:

* Add `tls_ignore_warning` option ([#5777](https://github.com/DataDog/integrations-core/pull/5777))
* Submit resource count metrics with their tags ([#5681](https://github.com/DataDog/integrations-core/pull/5681))
* Add tags support v2 using requests ([#5729](https://github.com/DataDog/integrations-core/pull/5729))
* Add per instance values as tag ([#5584](https://github.com/DataDog/integrations-core/pull/5584))

***Fixed***:

* Submit collected vsphere tags as host tags for realtime resources ([#5776](https://github.com/DataDog/integrations-core/pull/5776))
* Renaming vsphere_tags_prefix config to tags_prefix ([#5771](https://github.com/DataDog/integrations-core/pull/5771))
* Do not collect max, min and sum aggregates as they are the same as avg ([#5638](https://github.com/DataDog/integrations-core/pull/5638))

## 4.3.0 / 2019-12-13 / Agent 7.17.0

***Added***:

* Add ability to exclude specific host tags from host metadata ([#5201](https://github.com/DataDog/integrations-core/pull/5201))

## 4.2.2 / 2019-12-11

***Fixed***:

* Creating container views using a context manager ([#5187](https://github.com/DataDog/integrations-core/pull/5187))
* Add warning log on historical metrics collection failure ([#5161](https://github.com/DataDog/integrations-core/pull/5161))

## 4.2.1 / 2019-11-15 / Agent 7.16.0

***Fixed***:

* Collect the latest non-negative value for historical metrics ([#5026](https://github.com/DataDog/integrations-core/pull/5026))

## 4.2.0 / 2019-10-28

***Added***:

* Adds the ability to collect realtime and historical metrics in two different instances for better performance ([#4337](https://github.com/DataDog/integrations-core/pull/4337))

## 4.1.3 / 2019-06-19 / Agent 6.13.0

***Fixed***:

* Filters VMs in excluded hosts ([#3933](https://github.com/DataDog/integrations-core/pull/3933))

## 4.1.2 / 2019-06-17

***Fixed***:

* [vsphere] update metric_to_check ([#3904](https://github.com/DataDog/integrations-core/pull/3904))
* Fix handling of gray events ([#3864](https://github.com/DataDog/integrations-core/pull/3864))

## 4.1.1 / 2019-06-01 / Agent 6.12.0

***Fixed***:

* Fix event alarms publishing ([#3831](https://github.com/DataDog/integrations-core/pull/3831))
* Fix unit for vsphere.mem.usage.avg ([#3827](https://github.com/DataDog/integrations-core/pull/3827))

## 4.1.0 / 2019-04-25

***Added***:

* Adhere to code style ([#3581](https://github.com/DataDog/integrations-core/pull/3581))
* Support Python 3 ([#3250](https://github.com/DataDog/integrations-core/pull/3250))

## 4.0.0 / 2019-01-29 / Agent 6.10.0

***Changed***:

* Wait for jobs to finish before returning from check function ([#3034](https://github.com/DataDog/integrations-core/pull/3034))

## 3.6.2 / 2019-01-10 / Agent 6.9.0

***Fixed***:

* Fix tags normalization ([#2918](https://github.com/DataDog/integrations-core/pull/2918))

## 3.6.1 / 2019-01-04

***Fixed***:

* Demote critical log levels to error ([#2795](https://github.com/DataDog/integrations-core/pull/2795))

## 3.6.0 / 2018-11-29 / Agent 6.8.0

***Added***:

* Add option to collect cluster, datacenter and datastore metrics ([#2655](https://github.com/DataDog/integrations-core/pull/2655))

## 3.5.0 / 2018-11-21

***Added***:

* Handle unicode characters in vSphere object names ([#2596](https://github.com/DataDog/integrations-core/pull/2596))

## 3.4.0 / 2018-10-31

***Added***:

* Add option to use guest hostname instead of VM name ([#2479](https://github.com/DataDog/integrations-core/pull/2479))
* Upgrade requests ([#2481](https://github.com/DataDog/integrations-core/pull/2481))

***Fixed***:

* Fix "insufficient permission" error message formatting ([#2480](https://github.com/DataDog/integrations-core/pull/2480))

## 3.3.1 / 2018-09-19 / Agent 6.5.2

***Fixed***:

* Fix batch implementation logic ([#2265](https://github.com/DataDog/integrations-core/pull/2265))

## 3.3.0 / 2018-09-17

***Changed***:

* Precompute list of metric IDs to improve performance ([#2221](https://github.com/DataDog/integrations-core/pull/2221))

***Added***:

*  Add ability to filter metrics by collection level ([#2226](https://github.com/DataDog/integrations-core/pull/2226))

## 3.2.0 / 2018-09-11

***Changed***:

* Rewrite the Mor cache ([#2173](https://github.com/DataDog/integrations-core/pull/2173))

***Fixed***:

* Handle missing attributes in property collector result ([#2205](https://github.com/DataDog/integrations-core/pull/2205))
* Make the metadata cache thread safe ([#2212](https://github.com/DataDog/integrations-core/pull/2212))
* Make the connection list thread safe ([#2201](https://github.com/DataDog/integrations-core/pull/2201))
* Check that objects queue is initialized before processing it, and process it entirely ([#2192](https://github.com/DataDog/integrations-core/pull/2192))

## 3.1.0 / 2018-09-06 / Agent 6.5.0

***Changed***:

* Downgrade pyvmomi to v6.5.0.2017.5-1 ([#2180](https://github.com/DataDog/integrations-core/pull/2180))

## 3.0.0 / 2018-09-04

***Changed***:

* Upgrade pyvmomi to 6.7.0 ([#2153](https://github.com/DataDog/integrations-core/pull/2153))
* Make first level cache thread safe ([#2146](https://github.com/DataDog/integrations-core/pull/2146))

## 2.4.0 / 2018-08-30

***Changed***:

* Make the cache configuration thread safe ([#2125](https://github.com/DataDog/integrations-core/pull/2125))
* Removed unused `_clean` method, added more unit tests ([#2120](https://github.com/DataDog/integrations-core/pull/2120))

***Fixed***:

* Control size of the thread pool job queue ([#2131](https://github.com/DataDog/integrations-core/pull/2131))

## 2.3.1 / 2018-08-28

***Fixed***:

*  Fix `KeyError` due to race condition on the cache ([#2099](https://github.com/DataDog/integrations-core/pull/2099))

## 2.3.0 / 2018-08-21

***Changed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

***Fixed***:

* Drastically improve check performance by reducing number of calls to vSphere API ([#2039](https://github.com/DataDog/integrations-core/pull/2039))
* Retry connection once on failure, and correctly send CRITICAL service check if the connection still cannot be made ([#2060](https://github.com/DataDog/integrations-core/pull/2060))
* fix race condition and keyerror ([#1893](https://github.com/DataDog/integrations-core/pull/1893))

## 2.2.0 / 2018-06-20 / Agent 6.4.0

***Changed***:

* Bump requests to 2.19.1 ([#1743](https://github.com/DataDog/integrations-core/pull/1743))

## 2.1.0 / 2018-05-11

***Added***:

* Add custom tag support for service checks.

## 2.0.0 / 2018-02-28

***Added***:

* Run with Agent versions >= 6 ([#1098](https://github.com/DataDog/integrations-core/issues/1098))
* Add custom tag support ([#1178](https://github.com/DataDog/integrations-core/issues/1178))

## 1.0.4 / 2017-10-10

***Fixed***:

* Fix a possible leak of the vSphere password in the collector logs ([#722](https://github.com/DataDog/integrations-core/issues/722))

## 1.0.3 / 2017-08-28

***Fixed***:

* Fix case where metrics metadata don't contain what we expect.

## 1.0.2 / 2017-07-18

***Fixed***:

* Import `Timer` helper from `utils.timer` instead of deprecated `util` ([#484](https://github)com/DataDog/integrations-core/issues/484)

## 1.0.1 / 2017-06-05

***Fixed***:

* Fix case where returned data series are empty ([#346](https://github)com/DataDog/integrations-core/issues/346)

## 1.0.0 / 2017-03-22

***Added***:

* adds vsphere integration.
