# CHANGELOG - vsphere

## 5.1.0 / 2020-04-04

* [Added] resource filters: allow blacklist and tag filtering. See [#6194](https://github.com/DataDog/integrations-core/pull/6194).
* [Added] Add type annotations. See [#6036](https://github.com/DataDog/integrations-core/pull/6036).
* [Fixed] Limit tags collection logic to the monitored resources only. See [#6248](https://github.com/DataDog/integrations-core/pull/6248).
* [Fixed] Revert `to_native_string` to `to_string` for integrations. See [#6238](https://github.com/DataDog/integrations-core/pull/6238).
* [Fixed] Deprecating the legacy implementation. See [#6215](https://github.com/DataDog/integrations-core/pull/6215).
* [Fixed] Fix hostname resolution. See [#6190](https://github.com/DataDog/integrations-core/pull/6190).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Fix ssl context. See [#6075](https://github.com/DataDog/integrations-core/pull/6075).
* [Fixed] Rename `to_string()` utility to `to_native_string()`. See [#5996](https://github.com/DataDog/integrations-core/pull/5996).
* [Fixed] Improve logging of the legacy implementation. See [#5993](https://github.com/DataDog/integrations-core/pull/5993).

## 5.0.2 / 2020-02-29

* [Fixed] Disconnect vSphere connection to the server on refresh. See [#5929](https://github.com/DataDog/integrations-core/pull/5929).

## 5.0.1 / 2020-02-28

* [Fixed] Remove some unnecessary warnings. See [#5916](https://github.com/DataDog/integrations-core/pull/5916).
* [Fixed] Add tags section in conf.yaml. See [#5911](https://github.com/DataDog/integrations-core/pull/5911).

## 5.0.0 / 2020-02-22

* [Added] Add `tls_ignore_warning` option. See [#5777](https://github.com/DataDog/integrations-core/pull/5777).
* [Fixed] Submit collected vsphere tags as host tags for realtime resources. See [#5776](https://github.com/DataDog/integrations-core/pull/5776).
* [Fixed] Renaming vsphere_tags_prefix config to tags_prefix. See [#5771](https://github.com/DataDog/integrations-core/pull/5771).
* [Added] Submit resource count metrics with their tags. See [#5681](https://github.com/DataDog/integrations-core/pull/5681).
* [Added] Add tags support v2 using requests. See [#5729](https://github.com/DataDog/integrations-core/pull/5729).
* [Fixed] Do not collect max, min and sum aggregates as they are the same as avg. See [#5638](https://github.com/DataDog/integrations-core/pull/5638).
* [Added] Add per instance values as tag. See [#5584](https://github.com/DataDog/integrations-core/pull/5584).
* [Changed] vSphere new implementation. See [#5251](https://github.com/DataDog/integrations-core/pull/5251).

## 4.3.0 / 2019-12-13

* [Added] Add ability to exclude specific host tags from host metadata. See [#5201](https://github.com/DataDog/integrations-core/pull/5201).

## 4.2.2 / 2019-12-11

* [Fixed] Creating container views using a context manager. See [#5187](https://github.com/DataDog/integrations-core/pull/5187).
* [Fixed] Add warning log on historical metrics collection failure. See [#5161](https://github.com/DataDog/integrations-core/pull/5161).

## 4.2.1 / 2019-11-15

* [Fixed] Collect the latest non-negative value for historical metrics. See [#5026](https://github.com/DataDog/integrations-core/pull/5026).

## 4.2.0 / 2019-10-28

* [Added] Adds the ability to collect realtime and historical metrics in two different instances for better performance. See [#4337](https://github.com/DataDog/integrations-core/pull/4337).

## 4.1.3 / 2019-06-19

* [Fixed] Filters VMs in excluded hosts. See [#3933](https://github.com/DataDog/integrations-core/pull/3933).

## 4.1.2 / 2019-06-17

* [Fixed] [vsphere] update metric_to_check. See [#3904](https://github.com/DataDog/integrations-core/pull/3904).
* [Fixed] Fix handling of gray events. See [#3864](https://github.com/DataDog/integrations-core/pull/3864).

## 4.1.1 / 2019-06-01

* [Fixed] Fix event alarms publishing. See [#3831](https://github.com/DataDog/integrations-core/pull/3831).
* [Fixed] Fix unit for vsphere.mem.usage.avg. See [#3827](https://github.com/DataDog/integrations-core/pull/3827).

## 4.1.0 / 2019-04-25

* [Added] Adhere to code style. See [#3581](https://github.com/DataDog/integrations-core/pull/3581).
* [Added] Support Python 3. See [#3250](https://github.com/DataDog/integrations-core/pull/3250).

## 4.0.0 / 2019-01-29

* [Changed] Wait for jobs to finish before returning from check function. See [#3034](https://github.com/DataDog/integrations-core/pull/3034).

## 3.6.2 / 2019-01-10

* [Fixed] Fix tags normalization. See [#2918][1].

## 3.6.1 / 2019-01-04

* [Fixed] Demote critical log levels to error. See [#2795][2].

## 3.6.0 / 2018-11-29

* [Added] Add option to collect cluster, datacenter and datastore metrics. See [#2655][3].

## 3.5.0 / 2018-11-21

* [Added] Handle unicode characters in vSphere object names. See [#2596][4].

## 3.4.0 / 2018-10-31

* [Added] Add option to use guest hostname instead of VM name. See [#2479][5].
* [Added] Upgrade requests. See [#2481][6].
* [Fixed] Fix "insufficient permission" error message formatting. See [#2480][7].

## 3.3.1 / 2018-09-19

* [Fixed] Fix batch implementation logic. See [#2265][8].

## 3.3.0 / 2018-09-17

* [Added]  Add ability to filter metrics by collection level. See [#2226][9].
* [Changed] Precompute list of metric IDs to improve performance. See [#2221][10].

## 3.2.0 / 2018-09-11

* [Fixed] Handle missing attributes in property collector result. See [#2205][11].
* [Fixed] Make the metadata cache thread safe. See [#2212][12].
* [Fixed] Make the connection list thread safe. See [#2201][13].
* [Fixed] Check that objects queue is initialized before processing it, and process it entirely. See [#2192][14].
* [Changed] Rewrite the Mor cache. See [#2173][15].

## 3.1.0 / 2018-09-06

* [Changed] Downgrade pyvmomi to v6.5.0.2017.5-1. See [#2180][16].

## 3.0.0 / 2018-09-04

* [Changed] Upgrade pyvmomi to 6.7.0. See [#2153][17].
* [Changed] Make first level cache thread safe. See [#2146][18].

## 2.4.0 / 2018-08-30

* [Fixed] Control size of the thread pool job queue. See [#2131][19].
* [Changed] Make the cache configuration thread safe. See [#2125][20].
* [Changed] Removed unused `_clean` method, added more unit tests. See [#2120][21].

## 2.3.1 / 2018-08-28

* [Fixed]  Fix `KeyError` due to race condition on the cache. See [#2099][22].

## 2.3.0 / 2018-08-21

* [Fixed] Drastically improve check performance by reducing number of calls to vSphere API. See [#2039][23].
* [Fixed] Retry connection once on failure, and correctly send CRITICAL service check if the connection still cannot be made. See [#2060][24].
* [Fixed] fix race condition and keyerror. See [#1893][25].
* [Changed] Add data files to the wheel package. See [#1727][26].

## 2.2.0 / 2018-06-20

* [Changed] Bump requests to 2.19.1. See [#1743][27].

## 2.1.0 / 2018-05-11

* [FEATURE] Add custom tag support for service checks.

## 2.0.0 / 2018-02-28

* [FEATURE] Run with Agent versions >= 6. See [#1098][28].
* [FEATURE] Add custom tag support. See [#1178][29].

## 1.0.4 / 2017-10-10

* [BUGFIX] Fix a possible leak of the vSphere password in the collector logs. See [#722][30].

## 1.0.3 / 2017-08-28

* [BUGFIX] Fix case where metrics metadata don't contain what we expect.

## 1.0.2 / 2017-07-18

* [SANITY] Import `Timer` helper from `utils.timer` instead of deprecated `util`. See [#484][31]

## 1.0.1 / 2017-06-05

* [BUGFIX] Fix case where returned data series are empty. See [#346][32]

## 1.0.0 / 2017-03-22

* [FEATURE] adds vsphere integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2918
[2]: https://github.com/DataDog/integrations-core/pull/2795
[3]: https://github.com/DataDog/integrations-core/pull/2655
[4]: https://github.com/DataDog/integrations-core/pull/2596
[5]: https://github.com/DataDog/integrations-core/pull/2479
[6]: https://github.com/DataDog/integrations-core/pull/2481
[7]: https://github.com/DataDog/integrations-core/pull/2480
[8]: https://github.com/DataDog/integrations-core/pull/2265
[9]: https://github.com/DataDog/integrations-core/pull/2226
[10]: https://github.com/DataDog/integrations-core/pull/2221
[11]: https://github.com/DataDog/integrations-core/pull/2205
[12]: https://github.com/DataDog/integrations-core/pull/2212
[13]: https://github.com/DataDog/integrations-core/pull/2201
[14]: https://github.com/DataDog/integrations-core/pull/2192
[15]: https://github.com/DataDog/integrations-core/pull/2173
[16]: https://github.com/DataDog/integrations-core/pull/2180
[17]: https://github.com/DataDog/integrations-core/pull/2153
[18]: https://github.com/DataDog/integrations-core/pull/2146
[19]: https://github.com/DataDog/integrations-core/pull/2131
[20]: https://github.com/DataDog/integrations-core/pull/2125
[21]: https://github.com/DataDog/integrations-core/pull/2120
[22]: https://github.com/DataDog/integrations-core/pull/2099
[23]: https://github.com/DataDog/integrations-core/pull/2039
[24]: https://github.com/DataDog/integrations-core/pull/2060
[25]: https://github.com/DataDog/integrations-core/pull/1893
[26]: https://github.com/DataDog/integrations-core/pull/1727
[27]: https://github.com/DataDog/integrations-core/pull/1743
[28]: https://github.com/DataDog/integrations-core/issues/1098
[29]: https://github.com/DataDog/integrations-core/issues/1178
[30]: https://github.com/DataDog/integrations-core/issues/722
[31]: https://github.com/DataDog/integrations-core/issues/484
[32]: https://github.com/DataDog/integrations-core/issues/346
