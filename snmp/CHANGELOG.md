# CHANGELOG - snmp

## 6.0.0 / 2023-07-10

***Changed***:

* Rename vendor profiles to match vendor.yaml. See [#15039](https://github.com/DataDog/integrations-core/pull/15039).
* Rename generic-router to generic-device. See [#14723](https://github.com/DataDog/integrations-core/pull/14723).

***Added***:

* [NDM] Add audiocodes-mediant-sbc profile. See [#15117](https://github.com/DataDog/integrations-core/pull/15117).
* Add profile for fortinet-fortiswitch. See [#15192](https://github.com/DataDog/integrations-core/pull/15192).
* Add profile for Fireeye. See [#15185](https://github.com/DataDog/integrations-core/pull/15185).
* Add profile for fortinet-appliance. See [#15188](https://github.com/DataDog/integrations-core/pull/15188).
* Add arista-switch profile. See [#15092](https://github.com/DataDog/integrations-core/pull/15092).
* Add profile cisco-ironport-email. See [#15163](https://github.com/DataDog/integrations-core/pull/15163).
* Add profile cisco-firepower. See [#15160](https://github.com/DataDog/integrations-core/pull/15160).
* Add profile for extreme-switching. See [#15164](https://github.com/DataDog/integrations-core/pull/15164).
* Add profile cisco-access-point. See [#15147](https://github.com/DataDog/integrations-core/pull/15147).
* [NDM] [SNMP] Update F5 BIGIP profile. See [#15049](https://github.com/DataDog/integrations-core/pull/15049).
* Add profile for Aruba-cx-switch. See [#15107](https://github.com/DataDog/integrations-core/pull/15107).
* Add aruba-clearpass profile. See [#15088](https://github.com/DataDog/integrations-core/pull/15088).
* Add profile for Exagrid. See [#15137](https://github.com/DataDog/integrations-core/pull/15137).
* Add profile cisco-firepower-asa. See [#15157](https://github.com/DataDog/integrations-core/pull/15157).
* [SNMP] Add profile for alcatel-lucent omni access WLC. See [#15101](https://github.com/DataDog/integrations-core/pull/15101).
* [SNMP] Add profile for alcatel-lucent ind. See [#15095](https://github.com/DataDog/integrations-core/pull/15095).
* [NDM] Add bluecat-server profile. See [#15125](https://github.com/DataDog/integrations-core/pull/15125).
* [SNMP] Add profile for alcatel-lucent ent. See [#15094](https://github.com/DataDog/integrations-core/pull/15094).
* Add profile chrysalis-luna-hsm. See [#15133](https://github.com/DataDog/integrations-core/pull/15133).
* [NDM] Add avtech-roomalert-3s. See [#15076](https://github.com/DataDog/integrations-core/pull/15076).
* Add profile watchguard. See [#15130](https://github.com/DataDog/integrations-core/pull/15130).
* [SNMP] Add profile for Anue. See [#15123](https://github.com/DataDog/integrations-core/pull/15123).
* Add profile for aruba mobility controller. See [#15109](https://github.com/DataDog/integrations-core/pull/15109).
* [NDM] Add avtech roomalert 3e profile. See [#15075](https://github.com/DataDog/integrations-core/pull/15075).
* [NDM] Add avtech-roomalert-32s. See [#15058](https://github.com/DataDog/integrations-core/pull/15058).
* [SNMP] Add profile for generic UPS. See [#15068](https://github.com/DataDog/integrations-core/pull/15068).
* Add profile brother-net-printer. See [#15102](https://github.com/DataDog/integrations-core/pull/15102).
* Add profile brocade-fc-switch. See [#15065](https://github.com/DataDog/integrations-core/pull/15065).
* Update profile a10-thunder with metric_type. See [#15086](https://github.com/DataDog/integrations-core/pull/15086).
* Add profile _generic-ucd.yaml. See [#15046](https://github.com/DataDog/integrations-core/pull/15046).
* [NDM] Add profiles for Nvidia. See [#15051](https://github.com/DataDog/integrations-core/pull/15051).
* Add profile a10-thunder. See [#14712](https://github.com/DataDog/integrations-core/pull/14712).
* Add `_generic-lldp` profile. See [#15061](https://github.com/DataDog/integrations-core/pull/15061).
* Add per vendor generic profiles. See [#14721](https://github.com/DataDog/integrations-core/pull/14721).
* Add profile 3com-huawei. See [#14694](https://github.com/DataDog/integrations-core/pull/14694).
* Update profiles with missing devices. See [#14695](https://github.com/DataDog/integrations-core/pull/14695).
* Add profile for hp-ilo. See [#14771](https://github.com/DataDog/integrations-core/pull/14771).
* Add User Profiles support. See [#14752](https://github.com/DataDog/integrations-core/pull/14752).
* Add profile 3com. See [#14693](https://github.com/DataDog/integrations-core/pull/14693).

***Fixed***:

* Update alcatel-lucent-ind with prefix . See [#15184](https://github.com/DataDog/integrations-core/pull/15184).
* Update alcatel-lucent-ent with prefix. See [#15183](https://github.com/DataDog/integrations-core/pull/15183).
* Add roomalert prefix to avtech-roomalert-32s.yaml. See [#15180](https://github.com/DataDog/integrations-core/pull/15180).
* Add roomalert3s prefix to avtech-roomalert-3s.yaml. See [#15182](https://github.com/DataDog/integrations-core/pull/15182).
* Add `roomalert3e` prefix to avtech-roomalert-3e.yaml. See [#15181](https://github.com/DataDog/integrations-core/pull/15181).
* Add missing metric_type and ucd prefix for _generic-ucd. See [#15177](https://github.com/DataDog/integrations-core/pull/15177).
* Add prefixes to `nvidia-cumulus-linux-switch`. See [#15176](https://github.com/DataDog/integrations-core/pull/15176).
* Update _generic-ups.yaml. See [#15179](https://github.com/DataDog/integrations-core/pull/15179).
* Update a10-thunder axAppGlobalTotalCurrentConnections metric_type. See [#15169](https://github.com/DataDog/integrations-core/pull/15169).
* Document _cisco-cpu-memory.yaml metrics. See [#15149](https://github.com/DataDog/integrations-core/pull/15149).
* Update metadata.csv for 3com-huawei profile. See [#15038](https://github.com/DataDog/integrations-core/pull/15038).
* Refactor hp-ilo profile vendor. See [#14823](https://github.com/DataDog/integrations-core/pull/14823).
* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).
* Remove rules from test_profile_hierarchy. See [#14703](https://github.com/DataDog/integrations-core/pull/14703).

## 5.12.0 / 2023-05-26 / Agent 7.46.0

***Added***: 

* adds sysobjectids to cisco-catalyst profile. See [#14452](https://github.com/DataDog/integrations-core/pull/14452).
* [SNMP] Enriched BGP profile. See [#14399](https://github.com/DataDog/integrations-core/pull/14399).

***Fixed***: 

* NDM: Fix memory metrics OIDs for cisco-nexus. See [#14572](https://github.com/DataDog/integrations-core/pull/14572).
* Add .0 to hp scalar metrics. See [#14558](https://github.com/DataDog/integrations-core/pull/14558).


## 5.11.0 / 2022-12-09 / Agent 7.42.0

***Added***: 

* Add topology metadata e2e test (aos_lldp). See [#13373](https://github.com/DataDog/integrations-core/pull/13373).

***Fixed***: 

* Update dependencies. See [#13478](https://github.com/DataDog/integrations-core/pull/13478).
* Remove invalid 'service' field in snmp example config. See [#13341](https://github.com/DataDog/integrations-core/pull/13341).


## 5.10.0 / 2022-09-16 / Agent 7.40.0

***Added***: 

* Refactor tooling for getting the current env name. See [#12939](https://github.com/DataDog/integrations-core/pull/12939).

***Fixed***: 

* Add virtualdomain_index tag to fgFwPolStatsTable. See [#12760](https://github.com/DataDog/integrations-core/pull/12760).


## 5.9.0 / 2022-08-05 / Agent 7.39.0

***Added***: 

* Add metrics for VPN Tunnels. See [#11977](https://github.com/DataDog/integrations-core/pull/11977). Thanks [jalmeroth](https://github.com/jalmeroth).

***Fixed***: 

* Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).


## 5.8.0 / 2022-05-15 / Agent 7.37.0

***Added***: 

* Add memory and cpu abstract metrics. See [#11781](https://github.com/DataDog/integrations-core/pull/11781).

***Fixed***: 

* Fix meraki profile mac address. See [#11871](https://github.com/DataDog/integrations-core/pull/11871).
* Add format mac_address to profile interface metadata. See [#11870](https://github.com/DataDog/integrations-core/pull/11870).
* Updating check documentation for timeout and retries. See [#11848](https://github.com/DataDog/integrations-core/pull/11848).


## 5.7.0 / 2022-04-05 / Agent 7.36.0

***Added***: 

* Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).

***Fixed***: 

* Support newer versions of `click`. See [#11746](https://github.com/DataDog/integrations-core/pull/11746).
* Add `min_collection_interval` to snmp `init_config`. See [#11543](https://github.com/DataDog/integrations-core/pull/11543).


## 5.6.0 / 2022-02-19 / Agent 7.35.0

***Added***: 

* Add `pyproject.toml` file. See [#11432](https://github.com/DataDog/integrations-core/pull/11432).

***Fixed***: 

* Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).


## 5.5.0 / 2022-01-08 / Agent 7.34.0

***Added***: 

* Add `sysMultiHostCpuUsageRatio` to BIG-IP profile. See [#10924](https://github.com/DataDog/integrations-core/pull/10924). Thanks [kei6u](https://github.com/kei6u).
* Add profile metadata for Isilon. See [#11022](https://github.com/DataDog/integrations-core/pull/11022).
* Add metadata to Dell iDRAC profile. See [#11004](https://github.com/DataDog/integrations-core/pull/11004).
* Add profile metadata for fortinet-fortigate. See [#11002](https://github.com/DataDog/integrations-core/pull/11002).
* Add profile metadata for checkpoint_firewall. See [#10998](https://github.com/DataDog/integrations-core/pull/10998).
* Add profile metadata for netapp. See [#10968](https://github.com/DataDog/integrations-core/pull/10968).
* Add metrics to apc_ups profile. See [#10967](https://github.com/DataDog/integrations-core/pull/10967).
* Add profile metadata for palo alto. See [#10956](https://github.com/DataDog/integrations-core/pull/10956).
* Add profile metadata for arista. See [#10944](https://github.com/DataDog/integrations-core/pull/10944).
* Add profile metadata for aruba. See [#10952](https://github.com/DataDog/integrations-core/pull/10952).
* Add profile metadata for Juniper. See [#11005](https://github.com/DataDog/integrations-core/pull/11005).
* Add apc_ups profile metadata. See [#10857](https://github.com/DataDog/integrations-core/pull/10857).
* Add metadata to HP profiles. See [#10867](https://github.com/DataDog/integrations-core/pull/10867).
* Add location to _base.yaml. See [#10822](https://github.com/DataDog/integrations-core/pull/10822).
* Add use_device_id_as_hostname config. See [#10812](https://github.com/DataDog/integrations-core/pull/10812).
* Add profile metadata for Cisco Catalyst and 3850. See [#10767](https://github.com/DataDog/integrations-core/pull/10767).
* Add mac address as tag for meraki-cloud-controller  profile. See [#10779](https://github.com/DataDog/integrations-core/pull/10779).
* Add profile metadata for f5. See [#10667](https://github.com/DataDog/integrations-core/pull/10667).
* Add profile metadata for device and interface. See [#10666](https://github.com/DataDog/integrations-core/pull/10666).

***Fixed***: 

* Fix more SNMP illegal tabs. See [#11063](https://github.com/DataDog/integrations-core/pull/11063).
* Fix SNMP illegal tab character. See [#11062](https://github.com/DataDog/integrations-core/pull/11062).
* Fix default value for instance level oid_batch_size. See [#11018](https://github.com/DataDog/integrations-core/pull/11018).
* Add .0 to juniper metadata OIDs. See [#11019](https://github.com/DataDog/integrations-core/pull/11019).
* Fix netapp profile metrics. See [#10981](https://github.com/DataDog/integrations-core/pull/10981).
* Update auth and priv protocols. See [#10866](https://github.com/DataDog/integrations-core/pull/10866).


## 5.4.2 / 2021-10-07 / Agent 7.32.0

***Fixed***: 

* Hide collect_device_metadata by default. See [#10349](https://github.com/DataDog/integrations-core/pull/10349).


## 5.4.1 / 2021-10-06

***Fixed***: 

* Remove python only mention from check discovery props. See [#10352](https://github.com/DataDog/integrations-core/pull/10352).


## 5.4.0 / 2021-10-04

***Added***: 

* Update dependencies. See [#10258](https://github.com/DataDog/integrations-core/pull/10258).
* Add autodiscovery integration configs. See [#10079](https://github.com/DataDog/integrations-core/pull/10079).
* Add autodiscovery_subnet tag to discovered_devices_count metric. See [#10072](https://github.com/DataDog/integrations-core/pull/10072).

***Fixed***: 

* Better naming for testing environments. See [#10070](https://github.com/DataDog/integrations-core/pull/10070).
* Bump base package requirement. See [#10078](https://github.com/DataDog/integrations-core/pull/10078).


## 5.3.0 / 2021-08-22 / Agent 7.31.0

***Added***: 

* Add `ifNumber` to `_generic-if.yaml`. See [#9875](https://github.com/DataDog/integrations-core/pull/9875).
* Refactor profile validators. See [#9741](https://github.com/DataDog/integrations-core/pull/9741).

***Fixed***: 

* Enclose community string using single quote. See [#9742](https://github.com/DataDog/integrations-core/pull/9742).
* Test string float value in e2e. See [#9689](https://github.com/DataDog/integrations-core/pull/9689).


## 5.2.0 / 2021-05-28 / Agent 7.29.0

***Added***: 

* Add collect device metadata config. See [#9393](https://github.com/DataDog/integrations-core/pull/9393).
* Add rate type to error and discard counters. See [#9218](https://github.com/DataDog/integrations-core/pull/9218). Thanks [loganmc10](https://github.com/loganmc10).

***Fixed***: 

* Improve snmp example config. See [#9417](https://github.com/DataDog/integrations-core/pull/9417).
* Revert "Add collect device metadata config". See [#9439](https://github.com/DataDog/integrations-core/pull/9439).
* Fix mypy lint issue. See [#9288](https://github.com/DataDog/integrations-core/pull/9288).
* Update conf.yaml.example - wrong file name. See [#7704](https://github.com/DataDog/integrations-core/pull/7704).


## 5.1.0 / 2021-04-19 / Agent 7.28.0

***Added***: 

* Add doc for instance batch size config. See [#9109](https://github.com/DataDog/integrations-core/pull/9109).
* Add python loader tag to telemetry metrics. See [#9038](https://github.com/DataDog/integrations-core/pull/9038).
* [snmp] add metrics and tags to dell-rac profile. See [#8812](https://github.com/DataDog/integrations-core/pull/8812).


## 5.0.1 / 2021-03-10 / Agent 7.27.0

***Fixed***: 

* Fix snmp get bulk log. See [#8803](https://github.com/DataDog/integrations-core/pull/8803).


## 5.0.0 / 2021-03-07

***Changed***: 

* Move SNMP auto_conf.yaml to agent repo. See [#8709](https://github.com/DataDog/integrations-core/pull/8709).

***Added***: 

* Add BGP metrics to Juniper SRX Profile. See [#8771](https://github.com/DataDog/integrations-core/pull/8771).
* Support for additional Juniper devices. See [#8749](https://github.com/DataDog/integrations-core/pull/8749).

***Fixed***: 

* Fix Juniper EX sysObjectIds . See [#8728](https://github.com/DataDog/integrations-core/pull/8728).
* Better tests for generic_host_resources. See [#8266](https://github.com/DataDog/integrations-core/pull/8266).
* Add extract_value_pattern  to log on failure to submit metric. See [#8693](https://github.com/DataDog/integrations-core/pull/8693).
* 🐛  [snmp] use OIDPrinter to debug oids from bulks. See [#8688](https://github.com/DataDog/integrations-core/pull/8688).
* Fix oids not increasing link. See [#8655](https://github.com/DataDog/integrations-core/pull/8655).


## 4.1.0 / 2021-02-16

***Added***: 

* Add extract value feature. See [#8622](https://github.com/DataDog/integrations-core/pull/8622).
* Add SNMP check duration, interval, metrics count. See [#8211](https://github.com/DataDog/integrations-core/pull/8211).

***Fixed***: 

* Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).


## 4.0.0 / 2021-01-25 / Agent 7.26.0

***Changed***: 

* Add missing metrics to hp-ilo4 profile. See [#8220](https://github.com/DataDog/integrations-core/pull/8220).

***Added***: 

* Snmp Juniper profiles for EX (switches), MX (routers) and SRX (firewalls) series. See [#8206](https://github.com/DataDog/integrations-core/pull/8206).

***Fixed***: 

* Use mibless syntax for _generic-host-resources.yaml. See [#8305](https://github.com/DataDog/integrations-core/pull/8305).


## 3.10.0 / 2020-12-07 / Agent 7.25.0

***Added***: 

* Add snmp interface bandwidth usage metric. See [#8093](https://github.com/DataDog/integrations-core/pull/8093).
* Add interface alias (ifAlias) as a tag to interface metrics. See [#8018](https://github.com/DataDog/integrations-core/pull/8018). Thanks [loganmc10](https://github.com/loganmc10).
* Add generic Cisco ASA profile. See [#7971](https://github.com/DataDog/integrations-core/pull/7971).

***Fixed***: 

* Use MIB less syntax in example and link to profile format doc. See [#8073](https://github.com/DataDog/integrations-core/pull/8073).
* Add back cisco-asa-5525.yaml. See [#8041](https://github.com/DataDog/integrations-core/pull/8041).
* Improve symbol metric example. See [#8071](https://github.com/DataDog/integrations-core/pull/8071).
* Add deprecation notice for metric[].name syntax. See [#8070](https://github.com/DataDog/integrations-core/pull/8070).
* Add device_index to idrac (AI-938). See [#7525](https://github.com/DataDog/integrations-core/pull/7525).


## 3.9.0 / 2020-10-31 / Agent 7.24.0

***Added***: 

* Add 'device vendor' tag to metrics. See [#7871](https://github.com/DataDog/integrations-core/pull/7871).
* Track fetch ID in debug logs. See [#7736](https://github.com/DataDog/integrations-core/pull/7736).
* Make refresh_oids_cache_interval available as init_config. See [#7821](https://github.com/DataDog/integrations-core/pull/7821).
* Support alternative Mac Address index. See [#7688](https://github.com/DataDog/integrations-core/pull/7688).

***Fixed***: 

* Adding tag ciscoEnvMonSupplyStatusDescr to disambiguate metric. See [#7782](https://github.com/DataDog/integrations-core/pull/7782).


## 3.8.0 / 2020-09-04 / Agent 7.23.0

***Added***: 

* Add `index_transform` to support tagging using another table with different indexes. See [#7489](https://github.com/DataDog/integrations-core/pull/7489).

***Fixed***: 

* Validate SNMP profile hierarchy. See [#6798](https://github.com/DataDog/integrations-core/pull/6798).
* Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).


## 3.7.1 / 2020-08-12 / Agent 7.22.0

***Fixed***: 

* Fix apc ups profile. See [#7351](https://github.com/DataDog/integrations-core/pull/7351).
* Revert Fix wrong indentation of `table` key in column metric tags #7024. See [#7349](https://github.com/DataDog/integrations-core/pull/7349).


## 3.7.0 / 2020-08-03

***Added***: 

* Add OID caching. See [#7231](https://github.com/DataDog/integrations-core/pull/7231).

***Fixed***: 

* Refactor how OIDs are managed. See [#7230](https://github.com/DataDog/integrations-core/pull/7230).
* Sanitize OctetString. See [#7221](https://github.com/DataDog/integrations-core/pull/7221).
* Rename all_oids to scalar_oids. See [#7229](https://github.com/DataDog/integrations-core/pull/7229).
* Better logging for submit_metric. See [#7188](https://github.com/DataDog/integrations-core/pull/7188).


## 3.6.0 / 2020-07-24

***Added***: 

* Check tag for table metric. See [#6933](https://github.com/DataDog/integrations-core/pull/6933).
* Add new `flag_stream` type. See [#7072](https://github.com/DataDog/integrations-core/pull/7072).
* Add cisco catalyst profile. See [#6925](https://github.com/DataDog/integrations-core/pull/6925).
* Allow list of sysoids in profiles. See [#6936](https://github.com/DataDog/integrations-core/pull/6936).

***Fixed***: 

* Sanitize forced types values and cast to float. See [#7133](https://github.com/DataDog/integrations-core/pull/7133).
* Add `.0` to scalar oids. See [#7105](https://github.com/DataDog/integrations-core/pull/7105).
* Use OID instead of MIB for sysName. See [#7104](https://github.com/DataDog/integrations-core/pull/7104).
* Submit additional rate metrics in fortigate profile. See [#7058](https://github.com/DataDog/integrations-core/pull/7058).


## 3.5.3 / 2020-07-01 / Agent 7.21.0

***Fixed***: 

* Fix autodiscovery_subnet var in auto_conf.yaml. See [#7029](https://github.com/DataDog/integrations-core/pull/7029).


## 3.5.2 / 2020-06-30

***Fixed***: 

* Fix tag names for cisco asa profile. See [#7027](https://github.com/DataDog/integrations-core/pull/7027).


## 3.5.1 / 2020-06-30

***Fixed***: 

* Fix wrong indentation of `table` key in column metric tags. See [#7024](https://github.com/DataDog/integrations-core/pull/7024).


## 3.5.0 / 2020-06-29

***Added***: 

* Add regex match support for Tables. See [#6951](https://github.com/DataDog/integrations-core/pull/6951).
* Add snmp.devices_monitored metric. See [#6941](https://github.com/DataDog/integrations-core/pull/6941).
* Add IF-MIB metrics to the Meraki profile. See [#6905](https://github.com/DataDog/integrations-core/pull/6905).
* Add RTT metrics. See [#6872](https://github.com/DataDog/integrations-core/pull/6872).

***Fixed***: 

* Clean up of unused extends in meraki cloud profile. See [#6981](https://github.com/DataDog/integrations-core/pull/6981).
* [Refactor] Add device abstraction. See [#6953](https://github.com/DataDog/integrations-core/pull/6953).
* [Refactor] Clean up batching implementation. See [#6952](https://github.com/DataDog/integrations-core/pull/6952).
* Add index tagging to cfwConnectionStatValue. See [#6897](https://github.com/DataDog/integrations-core/pull/6897).


## 3.4.0 / 2020-06-11

***Added***: 

* Add NetApp profile. See [#6841](https://github.com/DataDog/integrations-core/pull/6841).

***Fixed***: 

* Fix `instance_number` tag on Cisco voice router metrics. See [#6867](https://github.com/DataDog/integrations-core/pull/6867).


## 3.3.0 / 2020-06-10

***Added***: 

* Add Fortinet FortiGate profile. See [#6504](https://github.com/DataDog/integrations-core/pull/6504). Thanks [lindseyferretti](https://github.com/lindseyferretti).
* Reuse MIB builder objects per SNMP engine. See [#6716](https://github.com/DataDog/integrations-core/pull/6716).
* Add HP health profile mixin. See [#6757](https://github.com/DataDog/integrations-core/pull/6757).
* Add routing metrics to additional profiles. See [#6764](https://github.com/DataDog/integrations-core/pull/6764).
* Add router metrics to cisco voice base profile. See [#6737](https://github.com/DataDog/integrations-core/pull/6737).

***Fixed***: 

* Fix gauge metrics wrongly submitted as rates in CISCO voice profile. See [#6794](https://github.com/DataDog/integrations-core/pull/6794).
* Push received metrics on partial failure. See [#6814](https://github.com/DataDog/integrations-core/pull/6814).
* Flatten Cisco profiles hierarchy. See [#6792](https://github.com/DataDog/integrations-core/pull/6792).
* Add missing tags to profiles tables. See [#6765](https://github.com/DataDog/integrations-core/pull/6765).
* Fix name KeyError. See [#6788](https://github.com/DataDog/integrations-core/pull/6788).
* Properly handle potential embedded null characters. See [#6640](https://github.com/DataDog/integrations-core/pull/6640).
* Remove iDRAC/poweredge profile inheritance. See [#6754](https://github.com/DataDog/integrations-core/pull/6754).
* Make profiles compatible with previous parsing. See [#6750](https://github.com/DataDog/integrations-core/pull/6750).


## 3.2.2 / 2020-05-21 / Agent 7.20.0

***Fixed***: 

* Fix error handling in getnext. See [#6701](https://github.com/DataDog/integrations-core/pull/6701).


## 3.2.1 / 2020-05-19

***Fixed***: 

* Add missing auto_conf. See [#6687](https://github.com/DataDog/integrations-core/pull/6687).


## 3.2.0 / 2020-05-17

***Added***: 

* Add diskStatus tag to Isilon profile. See [#6660](https://github.com/DataDog/integrations-core/pull/6660).
* Add BPG metrics to more profiles. See [#6655](https://github.com/DataDog/integrations-core/pull/6655).
* Add voice metrics and profiles. See [#6629](https://github.com/DataDog/integrations-core/pull/6629).


## 3.1.0 / 2020-05-14

***Added***: 

* Add `chatsworth` legacy metrics. See [#6624](https://github.com/DataDog/integrations-core/pull/6624).
* Add ifHighSpeed. See [#6602](https://github.com/DataDog/integrations-core/pull/6602).
* Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* Improve autodiscovery support. See [#6526](https://github.com/DataDog/integrations-core/pull/6526).

***Fixed***: 

* Exit discovery thread when check is gc-ed. See [#6484](https://github.com/DataDog/integrations-core/pull/6484).
* Don't use ifDescr for metric tagging. See [#6601](https://github.com/DataDog/integrations-core/pull/6601).
* Optimize away useless GET calls. See [#6456](https://github.com/DataDog/integrations-core/pull/6456).


## 3.0.0 / 2020-05-04

***Changed***: 

* Throw error if two profiles have the same sysObjectID. See [#6501](https://github.com/DataDog/integrations-core/pull/6501).

***Added***: 

* Add base BGP4 and Cisco-CSR1000v profiles. See [#6315](https://github.com/DataDog/integrations-core/pull/6315).
* Collect OSPF routing metrics. See [#6554](https://github.com/DataDog/integrations-core/pull/6554).
* Add F5 Big IP local traffic management (LTM) metrics. See [#5963](https://github.com/DataDog/integrations-core/pull/5963).
* Add more HP metrics. See [#6542](https://github.com/DataDog/integrations-core/pull/6542).
* Add more idrac/dell metrics. See [#6540](https://github.com/DataDog/integrations-core/pull/6540).
* Add additional Cisco metrics. See [#6539](https://github.com/DataDog/integrations-core/pull/6539).
* Add more metrics to Palo Alto profile. See [#6541](https://github.com/DataDog/integrations-core/pull/6541).
* Add upsOutletGroupStatusGroupState metric to APC UPS profile. See [#6555](https://github.com/DataDog/integrations-core/pull/6555).
* Add ifspeed metric to interface profile. See [#6499](https://github.com/DataDog/integrations-core/pull/6499).
* Add Isilon profile. See [#6518](https://github.com/DataDog/integrations-core/pull/6518).
* Add APC UPS profile. See [#6505](https://github.com/DataDog/integrations-core/pull/6505).
* Add env metric to cisco base profile. See [#6517](https://github.com/DataDog/integrations-core/pull/6517).
* Submit throughput as a rate. See [#6384](https://github.com/DataDog/integrations-core/pull/6384).
* Add more Cisco ASA metrics. See [#6335](https://github.com/DataDog/integrations-core/pull/6335).
* Add MIB resolution to `OID` model. See [#6242](https://github.com/DataDog/integrations-core/pull/6242).

***Fixed***: 

* Change default timeout to 5. See [#6546](https://github.com/DataDog/integrations-core/pull/6546).
* Remove empty values in config. See [#6455](https://github.com/DataDog/integrations-core/pull/6455).
* Use `OID` model in `OIDResolver`. See [#6469](https://github.com/DataDog/integrations-core/pull/6469).
* Isolate parsing logic into a dedicated sub-package. See [#6398](https://github.com/DataDog/integrations-core/pull/6398).
* Isolate PySNMP inspection hacks. See [#6461](https://github.com/DataDog/integrations-core/pull/6461).
* Drop outdated `warning` parameter in `parse_metrics`. See [#6412](https://github.com/DataDog/integrations-core/pull/6412).
* Fix debug output. See [#6400](https://github.com/DataDog/integrations-core/pull/6400).
* Check types on all modules. See [#6392](https://github.com/DataDog/integrations-core/pull/6392).
* Fix misleading `metric_tags` naming on `ParsedMetric`. See [#6387](https://github.com/DataDog/integrations-core/pull/6387).


## 2.6.1 / 2020-04-04 / Agent 7.19.0

***Fixed***: 

* Small profiles cleanups. See [#6233](https://github.com/DataDog/integrations-core/pull/6233).
* Remove duplicated idrac metrics from poweredge profile. See [#6232](https://github.com/DataDog/integrations-core/pull/6232).
* Only load installed profiles once. See [#6231](https://github.com/DataDog/integrations-core/pull/6231).
* Fix tag matching documentation. See [#6226](https://github.com/DataDog/integrations-core/pull/6226).


## 2.6.0 / 2020-03-24

***Added***: 

* Support regular expressions in dynamic tags. See [#6096](https://github.com/DataDog/integrations-core/pull/6096).
* Aruba, Arista and PDU profiles. See [#6002](https://github.com/DataDog/integrations-core/pull/6002).
* Load all profiles by default. See [#6051](https://github.com/DataDog/integrations-core/pull/6051).
* Add checkpoint firewall profile. See [#6021](https://github.com/DataDog/integrations-core/pull/6021).
* Add types to compat module. See [#6029](https://github.com/DataDog/integrations-core/pull/6029).
* Refactor and add types to `OIDResolver`. See [#6017](https://github.com/DataDog/integrations-core/pull/6017).
* Add `OID` helper class. See [#6000](https://github.com/DataDog/integrations-core/pull/6000).
* Add Cisco ASA 5525 profile and refactor cisco base profile. See [#5958](https://github.com/DataDog/integrations-core/pull/5958).
* Move PySNMP imports to a dedicated module. See [#5990](https://github.com/DataDog/integrations-core/pull/5990).
* Add Palo Alto and generic host resources SNMP profiles. See [#5914](https://github.com/DataDog/integrations-core/pull/5914).

***Fixed***: 

* Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* Implement `str()` for `OID` instances. See [#6046](https://github.com/DataDog/integrations-core/pull/6046).
* Move metric types to new module. See [#6044](https://github.com/DataDog/integrations-core/pull/6044).
* Isolate logic for converting SNMP values to metrics. See [#6031](https://github.com/DataDog/integrations-core/pull/6031).
* Move PySNMP imports to a separate `pysnmp_types` module. See [#6013](https://github.com/DataDog/integrations-core/pull/6013).
* Drop unused log argument on InstanceConfig. See [#6007](https://github.com/DataDog/integrations-core/pull/6007).
* Add OIDs to router profiles. See [#5991](https://github.com/DataDog/integrations-core/pull/5991).
* Validate and cast `discovery_interval` to a number. See [#5887](https://github.com/DataDog/integrations-core/pull/5887).


## 2.5.0 / 2020-02-27 / Agent 7.18.0

***Added***: 

* Query discovered devices in threads. See [#5462](https://github.com/DataDog/integrations-core/pull/5462).

***Fixed***: 

* Fix issue with tags leaking between discovered instances. See [#5899](https://github.com/DataDog/integrations-core/pull/5899).


## 2.4.1 / 2020-02-25

***Fixed***: 

* Handle case when servers report two values for entries in `metric_tags`. See [#5853](https://github.com/DataDog/integrations-core/pull/5853).


## 2.4.0 / 2020-02-22

***Added***: 

* Add extension mechanism for SNMP profiles. See [#5821](https://github.com/DataDog/integrations-core/pull/5821).
* Add snmp_host tag by default to profiles. See [#5812](https://github.com/DataDog/integrations-core/pull/5812).
* Add hpe proliant profile. See [#5724](https://github.com/DataDog/integrations-core/pull/5724).
* Tag metrics by profile. See [#5787](https://github.com/DataDog/integrations-core/pull/5787).
* Add `ignored_ip_addresses` option to ignore specific IP addresses when scanning a network.. See [#5785](https://github.com/DataDog/integrations-core/pull/5785).
* Add basic types to SNMP integration. See [#5782](https://github.com/DataDog/integrations-core/pull/5782).
* Use all matching profiles instead of only the most specific one. See [#5768](https://github.com/DataDog/integrations-core/pull/5768).
* Add a new metric_tags configuration. See [#5765](https://github.com/DataDog/integrations-core/pull/5765).
* Add profile for HP iLO4 devices. See [#5637](https://github.com/DataDog/integrations-core/pull/5637).
* Fetch sysUpTimeInstance automatically. See [#5752](https://github.com/DataDog/integrations-core/pull/5752).
* Add Dell Poweredge profile. See [#5723](https://github.com/DataDog/integrations-core/pull/5723).

***Fixed***: 

* Switch back to most specific profile matching. See [#5813](https://github.com/DataDog/integrations-core/pull/5813).


## 2.3.2 / 2020-01-15 / Agent 7.17.0

***Fixed***: 

* Tweak behavior related to discovery. See [#5466](https://github.com/DataDog/integrations-core/pull/5466).


## 2.3.1 / 2020-01-13

***Fixed***: 

* Fix usage of old OID list attributes on InstanceConfig. See [#5412](https://github.com/DataDog/integrations-core/pull/5412).


## 2.3.0 / 2020-01-07

***Added***: 

* Remove MIB requirement in profiles. See [#5397](https://github.com/DataDog/integrations-core/pull/5397).
* Implement table browsing with OIDs. See [#5368](https://github.com/DataDog/integrations-core/pull/5368).
* Update license years. See [#5384](https://github.com/DataDog/integrations-core/pull/5384).
* Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* Add a profile for Meraki cloud devices. See [#5215](https://github.com/DataDog/integrations-core/pull/5215).


## 2.2.0 / 2020-01-02

***Added***: 

* Add profile for Cisco Nexus switches. See [#5363](https://github.com/DataDog/integrations-core/pull/5363).
* Add profile for Intel IDRAC devices. See [#5227](https://github.com/DataDog/integrations-core/pull/5227).

***Fixed***: 

* Fetch table OIDs per table. See [#5192](https://github.com/DataDog/integrations-core/pull/5192).


## 2.1.0 / 2019-11-27 / Agent 7.16.0

***Added***: 

* Add Cisco 3850 profile. See [#5090](https://github.com/DataDog/integrations-core/pull/5090).

***Fixed***: 

* Disable MIB autofetch. See [#5094](https://github.com/DataDog/integrations-core/pull/5094).


## 2.0.1 / 2019-11-21

***Fixed***: 

* Handle total_time_to_temporal_percent missing. See [#5055](https://github.com/DataDog/integrations-core/pull/5055).


## 2.0.0 / 2019-11-15

***Changed***: 

* Modify profile layout. See [#4997](https://github.com/DataDog/integrations-core/pull/4997).

***Added***: 

* Add interface statuses to profiles. See [#5004](https://github.com/DataDog/integrations-core/pull/5004).
* Ignore metrics that are not retrieved. See [#5003](https://github.com/DataDog/integrations-core/pull/5003).
* Match profile with sysobject_id prefix. See [#4990](https://github.com/DataDog/integrations-core/pull/4990).
* Count the number of discovered devices. See [#4978](https://github.com/DataDog/integrations-core/pull/4978).
* Generic network router profile. See [#4937](https://github.com/DataDog/integrations-core/pull/4937).
* Allow tagging through different MIBs. See [#4853](https://github.com/DataDog/integrations-core/pull/4853).


## 1.14.1 / 2019-10-16 / Agent 6.15.0

***Fixed***: 

* Fix allowed host failure retry logic. See [#4782](https://github.com/DataDog/integrations-core/pull/4782).


## 1.14.0 / 2019-10-14

***Added***: 

* Store discovered hosts. See [#4712](https://github.com/DataDog/integrations-core/pull/4712).


## 1.13.0 / 2019-10-11

***Added***: 

* Automatically fetch MIBs that we don't know about. See [#4732](https://github.com/DataDog/integrations-core/pull/4732).


## 1.12.0 / 2019-10-10

***Added***: 

* Add profile for F5 BIG-IP devices. See [#4674](https://github.com/DataDog/integrations-core/pull/4674).


## 1.11.0 / 2019-09-19

***Added***: 

* Use bulk call when possible. See [#4530](https://github.com/DataDog/integrations-core/pull/4530).
* Remove failing discovered hosts. See [#4526](https://github.com/DataDog/integrations-core/pull/4526).
* Basic discovery mechanism and test. See [#4511](https://github.com/DataDog/integrations-core/pull/4511).
* Allow autoconfiguration of instances by sysObjectId. See [#4391](https://github.com/DataDog/integrations-core/pull/4391).

***Fixed***: 

* Handle bytes in network_address. See [#4577](https://github.com/DataDog/integrations-core/pull/4577).


## 1.10.0 / 2019-08-24 / Agent 6.14.0

***Added***: 

* Support referencing metrics by profile. See [#4329](https://github.com/DataDog/integrations-core/pull/4329).
* Upgrade pyasn1. See [#4289](https://github.com/DataDog/integrations-core/pull/4289).
* Reimplement config load logic. See [#4160](https://github.com/DataDog/integrations-core/pull/4160).


## 1.9.0 / 2019-07-13 / Agent 6.13.0

***Added***: 

* Add support for string types. See [#4087](https://github.com/DataDog/integrations-core/pull/4087).


## 1.8.0 / 2019-07-04

***Added***: 

* Match OIDs with leading dots. See [#3854](https://github.com/DataDog/integrations-core/pull/3854).


## 1.7.0 / 2019-05-14 / Agent 6.12.0

***Added***: 

* Adhere to code style. See [#3565](https://github.com/DataDog/integrations-core/pull/3565).


## 1.6.0 / 2019-03-29 / Agent 6.11.0

***Added***: 

* Add metrics config globally. See [#3230](https://github.com/DataDog/integrations-core/pull/3230).


## 1.5.0 / 2019-02-18 / Agent 6.10.0

***Added***: 

* Improve performance by querying only necessary columns from a table. See [#3059](https://github.com/DataDog/integrations-core/pull/3059).
* Support Python 3. See [#3016](https://github.com/DataDog/integrations-core/pull/3016).

***Fixed***: 

* Log the correct information about snmpnext result. See [#3021](https://github.com/DataDog/integrations-core/pull/3021).


## 1.4.2 / 2018-10-12 / Agent 6.6.0

***Fixed***: 

* Fix `enforce_mib_constraints` parameter having no effect.. See [#2340](https://github.com/DataDog/integrations-core/pull/2340).


## 1.4.1 / 2018-09-04 / Agent 6.5.0

***Fixed***: 

* Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).


## 1.4.0 / 2018-05-11

***Added***: 

* Enhance error handling when metrics aren't defined or device cannot be reached. See [#1406](https://github.com/DataDog/integrations-core/issues/1406)


## 1.3.1 / 2018-02-13

***Fixed***: 

* Fix warning service check reporting. See [#1041](https://github.com/DataDog/integrations-core/issues/1041)


## 1.3.0 / 2017-10-10

***Added***: 

* Add support for SNMPv3 Contexts. See [#723](https://github.com/DataDog/integrations-core/issues/723)


## 1.2.0 / 2017-07-18

***Changed***: 

* Drop dependency on pycrypto. See [#426](https://github.com/DataDog/integrations-core/issues/426)


## 1.1.0 / 2017-04-24

***Added***: 

* Add individual metric tagging to OID and MIB Non-tabular data. See [#248](https://github.com/DataDog/integrations-core/issues/248)


## 1.0.0 / 2017-03-22

***Added***: 

* adds snmp integration.

