# CHANGELOG - snmp

## 2.5.0 / 2020-02-27

* [Added] Query discovered devices in threads. See [#5462](https://github.com/DataDog/integrations-core/pull/5462).
* [Fixed] Fix issue with tags leaking between discovered instances. See [#5899](https://github.com/DataDog/integrations-core/pull/5899).

## 2.4.1 / 2020-02-25

* [Fixed] Handle case when servers report two values for entries in `metric_tags`. See [#5853](https://github.com/DataDog/integrations-core/pull/5853).

## 2.4.0 / 2020-02-22

* [Added] Add extension mechanism for SNMP profiles. See [#5821](https://github.com/DataDog/integrations-core/pull/5821).
* [Fixed] Switch back to most specific profile matching. See [#5813](https://github.com/DataDog/integrations-core/pull/5813).
* [Added] Add snmp_host tag by default to profiles. See [#5812](https://github.com/DataDog/integrations-core/pull/5812).
* [Added] Add hpe proliant profile. See [#5724](https://github.com/DataDog/integrations-core/pull/5724).
* [Added] Tag metrics by profile. See [#5787](https://github.com/DataDog/integrations-core/pull/5787).
* [Added] Add `ignored_ip_addresses` option to ignore specific IP addresses when scanning a network.. See [#5785](https://github.com/DataDog/integrations-core/pull/5785).
* [Added] Add basic types to SNMP integration. See [#5782](https://github.com/DataDog/integrations-core/pull/5782).
* [Added] Use all matching profiles instead of only the most specific one. See [#5768](https://github.com/DataDog/integrations-core/pull/5768).
* [Added] Add a new metric_tags configuration. See [#5765](https://github.com/DataDog/integrations-core/pull/5765).
* [Added] Add profile for HP iLO4 devices. See [#5637](https://github.com/DataDog/integrations-core/pull/5637).
* [Added] Fetch sysUpTimeInstance automatically. See [#5752](https://github.com/DataDog/integrations-core/pull/5752).
* [Added] Add Dell Poweredge profile. See [#5723](https://github.com/DataDog/integrations-core/pull/5723).

## 2.3.2 / 2020-01-15

* [Fixed] Tweak behavior related to discovery. See [#5466](https://github.com/DataDog/integrations-core/pull/5466).

## 2.3.1 / 2020-01-13

* [Fixed] Fix usage of old OID list attributes on InstanceConfig. See [#5412](https://github.com/DataDog/integrations-core/pull/5412).

## 2.3.0 / 2020-01-07

* [Added] Remove MIB requirement in profiles. See [#5397](https://github.com/DataDog/integrations-core/pull/5397).
* [Added] Implement table browsing with OIDs. See [#5368](https://github.com/DataDog/integrations-core/pull/5368).
* [Added] Update license years. See [#5384](https://github.com/DataDog/integrations-core/pull/5384).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Add a profile for Meraki cloud devices. See [#5215](https://github.com/DataDog/integrations-core/pull/5215).

## 2.2.0 / 2020-01-02

* [Added] Add profile for Cisco Nexus switches. See [#5363](https://github.com/DataDog/integrations-core/pull/5363).
* [Added] Add profile for Intel IDRAC devices. See [#5227](https://github.com/DataDog/integrations-core/pull/5227).
* [Fixed] Fetch table OIDs per table. See [#5192](https://github.com/DataDog/integrations-core/pull/5192).

## 2.1.0 / 2019-11-27

* [Fixed] Disable MIB autofetch. See [#5094](https://github.com/DataDog/integrations-core/pull/5094).
* [Added] Add Cisco 3850 profile. See [#5090](https://github.com/DataDog/integrations-core/pull/5090).

## 2.0.1 / 2019-11-21

* [Fixed] Handle total_time_to_temporal_percent missing. See [#5055](https://github.com/DataDog/integrations-core/pull/5055).

## 2.0.0 / 2019-11-15

* [Added] Add interface statuses to profiles. See [#5004](https://github.com/DataDog/integrations-core/pull/5004).
* [Added] Ignore metrics that are not retrieved. See [#5003](https://github.com/DataDog/integrations-core/pull/5003).
* [Changed] Modify profile layout. See [#4997](https://github.com/DataDog/integrations-core/pull/4997).
* [Added] Match profile with sysobject_id prefix. See [#4990](https://github.com/DataDog/integrations-core/pull/4990).
* [Added] Count the number of discovered devices. See [#4978](https://github.com/DataDog/integrations-core/pull/4978).
* [Added] Generic network router profile. See [#4937](https://github.com/DataDog/integrations-core/pull/4937).
* [Added] Allow tagging through different MIBs. See [#4853](https://github.com/DataDog/integrations-core/pull/4853).

## 1.14.1 / 2019-10-16

* [Fixed] Fix allowed host failure retry logic. See [#4782](https://github.com/DataDog/integrations-core/pull/4782).

## 1.14.0 / 2019-10-14

* [Added] Store discovered hosts. See [#4712](https://github.com/DataDog/integrations-core/pull/4712).

## 1.13.0 / 2019-10-11

* [Added] Automatically fetch MIBs that we don't know about. See [#4732](https://github.com/DataDog/integrations-core/pull/4732).

## 1.12.0 / 2019-10-10

* [Added] Add profile for F5 BIG-IP devices. See [#4674](https://github.com/DataDog/integrations-core/pull/4674).

## 1.11.0 / 2019-09-19

* [Fixed] Handle bytes in network_address. See [#4577](https://github.com/DataDog/integrations-core/pull/4577).
* [Added] Use bulk call when possible. See [#4530](https://github.com/DataDog/integrations-core/pull/4530).
* [Added] Remove failing discovered hosts. See [#4526](https://github.com/DataDog/integrations-core/pull/4526).
* [Added] Basic discovery mechanism and test. See [#4511](https://github.com/DataDog/integrations-core/pull/4511).
* [Added] Allow autoconfiguration of instances by sysObjectId. See [#4391](https://github.com/DataDog/integrations-core/pull/4391).

## 1.10.0 / 2019-08-24

* [Added] Support referencing metrics by profile. See [#4329](https://github.com/DataDog/integrations-core/pull/4329).
* [Added] Upgrade pyasn1. See [#4289](https://github.com/DataDog/integrations-core/pull/4289).
* [Added] Reimplement config load logic. See [#4160](https://github.com/DataDog/integrations-core/pull/4160).

## 1.9.0 / 2019-07-13

* [Added] Add support for string types. See [#4087](https://github.com/DataDog/integrations-core/pull/4087).

## 1.8.0 / 2019-07-04

* [Added] Match OIDs with leading dots. See [#3854](https://github.com/DataDog/integrations-core/pull/3854).

## 1.7.0 / 2019-05-14

* [Added] Adhere to code style. See [#3565](https://github.com/DataDog/integrations-core/pull/3565).

## 1.6.0 / 2019-03-29

* [Added] Add metrics config globally. See [#3230](https://github.com/DataDog/integrations-core/pull/3230).

## 1.5.0 / 2019-02-18

* [Added] Improve performance by querying only necessary columns from a table. See [#3059](https://github.com/DataDog/integrations-core/pull/3059).
* [Fixed] Log the correct information about snmpnext result. See [#3021](https://github.com/DataDog/integrations-core/pull/3021).
* [Added] Support Python 3. See [#3016](https://github.com/DataDog/integrations-core/pull/3016).

## 1.4.2 / 2018-10-12

* [Fixed] Fix `enforce_mib_constraints` parameter having no effect.. See [#2340][1].

## 1.4.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.4.0 / 2018-05-11

* [IMPROVEMENT] Enhance error handling when metrics aren't defined or device cannot be reached. See [#1406][3]

## 1.3.1 / 2018-02-13

* [BUGFIX] Fix warning service check reporting. See [#1041][4]

## 1.3.0 / 2017-10-10

* [FEATURE] Add support for SNMPv3 Contexts. See [#723][5]

## 1.2.0 / 2017-07-18

* [IMPROVEMENT] Drop dependency on pycrypto. See [#426][6]

## 1.1.0 / 2017-04-24

* [FEATURE] Add individual metric tagging to OID and MIB Non-tabular data. See [#248][7]

## 1.0.0 / 2017-03-22

* [FEATURE] adds snmp integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2340
[2]: https://github.com/DataDog/integrations-core/pull/1727
[3]: https://github.com/DataDog/integrations-core/issues/1406
[4]: https://github.com/DataDog/integrations-core/issues/1041
[5]: https://github.com/DataDog/integrations-core/issues/723
[6]: https://github.com/DataDog/integrations-core/issues/426
[7]: https://github.com/DataDog/integrations-core/issues/248
