# CHANGELOG - snmp

## 4.0.0 / 2021-01-25

* [Added] Snmp Juniper profiles for EX (switches), MX (routers) and SRX (firewalls) series. See [#8206](https://github.com/DataDog/integrations-core/pull/8206).
* [Fixed] Use mibless syntax for _generic-host-resources.yaml. See [#8305](https://github.com/DataDog/integrations-core/pull/8305).
* [Changed] Add missing metrics to hp-ilo4 profile. See [#8220](https://github.com/DataDog/integrations-core/pull/8220).

## 3.10.0 / 2020-12-07 / Agent 7.25.0

* [Added] Add snmp interface bandwidth usage metric. See [#8093](https://github.com/DataDog/integrations-core/pull/8093).
* [Added] Add interface alias (ifAlias) as a tag to interface metrics. See [#8018](https://github.com/DataDog/integrations-core/pull/8018). Thanks [loganmc10](https://github.com/loganmc10).
* [Added] Add generic Cisco ASA profile. See [#7971](https://github.com/DataDog/integrations-core/pull/7971).
* [Fixed] Use MIB less syntax in example and link to profile format doc. See [#8073](https://github.com/DataDog/integrations-core/pull/8073).
* [Fixed] Add back cisco-asa-5525.yaml. See [#8041](https://github.com/DataDog/integrations-core/pull/8041).
* [Fixed] Improve symbol metric example. See [#8071](https://github.com/DataDog/integrations-core/pull/8071).
* [Fixed] Add deprecation notice for metric[].name syntax. See [#8070](https://github.com/DataDog/integrations-core/pull/8070).
* [Fixed] Add device_index to idrac (AI-938). See [#7525](https://github.com/DataDog/integrations-core/pull/7525).

## 3.9.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add 'device vendor' tag to metrics. See [#7871](https://github.com/DataDog/integrations-core/pull/7871).
* [Added] Track fetch ID in debug logs. See [#7736](https://github.com/DataDog/integrations-core/pull/7736).
* [Added] Make refresh_oids_cache_interval available as init_config. See [#7821](https://github.com/DataDog/integrations-core/pull/7821).
* [Added] Support alternative Mac Address index. See [#7688](https://github.com/DataDog/integrations-core/pull/7688).
* [Fixed] Adding tag ciscoEnvMonSupplyStatusDescr to disambiguate metric. See [#7782](https://github.com/DataDog/integrations-core/pull/7782).

## 3.8.0 / 2020-09-04 / Agent 7.23.0

* [Added] Add `index_transform` to support tagging using another table with different indexes. See [#7489](https://github.com/DataDog/integrations-core/pull/7489).
* [Fixed] Validate SNMP profile hierarchy. See [#6798](https://github.com/DataDog/integrations-core/pull/6798).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 3.7.1 / 2020-08-12 / Agent 7.22.0

* [Fixed] Fix apc ups profile. See [#7351](https://github.com/DataDog/integrations-core/pull/7351).
* [Fixed] Revert Fix wrong indentation of `table` key in column metric tags #7024. See [#7349](https://github.com/DataDog/integrations-core/pull/7349).

## 3.7.0 / 2020-08-03

* [Added] Add OID caching. See [#7231](https://github.com/DataDog/integrations-core/pull/7231).
* [Fixed] Refactor how OIDs are managed. See [#7230](https://github.com/DataDog/integrations-core/pull/7230).
* [Fixed] Sanitize OctetString. See [#7221](https://github.com/DataDog/integrations-core/pull/7221).
* [Fixed] Rename all_oids to scalar_oids. See [#7229](https://github.com/DataDog/integrations-core/pull/7229).
* [Fixed] Better logging for submit_metric. See [#7188](https://github.com/DataDog/integrations-core/pull/7188).

## 3.6.0 / 2020-07-24

* [Added] Check tag for table metric. See [#6933](https://github.com/DataDog/integrations-core/pull/6933).
* [Added] Add new `flag_stream` type. See [#7072](https://github.com/DataDog/integrations-core/pull/7072).
* [Added] Add cisco catalyst profile. See [#6925](https://github.com/DataDog/integrations-core/pull/6925).
* [Added] Allow list of sysoids in profiles. See [#6936](https://github.com/DataDog/integrations-core/pull/6936).
* [Fixed] Sanitize forced types values and cast to float. See [#7133](https://github.com/DataDog/integrations-core/pull/7133).
* [Fixed] Add `.0` to scalar oids. See [#7105](https://github.com/DataDog/integrations-core/pull/7105).
* [Fixed] Use OID instead of MIB for sysName. See [#7104](https://github.com/DataDog/integrations-core/pull/7104).
* [Fixed] Submit additional rate metrics in fortigate profile. See [#7058](https://github.com/DataDog/integrations-core/pull/7058).

## 3.5.3 / 2020-07-01 / Agent 7.21.0

* [Fixed] Fix autodiscovery_subnet var in auto_conf.yaml. See [#7029](https://github.com/DataDog/integrations-core/pull/7029).

## 3.5.2 / 2020-06-30

* [Fixed] Fix tag names for cisco asa profile. See [#7027](https://github.com/DataDog/integrations-core/pull/7027).

## 3.5.1 / 2020-06-30

* [Fixed] Fix wrong indentation of `table` key in column metric tags. See [#7024](https://github.com/DataDog/integrations-core/pull/7024).

## 3.5.0 / 2020-06-29

* [Added] Add regex match support for Tables. See [#6951](https://github.com/DataDog/integrations-core/pull/6951).
* [Added] Add snmp.devices_monitored metric. See [#6941](https://github.com/DataDog/integrations-core/pull/6941).
* [Added] Add IF-MIB metrics to the Meraki profile. See [#6905](https://github.com/DataDog/integrations-core/pull/6905).
* [Added] Add RTT metrics. See [#6872](https://github.com/DataDog/integrations-core/pull/6872).
* [Fixed] Clean up of unused extends in meraki cloud profile. See [#6981](https://github.com/DataDog/integrations-core/pull/6981).
* [Fixed] [Refactor] Add device abstraction. See [#6953](https://github.com/DataDog/integrations-core/pull/6953).
* [Fixed] [Refactor] Clean up batching implementation. See [#6952](https://github.com/DataDog/integrations-core/pull/6952).
* [Fixed] Add index tagging to cfwConnectionStatValue. See [#6897](https://github.com/DataDog/integrations-core/pull/6897).

## 3.4.0 / 2020-06-11

* [Added] Add NetApp profile. See [#6841](https://github.com/DataDog/integrations-core/pull/6841).
* [Fixed] Fix `instance_number` tag on Cisco voice router metrics. See [#6867](https://github.com/DataDog/integrations-core/pull/6867).

## 3.3.0 / 2020-06-10

* [Added] Add Fortinet FortiGate profile. See [#6504](https://github.com/DataDog/integrations-core/pull/6504). Thanks [lindseyferretti](https://github.com/lindseyferretti).
* [Added] Reuse MIB builder objects per SNMP engine. See [#6716](https://github.com/DataDog/integrations-core/pull/6716).
* [Added] Add HP health profile mixin. See [#6757](https://github.com/DataDog/integrations-core/pull/6757).
* [Added] Add routing metrics to additional profiles. See [#6764](https://github.com/DataDog/integrations-core/pull/6764).
* [Added] Add router metrics to cisco voice base profile. See [#6737](https://github.com/DataDog/integrations-core/pull/6737).
* [Fixed] Fix gauge metrics wrongly submitted as rates in CISCO voice profile. See [#6794](https://github.com/DataDog/integrations-core/pull/6794).
* [Fixed] Push received metrics on partial failure. See [#6814](https://github.com/DataDog/integrations-core/pull/6814).
* [Fixed] Flatten Cisco profiles hierarchy. See [#6792](https://github.com/DataDog/integrations-core/pull/6792).
* [Fixed] Add missing tags to profiles tables. See [#6765](https://github.com/DataDog/integrations-core/pull/6765).
* [Fixed] Fix name KeyError. See [#6788](https://github.com/DataDog/integrations-core/pull/6788).
* [Fixed] Properly handle potential embedded null characters. See [#6640](https://github.com/DataDog/integrations-core/pull/6640).
* [Fixed] Remove iDRAC/poweredge profile inheritance. See [#6754](https://github.com/DataDog/integrations-core/pull/6754).
* [Fixed] Make profiles compatible with previous parsing. See [#6750](https://github.com/DataDog/integrations-core/pull/6750).

## 3.2.2 / 2020-05-21 / Agent 7.20.0

* [Fixed] Fix error handling in getnext. See [#6701](https://github.com/DataDog/integrations-core/pull/6701).

## 3.2.1 / 2020-05-19

* [Fixed] Add missing auto_conf. See [#6687](https://github.com/DataDog/integrations-core/pull/6687).

## 3.2.0 / 2020-05-17

* [Added] Add diskStatus tag to Isilon profile. See [#6660](https://github.com/DataDog/integrations-core/pull/6660).
* [Added] Add BPG metrics to more profiles. See [#6655](https://github.com/DataDog/integrations-core/pull/6655).
* [Added] Add voice metrics and profiles. See [#6629](https://github.com/DataDog/integrations-core/pull/6629).

## 3.1.0 / 2020-05-14

* [Added] Add `chatsworth` legacy metrics. See [#6624](https://github.com/DataDog/integrations-core/pull/6624).
* [Added] Add ifHighSpeed. See [#6602](https://github.com/DataDog/integrations-core/pull/6602).
* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Improve autodiscovery support. See [#6526](https://github.com/DataDog/integrations-core/pull/6526).
* [Fixed] Exit discovery thread when check is gc-ed. See [#6484](https://github.com/DataDog/integrations-core/pull/6484).
* [Fixed] Don't use ifDescr for metric tagging. See [#6601](https://github.com/DataDog/integrations-core/pull/6601).
* [Fixed] Optimize away useless GET calls. See [#6456](https://github.com/DataDog/integrations-core/pull/6456).

## 3.0.0 / 2020-05-04

* [Added] Add base BGP4 and Cisco-CSR1000v profiles. See [#6315](https://github.com/DataDog/integrations-core/pull/6315).
* [Added] Collect OSPF routing metrics. See [#6554](https://github.com/DataDog/integrations-core/pull/6554).
* [Added] Add F5 Big IP local traffic management (LTM) metrics. See [#5963](https://github.com/DataDog/integrations-core/pull/5963).
* [Added] Add more HP metrics. See [#6542](https://github.com/DataDog/integrations-core/pull/6542).
* [Added] Add more idrac/dell metrics. See [#6540](https://github.com/DataDog/integrations-core/pull/6540).
* [Added] Add additional Cisco metrics. See [#6539](https://github.com/DataDog/integrations-core/pull/6539).
* [Added] Add more metrics to Palo Alto profile. See [#6541](https://github.com/DataDog/integrations-core/pull/6541).
* [Added] Add upsOutletGroupStatusGroupState metric to APC UPS profile. See [#6555](https://github.com/DataDog/integrations-core/pull/6555).
* [Added] Add ifspeed metric to interface profile. See [#6499](https://github.com/DataDog/integrations-core/pull/6499).
* [Added] Add Isilon profile. See [#6518](https://github.com/DataDog/integrations-core/pull/6518).
* [Added] Add APC UPS profile. See [#6505](https://github.com/DataDog/integrations-core/pull/6505).
* [Added] Add env metric to cisco base profile. See [#6517](https://github.com/DataDog/integrations-core/pull/6517).
* [Added] Submit throughput as a rate. See [#6384](https://github.com/DataDog/integrations-core/pull/6384).
* [Added] Add more Cisco ASA metrics. See [#6335](https://github.com/DataDog/integrations-core/pull/6335).
* [Added] Add MIB resolution to `OID` model. See [#6242](https://github.com/DataDog/integrations-core/pull/6242).
* [Fixed] Change default timeout to 5. See [#6546](https://github.com/DataDog/integrations-core/pull/6546).
* [Fixed] Remove empty values in config. See [#6455](https://github.com/DataDog/integrations-core/pull/6455).
* [Fixed] Use `OID` model in `OIDResolver`. See [#6469](https://github.com/DataDog/integrations-core/pull/6469).
* [Fixed] Isolate parsing logic into a dedicated sub-package. See [#6398](https://github.com/DataDog/integrations-core/pull/6398).
* [Fixed] Isolate PySNMP inspection hacks. See [#6461](https://github.com/DataDog/integrations-core/pull/6461).
* [Fixed] Drop outdated `warning` parameter in `parse_metrics`. See [#6412](https://github.com/DataDog/integrations-core/pull/6412).
* [Fixed] Fix debug output. See [#6400](https://github.com/DataDog/integrations-core/pull/6400).
* [Fixed] Check types on all modules. See [#6392](https://github.com/DataDog/integrations-core/pull/6392).
* [Fixed] Fix misleading `metric_tags` naming on `ParsedMetric`. See [#6387](https://github.com/DataDog/integrations-core/pull/6387).
* [Changed] Throw error if two profiles have the same sysObjectID. See [#6501](https://github.com/DataDog/integrations-core/pull/6501).

## 2.6.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Small profiles cleanups. See [#6233](https://github.com/DataDog/integrations-core/pull/6233).
* [Fixed] Remove duplicated idrac metrics from poweredge profile. See [#6232](https://github.com/DataDog/integrations-core/pull/6232).
* [Fixed] Only load installed profiles once. See [#6231](https://github.com/DataDog/integrations-core/pull/6231).
* [Fixed] Fix tag matching documentation. See [#6226](https://github.com/DataDog/integrations-core/pull/6226).

## 2.6.0 / 2020-03-24

* [Added] Support regular expressions in dynamic tags. See [#6096](https://github.com/DataDog/integrations-core/pull/6096).
* [Added] Aruba, Arista and PDU profiles. See [#6002](https://github.com/DataDog/integrations-core/pull/6002).
* [Added] Load all profiles by default. See [#6051](https://github.com/DataDog/integrations-core/pull/6051).
* [Added] Add checkpoint firewall profile. See [#6021](https://github.com/DataDog/integrations-core/pull/6021).
* [Added] Add types to compat module. See [#6029](https://github.com/DataDog/integrations-core/pull/6029).
* [Added] Refactor and add types to `OIDResolver`. See [#6017](https://github.com/DataDog/integrations-core/pull/6017).
* [Added] Add `OID` helper class. See [#6000](https://github.com/DataDog/integrations-core/pull/6000).
* [Added] Add Cisco ASA 5525 profile and refactor cisco base profile. See [#5958](https://github.com/DataDog/integrations-core/pull/5958).
* [Added] Move PySNMP imports to a dedicated module. See [#5990](https://github.com/DataDog/integrations-core/pull/5990).
* [Added] Add Palo Alto and generic host resources SNMP profiles. See [#5914](https://github.com/DataDog/integrations-core/pull/5914).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Implement `str()` for `OID` instances. See [#6046](https://github.com/DataDog/integrations-core/pull/6046).
* [Fixed] Move metric types to new module. See [#6044](https://github.com/DataDog/integrations-core/pull/6044).
* [Fixed] Isolate logic for converting SNMP values to metrics. See [#6031](https://github.com/DataDog/integrations-core/pull/6031).
* [Fixed] Move PySNMP imports to a separate `pysnmp_types` module. See [#6013](https://github.com/DataDog/integrations-core/pull/6013).
* [Fixed] Drop unused log argument on InstanceConfig. See [#6007](https://github.com/DataDog/integrations-core/pull/6007).
* [Fixed] Add OIDs to router profiles. See [#5991](https://github.com/DataDog/integrations-core/pull/5991).
* [Fixed] Validate and cast `discovery_interval` to a number. See [#5887](https://github.com/DataDog/integrations-core/pull/5887).

## 2.5.0 / 2020-02-27 / Agent 7.18.0

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

## 2.3.2 / 2020-01-15 / Agent 7.17.0

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

## 2.1.0 / 2019-11-27 / Agent 7.16.0

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

## 1.14.1 / 2019-10-16 / Agent 6.15.0

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

## 1.10.0 / 2019-08-24 / Agent 6.14.0

* [Added] Support referencing metrics by profile. See [#4329](https://github.com/DataDog/integrations-core/pull/4329).
* [Added] Upgrade pyasn1. See [#4289](https://github.com/DataDog/integrations-core/pull/4289).
* [Added] Reimplement config load logic. See [#4160](https://github.com/DataDog/integrations-core/pull/4160).

## 1.9.0 / 2019-07-13 / Agent 6.13.0

* [Added] Add support for string types. See [#4087](https://github.com/DataDog/integrations-core/pull/4087).

## 1.8.0 / 2019-07-04

* [Added] Match OIDs with leading dots. See [#3854](https://github.com/DataDog/integrations-core/pull/3854).

## 1.7.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3565](https://github.com/DataDog/integrations-core/pull/3565).

## 1.6.0 / 2019-03-29 / Agent 6.11.0

* [Added] Add metrics config globally. See [#3230](https://github.com/DataDog/integrations-core/pull/3230).

## 1.5.0 / 2019-02-18 / Agent 6.10.0

* [Added] Improve performance by querying only necessary columns from a table. See [#3059](https://github.com/DataDog/integrations-core/pull/3059).
* [Fixed] Log the correct information about snmpnext result. See [#3021](https://github.com/DataDog/integrations-core/pull/3021).
* [Added] Support Python 3. See [#3016](https://github.com/DataDog/integrations-core/pull/3016).

## 1.4.2 / 2018-10-12 / Agent 6.6.0

* [Fixed] Fix `enforce_mib_constraints` parameter having no effect.. See [#2340][1].

## 1.4.1 / 2018-09-04 / Agent 6.5.0

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
