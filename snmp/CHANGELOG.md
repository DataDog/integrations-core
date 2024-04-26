# CHANGELOG - snmp

<!-- towncrier release notes start -->

## 7.3.0 / 2024-04-26

***Added***:

* [SNMP] Add device_hostname tag ([#17433](https://github.com/DataDog/integrations-core/pull/17433))

## 7.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Bump `pycryptodomex` version to 3.19.1 ([#16560](https://github.com/DataDog/integrations-core/pull/16560))
* Add `device_type` to OOTB profiles ([#16564](https://github.com/DataDog/integrations-core/pull/16564))
* [SNMP] Add general IPsec profile for Cisco devices ([#16597](https://github.com/DataDog/integrations-core/pull/16597))
* [SNMP] Add abstract profiles for VoIP ([#16711](https://github.com/DataDog/integrations-core/pull/16711))
* Update dependencies ([#16788](https://github.com/DataDog/integrations-core/pull/16788))
* Add ping documentation ([#16881](https://github.com/DataDog/integrations-core/pull/16881))

## 7.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Bump the base check version to 32.6.0 ([#16323](https://github.com/DataDog/integrations-core/pull/16323))

## 7.0.1 / 2023-10-26 / Agent 7.50.0

***Fixed***:

* Update default profiles column to symbol ([#15998](https://github.com/DataDog/integrations-core/pull/15998))
* Deprecate init_config.profiles ([#16068](https://github.com/DataDog/integrations-core/pull/16068))

## 7.0.0 / 2023-09-29 / Agent 7.49.0

***Changed***:

* Add `assert_all_profile_metrics_and_tags_covered` and fix mappings in profiles ([#15720](https://github.com/DataDog/integrations-core/pull/15720))
* Refactor arista profiles extends ([#15767](https://github.com/DataDog/integrations-core/pull/15767))
* Fix mappings in _dell-rac & dell-poweredge ([#15827](https://github.com/DataDog/integrations-core/pull/15827))

***Fixed***:

* Remove duplicate mem tag in tp-link.yaml ([#15665](https://github.com/DataDog/integrations-core/pull/15665))
* Remove unsupported metric in riverbed-interceptor.yaml ([#15678](https://github.com/DataDog/integrations-core/pull/15678))
* Delete unnecessary extend for ubiquiti profiles ([#15643](https://github.com/DataDog/integrations-core/pull/15643))
* Add comment for fanSpeedSensorStatus ([#15804](https://github.com/DataDog/integrations-core/pull/15804))
* Update Cisco model metadata regex ([#15908](https://github.com/DataDog/integrations-core/pull/15908))
* Update generic-ospf profile mappings ([#15764](https://github.com/DataDog/integrations-core/pull/15764))

## 6.2.3 / 2023-09-13 / Agent 7.48.0

***Fixed***:

* Update mappings in SNMP profiles ([#15826](https://github.com/DataDog/integrations-core/pull/15826))

## 6.2.2 / 2023-09-12

***Fixed***:

* Fix mapping for apc-pdu ([#15765](https://github.com/DataDog/integrations-core/pull/15765))
* Fixes for SNMP Profiles introduced in 7.48 ([#15800](https://github.com/DataDog/integrations-core/pull/15800))

## 6.2.1 / 2023-09-05

***Fixed***:

* Fix SNMP profiles metric tags mappings using MIBs ([#15668](https://github.com/DataDog/integrations-core/pull/15668))

## 6.2.0 / 2023-08-18

***Added***:

* Add hardware metrics for Cisco (non-categorical) ([#15551](https://github.com/DataDog/integrations-core/pull/15551))
* Add hardware metrics for Dell (non-categorical) ([#15567](https://github.com/DataDog/integrations-core/pull/15567))
* Add hardware metrics for F5 (non-categorical) ([#15568](https://github.com/DataDog/integrations-core/pull/15568))
* Add hardware metrics for Fortinet (non-categorical) ([#15553](https://github.com/DataDog/integrations-core/pull/15553))
* Add hardware metrics for Meraki ([#15542](https://github.com/DataDog/integrations-core/pull/15542))
* Add citrix-netscaler-sdx profile ([#15482](https://github.com/DataDog/integrations-core/pull/15482))

## 6.1.0 / 2023-08-10

***Added***:

* Add netgear-switch ([#15337](https://github.com/DataDog/integrations-core/pull/15337))
* Add hardware metrics Checkpoint Firewall (fan) ([#15514](https://github.com/DataDog/integrations-core/pull/15514))
* Add hardware metrics for HP (power supplies) [FIX] ([#15491](https://github.com/DataDog/integrations-core/pull/15491))
* Add profile netgear-readynas ([#15322](https://github.com/DataDog/integrations-core/pull/15322))
* Add hardware metrics for Dell (power supplies) ([#15456](https://github.com/DataDog/integrations-core/pull/15456))
* Add hardware metrics for cisco (fan) ([#15507](https://github.com/DataDog/integrations-core/pull/15507))
* Add hardware metrics for Chatsworth (power supplies)  ([#15471](https://github.com/DataDog/integrations-core/pull/15471))
* Add hardware metrics for Cisco (power supplies) ([#15480](https://github.com/DataDog/integrations-core/pull/15480))
* Add profile dell-emc-data-domain ([#15436](https://github.com/DataDog/integrations-core/pull/15436))
* Add hardware metrics for HP (power supplies) ([#15467](https://github.com/DataDog/integrations-core/pull/15467))
* [SNMP] Add profile for Avaya Nortel ethernet routing switch ([#15472](https://github.com/DataDog/integrations-core/pull/15472))
* [NDM] Add bgpPeerRemoteAs as tag ([#15225](https://github.com/DataDog/integrations-core/pull/15225))
* Add dlink-dgs-switch profile ([#15461](https://github.com/DataDog/integrations-core/pull/15461))
* Add peplink profile ([#15464](https://github.com/DataDog/integrations-core/pull/15464))
* [SNMP] Add profile for Avaya Media gateway ([#15469](https://github.com/DataDog/integrations-core/pull/15469))
* [SNMP] Add profile for Avaya Cajun switch ([#15466](https://github.com/DataDog/integrations-core/pull/15466))
* Add profile for pf-sense ([#15468](https://github.com/DataDog/integrations-core/pull/15468))
* Add profiles for netgear &  netgear-access-point ([#15306](https://github.com/DataDog/integrations-core/pull/15306))
* Investigate hierarchy for dell profiles ([#15446](https://github.com/DataDog/integrations-core/pull/15446))
* Add profile omron-cj-ethernet-ip ([#15465](https://github.com/DataDog/integrations-core/pull/15465))
* [SNMP] Add profile for Avocent ACS ([#15460](https://github.com/DataDog/integrations-core/pull/15460))
* [NDM] Add cyberpower-pdu profile ([#15158](https://github.com/DataDog/integrations-core/pull/15158))
* Add profile opengear-infrastructure-manager ([#15455](https://github.com/DataDog/integrations-core/pull/15455))
* [NDM] Add barracuda-cloudgen profile ([#15153](https://github.com/DataDog/integrations-core/pull/15153))
* Add profile opengear-console-manager ([#15451](https://github.com/DataDog/integrations-core/pull/15451))
* [SNMP] Add profile for Eaton EPDU ([#15458](https://github.com/DataDog/integrations-core/pull/15458))
* Add ubiquiti-unifi-security-gateway ([#15433](https://github.com/DataDog/integrations-core/pull/15433))
* [SNMP] Add profile for Palo-Alto Cloudgenix ([#15432](https://github.com/DataDog/integrations-core/pull/15432))
* Add profile dell-sonicwall ([#15426](https://github.com/DataDog/integrations-core/pull/15426))
* [SNMP] Add profile for Western-Digital Mycloud EX2 Ultra ([#15444](https://github.com/DataDog/integrations-core/pull/15444))
* [NDM] Add citrix-netscaler profile ([#15349](https://github.com/DataDog/integrations-core/pull/15349))
* [SNMP] Add profile for Dialogic media gateway ([#15445](https://github.com/DataDog/integrations-core/pull/15445))
* Add profile dell-powerconnect ([#15423](https://github.com/DataDog/integrations-core/pull/15423))
* Add profile dell-os10 ([#15414](https://github.com/DataDog/integrations-core/pull/15414))
* [NDM] add cradlepoint profile ([#15419](https://github.com/DataDog/integrations-core/pull/15419))
* [SNMP] Add profile for VMWare ESX ([#15430](https://github.com/DataDog/integrations-core/pull/15430))
* Add profile dell-force10 ([#15424](https://github.com/DataDog/integrations-core/pull/15424))
* [SNMP] Add profile for HP MSA ([#15310](https://github.com/DataDog/integrations-core/pull/15310))
* [SNMP] Add profile for Vertiv Liebert AC ([#15415](https://github.com/DataDog/integrations-core/pull/15415))
* [SNMP] Add profile for Vertiv Watchdog ([#15412](https://github.com/DataDog/integrations-core/pull/15412))
* [SNMP] Add profile for NEC univerge ([#15403](https://github.com/DataDog/integrations-core/pull/15403))
* Add profile ubiquiti-unifi ([#15399](https://github.com/DataDog/integrations-core/pull/15399))
* Add profile ixsystems-truenas ([#15398](https://github.com/DataDog/integrations-core/pull/15398))
* Add profile tripplite-ups ([#15397](https://github.com/DataDog/integrations-core/pull/15397))
* Add profile tripplite-pdu ([#15396](https://github.com/DataDog/integrations-core/pull/15396))
* Add profile for zebra-printer ([#15385](https://github.com/DataDog/integrations-core/pull/15385))
* [SNMP] Add profile for Mikrotik routers ([#15388](https://github.com/DataDog/integrations-core/pull/15388))
* Add profile for zyxel-switch ([#15386](https://github.com/DataDog/integrations-core/pull/15386))
* Add profile for velocloud-edge ([#15382](https://github.com/DataDog/integrations-core/pull/15382))
* [SNMP] Add profile for IBM Lenovo servers ([#15377](https://github.com/DataDog/integrations-core/pull/15377))
* Add profile for servertech-pdu4 ([#15369](https://github.com/DataDog/integrations-core/pull/15369))
* Add profile infinera-coriant-groove ([#15374](https://github.com/DataDog/integrations-core/pull/15374))
* Add profile mcafee-web-gateway ([#15373](https://github.com/DataDog/integrations-core/pull/15373))
* [SNMP] Add profile for IBM datapower gateway ([#15371](https://github.com/DataDog/integrations-core/pull/15371))
* Add profile kyocera-printer ([#15370](https://github.com/DataDog/integrations-core/pull/15370))
* Add profile linksys ([#15372](https://github.com/DataDog/integrations-core/pull/15372))
* Add profile sophos-xgs-firewall ([#15368](https://github.com/DataDog/integrations-core/pull/15368))
* Add profile juniper-pulse-secure ([#15367](https://github.com/DataDog/integrations-core/pull/15367))
* Add profile infoblox-ipam ([#15354](https://github.com/DataDog/integrations-core/pull/15354))
* Add juniper-qfx.yaml ([#15366](https://github.com/DataDog/integrations-core/pull/15366))
* [SNMP] Add profile for Huawei access controllers ([#15358](https://github.com/DataDog/integrations-core/pull/15358))
* Add profile for synology-disk-station ([#15335](https://github.com/DataDog/integrations-core/pull/15335))
* Add profile for silverpeak-edgeconnect ([#15328](https://github.com/DataDog/integrations-core/pull/15328))
* [SNMP] Add profile for Huawei switches ([#15357](https://github.com/DataDog/integrations-core/pull/15357))
* [SNMP] Add profile for Huawei routers ([#15356](https://github.com/DataDog/integrations-core/pull/15356))
* [SNMP] Add profile for Huawei devices ([#15343](https://github.com/DataDog/integrations-core/pull/15343))
* [SNMP] Add profile for APC Netbotz ([#15136](https://github.com/DataDog/integrations-core/pull/15136))
* Add profile for tp-link ([#15339](https://github.com/DataDog/integrations-core/pull/15339))
* Add profile for servertech-pdu3 ([#15341](https://github.com/DataDog/integrations-core/pull/15341))
* [NDM] Add profile for avaya aura ms ([#15214](https://github.com/DataDog/integrations-core/pull/15214))
* Add profile for sinetica-eagle-i ([#15340](https://github.com/DataDog/integrations-core/pull/15340))
* Add profile for server-iron-switch ([#15329](https://github.com/DataDog/integrations-core/pull/15329))
* [SNMP] Add profile for HP Nimble ([#15312](https://github.com/DataDog/integrations-core/pull/15312))
* Add profile for ruckus-unleashed ([#15311](https://github.com/DataDog/integrations-core/pull/15311))
* Add profile for raritan-dominion ([#15326](https://github.com/DataDog/integrations-core/pull/15326))
* [SNMP] Add profile for HP Bladesystem enclosure ([#15248](https://github.com/DataDog/integrations-core/pull/15248))
* [SNMP] Add APC PDU profile ([#15135](https://github.com/DataDog/integrations-core/pull/15135))
* Add profile for riverbed-interceptor ([#15294](https://github.com/DataDog/integrations-core/pull/15294))
* Add profile for hp-icf-switch ([#15209](https://github.com/DataDog/integrations-core/pull/15209))
* Add profile for hp-h3c-switch ([#15207](https://github.com/DataDog/integrations-core/pull/15207))
* Add profile for riverbed-steelhead ([#15300](https://github.com/DataDog/integrations-core/pull/15300))
* Add profile for ruckus-wap ([#15309](https://github.com/DataDog/integrations-core/pull/15309))
* Add profile for Aruba WC ([#15128](https://github.com/DataDog/integrations-core/pull/15128))
* [SNMP] Add profile for Nasuni ([#15253](https://github.com/DataDog/integrations-core/pull/15253))
* Add interface_index to interface metrics ([#15274](https://github.com/DataDog/integrations-core/pull/15274))
* Add profile for gigamon ([#15195](https://github.com/DataDog/integrations-core/pull/15195))
* Add profile cisco-ucs ([#15265](https://github.com/DataDog/integrations-core/pull/15265))
* Add profile cisco-wan-optimizer ([#15270](https://github.com/DataDog/integrations-core/pull/15270))
* Add profile for ups ([#15205](https://github.com/DataDog/integrations-core/pull/15205))
* Add profile cisco-load-balancer ([#15210](https://github.com/DataDog/integrations-core/pull/15210))
* Add `hr_device_index` tag to `snmp.hrProcessorLoad` metric ([#15202](https://github.com/DataDog/integrations-core/pull/15202))
* Add profile cisco-ise ([#15193](https://github.com/DataDog/integrations-core/pull/15193))
* Add profile cisco-sb ([#15264](https://github.com/DataDog/integrations-core/pull/15264))

***Fixed***:

* Update forced_type to metric_type ([#15191](https://github.com/DataDog/integrations-core/pull/15191))
* Add abstract profile for cisco vendor to reduce duplication ([#15266](https://github.com/DataDog/integrations-core/pull/15266))
* Fix cisco-ise profile ([#15283](https://github.com/DataDog/integrations-core/pull/15283))

## 6.0.0 / 2023-07-10 / Agent 7.47.0

***Changed***:

* Rename vendor profiles to match vendor.yaml ([#15039](https://github.com/DataDog/integrations-core/pull/15039))
* Rename generic-router to generic-device ([#14723](https://github.com/DataDog/integrations-core/pull/14723))

***Added***:

* [NDM] Add audiocodes-mediant-sbc profile ([#15117](https://github.com/DataDog/integrations-core/pull/15117))
* Add profile for fortinet-fortiswitch ([#15192](https://github.com/DataDog/integrations-core/pull/15192))
* Add profile for Fireeye ([#15185](https://github.com/DataDog/integrations-core/pull/15185))
* Add profile for fortinet-appliance ([#15188](https://github.com/DataDog/integrations-core/pull/15188))
* Add arista-switch profile ([#15092](https://github.com/DataDog/integrations-core/pull/15092))
* Add profile cisco-ironport-email ([#15163](https://github.com/DataDog/integrations-core/pull/15163))
* Add profile cisco-firepower ([#15160](https://github.com/DataDog/integrations-core/pull/15160))
* Add profile for extreme-switching ([#15164](https://github.com/DataDog/integrations-core/pull/15164))
* Add profile cisco-access-point ([#15147](https://github.com/DataDog/integrations-core/pull/15147))
* [NDM] [SNMP] Update F5 BIGIP profile ([#15049](https://github.com/DataDog/integrations-core/pull/15049))
* Add profile for Aruba-cx-switch ([#15107](https://github.com/DataDog/integrations-core/pull/15107))
* Add aruba-clearpass profile ([#15088](https://github.com/DataDog/integrations-core/pull/15088))
* Add profile for Exagrid ([#15137](https://github.com/DataDog/integrations-core/pull/15137))
* Add profile cisco-firepower-asa ([#15157](https://github.com/DataDog/integrations-core/pull/15157))
* [SNMP] Add profile for alcatel-lucent omni access WLC ([#15101](https://github.com/DataDog/integrations-core/pull/15101))
* [SNMP] Add profile for alcatel-lucent ind ([#15095](https://github.com/DataDog/integrations-core/pull/15095))
* [NDM] Add bluecat-server profile ([#15125](https://github.com/DataDog/integrations-core/pull/15125))
* [SNMP] Add profile for alcatel-lucent ent ([#15094](https://github.com/DataDog/integrations-core/pull/15094))
* Add profile chrysalis-luna-hsm ([#15133](https://github.com/DataDog/integrations-core/pull/15133))
* [NDM] Add avtech-roomalert-3s ([#15076](https://github.com/DataDog/integrations-core/pull/15076))
* Add profile watchguard ([#15130](https://github.com/DataDog/integrations-core/pull/15130))
* [SNMP] Add profile for Anue ([#15123](https://github.com/DataDog/integrations-core/pull/15123))
* Add profile for aruba mobility controller ([#15109](https://github.com/DataDog/integrations-core/pull/15109))
* [NDM] Add avtech roomalert 3e profile ([#15075](https://github.com/DataDog/integrations-core/pull/15075))
* [NDM] Add avtech-roomalert-32s ([#15058](https://github.com/DataDog/integrations-core/pull/15058))
* [SNMP] Add profile for generic UPS ([#15068](https://github.com/DataDog/integrations-core/pull/15068))
* Add profile brother-net-printer ([#15102](https://github.com/DataDog/integrations-core/pull/15102))
* Add profile brocade-fc-switch ([#15065](https://github.com/DataDog/integrations-core/pull/15065))
* Update profile a10-thunder with metric_type ([#15086](https://github.com/DataDog/integrations-core/pull/15086))
* Add profile _generic-ucd.yaml ([#15046](https://github.com/DataDog/integrations-core/pull/15046))
* [NDM] Add profiles for Nvidia ([#15051](https://github.com/DataDog/integrations-core/pull/15051))
* Add profile a10-thunder ([#14712](https://github.com/DataDog/integrations-core/pull/14712))
* Add `_generic-lldp` profile ([#15061](https://github.com/DataDog/integrations-core/pull/15061))
* Add per vendor generic profiles ([#14721](https://github.com/DataDog/integrations-core/pull/14721))
* Add profile 3com-huawei ([#14694](https://github.com/DataDog/integrations-core/pull/14694))
* Update profiles with missing devices ([#14695](https://github.com/DataDog/integrations-core/pull/14695))
* Add profile for hp-ilo ([#14771](https://github.com/DataDog/integrations-core/pull/14771))
* Add User Profiles support ([#14752](https://github.com/DataDog/integrations-core/pull/14752))
* Add profile 3com ([#14693](https://github.com/DataDog/integrations-core/pull/14693))

***Fixed***:

* Update alcatel-lucent-ind with prefix  ([#15184](https://github.com/DataDog/integrations-core/pull/15184))
* Update alcatel-lucent-ent with prefix ([#15183](https://github.com/DataDog/integrations-core/pull/15183))
* Add roomalert prefix to avtech-roomalert-32s.yaml ([#15180](https://github.com/DataDog/integrations-core/pull/15180))
* Add roomalert3s prefix to avtech-roomalert-3s.yaml ([#15182](https://github.com/DataDog/integrations-core/pull/15182))
* Add `roomalert3e` prefix to avtech-roomalert-3e.yaml ([#15181](https://github.com/DataDog/integrations-core/pull/15181))
* Add missing metric_type and ucd prefix for _generic-ucd ([#15177](https://github.com/DataDog/integrations-core/pull/15177))
* Add prefixes to `nvidia-cumulus-linux-switch` ([#15176](https://github.com/DataDog/integrations-core/pull/15176))
* Update _generic-ups.yaml ([#15179](https://github.com/DataDog/integrations-core/pull/15179))
* Update a10-thunder axAppGlobalTotalCurrentConnections metric_type ([#15169](https://github.com/DataDog/integrations-core/pull/15169))
* Document _cisco-cpu-memory.yaml metrics ([#15149](https://github.com/DataDog/integrations-core/pull/15149))
* Update metadata.csv for 3com-huawei profile ([#15038](https://github.com/DataDog/integrations-core/pull/15038))
* Refactor hp-ilo profile vendor ([#14823](https://github.com/DataDog/integrations-core/pull/14823))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Remove rules from test_profile_hierarchy ([#14703](https://github.com/DataDog/integrations-core/pull/14703))

## 5.12.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* adds sysobjectids to cisco-catalyst profile ([#14452](https://github.com/DataDog/integrations-core/pull/14452))
* [SNMP] Enriched BGP profile ([#14399](https://github.com/DataDog/integrations-core/pull/14399))

***Fixed***:

* NDM: Fix memory metrics OIDs for cisco-nexus ([#14572](https://github.com/DataDog/integrations-core/pull/14572))
* Add .0 to hp scalar metrics ([#14558](https://github.com/DataDog/integrations-core/pull/14558))

## 5.11.0 / 2022-12-09 / Agent 7.42.0

***Added***:

* Add topology metadata e2e test (aos_lldp) ([#13373](https://github.com/DataDog/integrations-core/pull/13373))

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))
* Remove invalid 'service' field in snmp example config ([#13341](https://github.com/DataDog/integrations-core/pull/13341))

## 5.10.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Refactor tooling for getting the current env name ([#12939](https://github.com/DataDog/integrations-core/pull/12939))

***Fixed***:

* Add virtualdomain_index tag to fgFwPolStatsTable ([#12760](https://github.com/DataDog/integrations-core/pull/12760))

## 5.9.0 / 2022-08-05 / Agent 7.39.0

***Added***:

* Add metrics for VPN Tunnels ([#11977](https://github.com/DataDog/integrations-core/pull/11977)) Thanks [jalmeroth](https://github.com/jalmeroth).

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 5.8.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Add memory and cpu abstract metrics ([#11781](https://github.com/DataDog/integrations-core/pull/11781))

***Fixed***:

* Fix meraki profile mac address ([#11871](https://github.com/DataDog/integrations-core/pull/11871))
* Add format mac_address to profile interface metadata ([#11870](https://github.com/DataDog/integrations-core/pull/11870))
* Updating check documentation for timeout and retries ([#11848](https://github.com/DataDog/integrations-core/pull/11848))

## 5.7.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))
* Add `min_collection_interval` to snmp `init_config` ([#11543](https://github.com/DataDog/integrations-core/pull/11543))

## 5.6.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11432](https://github.com/DataDog/integrations-core/pull/11432))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 5.5.0 / 2022-01-08 / Agent 7.34.0

***Added***:

* Add `sysMultiHostCpuUsageRatio` to BIG-IP profile ([#10924](https://github.com/DataDog/integrations-core/pull/10924)) Thanks [kei6u](https://github.com/kei6u).
* Add profile metadata for Isilon ([#11022](https://github.com/DataDog/integrations-core/pull/11022))
* Add metadata to Dell iDRAC profile ([#11004](https://github.com/DataDog/integrations-core/pull/11004))
* Add profile metadata for fortinet-fortigate ([#11002](https://github.com/DataDog/integrations-core/pull/11002))
* Add profile metadata for checkpoint_firewall ([#10998](https://github.com/DataDog/integrations-core/pull/10998))
* Add profile metadata for netapp ([#10968](https://github.com/DataDog/integrations-core/pull/10968))
* Add metrics to apc_ups profile ([#10967](https://github.com/DataDog/integrations-core/pull/10967))
* Add profile metadata for palo alto ([#10956](https://github.com/DataDog/integrations-core/pull/10956))
* Add profile metadata for arista ([#10944](https://github.com/DataDog/integrations-core/pull/10944))
* Add profile metadata for aruba ([#10952](https://github.com/DataDog/integrations-core/pull/10952))
* Add profile metadata for Juniper ([#11005](https://github.com/DataDog/integrations-core/pull/11005))
* Add apc_ups profile metadata ([#10857](https://github.com/DataDog/integrations-core/pull/10857))
* Add metadata to HP profiles ([#10867](https://github.com/DataDog/integrations-core/pull/10867))
* Add location to _base.yaml ([#10822](https://github.com/DataDog/integrations-core/pull/10822))
* Add use_device_id_as_hostname config ([#10812](https://github.com/DataDog/integrations-core/pull/10812))
* Add profile metadata for Cisco Catalyst and 3850 ([#10767](https://github.com/DataDog/integrations-core/pull/10767))
* Add mac address as tag for meraki-cloud-controller  profile ([#10779](https://github.com/DataDog/integrations-core/pull/10779))
* Add profile metadata for f5 ([#10667](https://github.com/DataDog/integrations-core/pull/10667))
* Add profile metadata for device and interface ([#10666](https://github.com/DataDog/integrations-core/pull/10666))

***Fixed***:

* Fix more SNMP illegal tabs ([#11063](https://github.com/DataDog/integrations-core/pull/11063))
* Fix SNMP illegal tab character ([#11062](https://github.com/DataDog/integrations-core/pull/11062))
* Fix default value for instance level oid_batch_size ([#11018](https://github.com/DataDog/integrations-core/pull/11018))
* Add .0 to juniper metadata OIDs ([#11019](https://github.com/DataDog/integrations-core/pull/11019))
* Fix netapp profile metrics ([#10981](https://github.com/DataDog/integrations-core/pull/10981))
* Update auth and priv protocols ([#10866](https://github.com/DataDog/integrations-core/pull/10866))

## 5.4.2 / 2021-10-07 / Agent 7.32.0

***Fixed***:

* Hide collect_device_metadata by default ([#10349](https://github.com/DataDog/integrations-core/pull/10349))

## 5.4.1 / 2021-10-06

***Fixed***:

* Remove python only mention from check discovery props ([#10352](https://github.com/DataDog/integrations-core/pull/10352))

## 5.4.0 / 2021-10-04

***Added***:

* Update dependencies ([#10258](https://github.com/DataDog/integrations-core/pull/10258))
* Add autodiscovery integration configs ([#10079](https://github.com/DataDog/integrations-core/pull/10079))
* Add autodiscovery_subnet tag to discovered_devices_count metric ([#10072](https://github.com/DataDog/integrations-core/pull/10072))

***Fixed***:

* Better naming for testing environments ([#10070](https://github.com/DataDog/integrations-core/pull/10070))
* Bump base package requirement ([#10078](https://github.com/DataDog/integrations-core/pull/10078))

## 5.3.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Add `ifNumber` to `_generic-if.yaml` ([#9875](https://github.com/DataDog/integrations-core/pull/9875))
* Refactor profile validators ([#9741](https://github.com/DataDog/integrations-core/pull/9741))

***Fixed***:

* Enclose community string using single quote ([#9742](https://github.com/DataDog/integrations-core/pull/9742))
* Test string float value in e2e ([#9689](https://github.com/DataDog/integrations-core/pull/9689))

## 5.2.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add collect device metadata config ([#9393](https://github.com/DataDog/integrations-core/pull/9393))
* Add rate type to error and discard counters ([#9218](https://github.com/DataDog/integrations-core/pull/9218)) Thanks [loganmc10](https://github.com/loganmc10).

***Fixed***:

* Improve snmp example config ([#9417](https://github.com/DataDog/integrations-core/pull/9417))
* Revert "Add collect device metadata config" ([#9439](https://github.com/DataDog/integrations-core/pull/9439))
* Fix mypy lint issue ([#9288](https://github.com/DataDog/integrations-core/pull/9288))
* Update conf.yaml.example - wrong file name ([#7704](https://github.com/DataDog/integrations-core/pull/7704))

## 5.1.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Add doc for instance batch size config ([#9109](https://github.com/DataDog/integrations-core/pull/9109))
* Add python loader tag to telemetry metrics ([#9038](https://github.com/DataDog/integrations-core/pull/9038))
* [snmp] add metrics and tags to dell-rac profile ([#8812](https://github.com/DataDog/integrations-core/pull/8812))

## 5.0.1 / 2021-03-10 / Agent 7.27.0

***Fixed***:

* Fix snmp get bulk log ([#8803](https://github.com/DataDog/integrations-core/pull/8803))

## 5.0.0 / 2021-03-07

***Changed***:

* Move SNMP auto_conf.yaml to agent repo ([#8709](https://github.com/DataDog/integrations-core/pull/8709))

***Added***:

* Add BGP metrics to Juniper SRX Profile ([#8771](https://github.com/DataDog/integrations-core/pull/8771))
* Support for additional Juniper devices ([#8749](https://github.com/DataDog/integrations-core/pull/8749))

***Fixed***:

* Fix Juniper EX sysObjectIds  ([#8728](https://github.com/DataDog/integrations-core/pull/8728))
* Better tests for generic_host_resources ([#8266](https://github.com/DataDog/integrations-core/pull/8266))
* Add extract_value_pattern  to log on failure to submit metric ([#8693](https://github.com/DataDog/integrations-core/pull/8693))
* 🐛  [snmp] use OIDPrinter to debug oids from bulks ([#8688](https://github.com/DataDog/integrations-core/pull/8688))
* Fix oids not increasing link ([#8655](https://github.com/DataDog/integrations-core/pull/8655))

## 4.1.0 / 2021-02-16

***Added***:

* Add extract value feature ([#8622](https://github.com/DataDog/integrations-core/pull/8622))
* Add SNMP check duration, interval, metrics count ([#8211](https://github.com/DataDog/integrations-core/pull/8211))

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 4.0.0 / 2021-01-25 / Agent 7.26.0

***Changed***:

* Add missing metrics to hp-ilo4 profile ([#8220](https://github.com/DataDog/integrations-core/pull/8220))

***Added***:

* Snmp Juniper profiles for EX (switches), MX (routers) and SRX (firewalls) series ([#8206](https://github.com/DataDog/integrations-core/pull/8206))

***Fixed***:

* Use mibless syntax for _generic-host-resources.yaml ([#8305](https://github.com/DataDog/integrations-core/pull/8305))

## 3.10.0 / 2020-12-07 / Agent 7.25.0

***Added***:

* Add snmp interface bandwidth usage metric ([#8093](https://github.com/DataDog/integrations-core/pull/8093))
* Add interface alias (ifAlias) as a tag to interface metrics ([#8018](https://github.com/DataDog/integrations-core/pull/8018)) Thanks [loganmc10](https://github.com/loganmc10).
* Add generic Cisco ASA profile ([#7971](https://github.com/DataDog/integrations-core/pull/7971))

***Fixed***:

* Use MIB less syntax in example and link to profile format doc ([#8073](https://github.com/DataDog/integrations-core/pull/8073))
* Add back cisco-asa-5525.yaml ([#8041](https://github.com/DataDog/integrations-core/pull/8041))
* Improve symbol metric example ([#8071](https://github.com/DataDog/integrations-core/pull/8071))
* Add deprecation notice for metric[].name syntax ([#8070](https://github.com/DataDog/integrations-core/pull/8070))
* Add device_index to idrac (AI-938) ([#7525](https://github.com/DataDog/integrations-core/pull/7525))

## 3.9.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Add 'device vendor' tag to metrics ([#7871](https://github.com/DataDog/integrations-core/pull/7871))
* Track fetch ID in debug logs ([#7736](https://github.com/DataDog/integrations-core/pull/7736))
* Make refresh_oids_cache_interval available as init_config ([#7821](https://github.com/DataDog/integrations-core/pull/7821))
* Support alternative Mac Address index ([#7688](https://github.com/DataDog/integrations-core/pull/7688))

***Fixed***:

* Adding tag ciscoEnvMonSupplyStatusDescr to disambiguate metric ([#7782](https://github.com/DataDog/integrations-core/pull/7782))

## 3.8.0 / 2020-09-04 / Agent 7.23.0

***Added***:

* Add `index_transform` to support tagging using another table with different indexes ([#7489](https://github.com/DataDog/integrations-core/pull/7489))

***Fixed***:

* Validate SNMP profile hierarchy ([#6798](https://github.com/DataDog/integrations-core/pull/6798))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 3.7.1 / 2020-08-12 / Agent 7.22.0

***Fixed***:

* Fix apc ups profile ([#7351](https://github.com/DataDog/integrations-core/pull/7351))
* Revert Fix wrong indentation of `table` key in column metric tags #7024 ([#7349](https://github.com/DataDog/integrations-core/pull/7349))

## 3.7.0 / 2020-08-03

***Added***:

* Add OID caching ([#7231](https://github.com/DataDog/integrations-core/pull/7231))

***Fixed***:

* Refactor how OIDs are managed ([#7230](https://github.com/DataDog/integrations-core/pull/7230))
* Sanitize OctetString ([#7221](https://github.com/DataDog/integrations-core/pull/7221))
* Rename all_oids to scalar_oids ([#7229](https://github.com/DataDog/integrations-core/pull/7229))
* Better logging for submit_metric ([#7188](https://github.com/DataDog/integrations-core/pull/7188))

## 3.6.0 / 2020-07-24

***Added***:

* Check tag for table metric ([#6933](https://github.com/DataDog/integrations-core/pull/6933))
* Add new `flag_stream` type ([#7072](https://github.com/DataDog/integrations-core/pull/7072))
* Add cisco catalyst profile ([#6925](https://github.com/DataDog/integrations-core/pull/6925))
* Allow list of sysoids in profiles ([#6936](https://github.com/DataDog/integrations-core/pull/6936))

***Fixed***:

* Sanitize forced types values and cast to float ([#7133](https://github.com/DataDog/integrations-core/pull/7133))
* Add `.0` to scalar oids ([#7105](https://github.com/DataDog/integrations-core/pull/7105))
* Use OID instead of MIB for sysName ([#7104](https://github.com/DataDog/integrations-core/pull/7104))
* Submit additional rate metrics in fortigate profile ([#7058](https://github.com/DataDog/integrations-core/pull/7058))

## 3.5.3 / 2020-07-01 / Agent 7.21.0

***Fixed***:

* Fix autodiscovery_subnet var in auto_conf.yaml ([#7029](https://github.com/DataDog/integrations-core/pull/7029))

## 3.5.2 / 2020-06-30

***Fixed***:

* Fix tag names for cisco asa profile ([#7027](https://github.com/DataDog/integrations-core/pull/7027))

## 3.5.1 / 2020-06-30

***Fixed***:

* Fix wrong indentation of `table` key in column metric tags ([#7024](https://github.com/DataDog/integrations-core/pull/7024))

## 3.5.0 / 2020-06-29

***Added***:

* Add regex match support for Tables ([#6951](https://github.com/DataDog/integrations-core/pull/6951))
* Add snmp.devices_monitored metric ([#6941](https://github.com/DataDog/integrations-core/pull/6941))
* Add IF-MIB metrics to the Meraki profile ([#6905](https://github.com/DataDog/integrations-core/pull/6905))
* Add RTT metrics ([#6872](https://github.com/DataDog/integrations-core/pull/6872))

***Fixed***:

* Clean up of unused extends in meraki cloud profile ([#6981](https://github.com/DataDog/integrations-core/pull/6981))
* [Refactor] Add device abstraction ([#6953](https://github.com/DataDog/integrations-core/pull/6953))
* [Refactor] Clean up batching implementation ([#6952](https://github.com/DataDog/integrations-core/pull/6952))
* Add index tagging to cfwConnectionStatValue ([#6897](https://github.com/DataDog/integrations-core/pull/6897))

## 3.4.0 / 2020-06-11

***Added***:

* Add NetApp profile ([#6841](https://github.com/DataDog/integrations-core/pull/6841))

***Fixed***:

* Fix `instance_number` tag on Cisco voice router metrics ([#6867](https://github.com/DataDog/integrations-core/pull/6867))

## 3.3.0 / 2020-06-10

***Added***:

* Add Fortinet FortiGate profile ([#6504](https://github.com/DataDog/integrations-core/pull/6504)) Thanks [lindseyferretti](https://github.com/lindseyferretti).
* Reuse MIB builder objects per SNMP engine ([#6716](https://github.com/DataDog/integrations-core/pull/6716))
* Add HP health profile mixin ([#6757](https://github.com/DataDog/integrations-core/pull/6757))
* Add routing metrics to additional profiles ([#6764](https://github.com/DataDog/integrations-core/pull/6764))
* Add router metrics to cisco voice base profile ([#6737](https://github.com/DataDog/integrations-core/pull/6737))

***Fixed***:

* Fix gauge metrics wrongly submitted as rates in CISCO voice profile ([#6794](https://github.com/DataDog/integrations-core/pull/6794))
* Push received metrics on partial failure ([#6814](https://github.com/DataDog/integrations-core/pull/6814))
* Flatten Cisco profiles hierarchy ([#6792](https://github.com/DataDog/integrations-core/pull/6792))
* Add missing tags to profiles tables ([#6765](https://github.com/DataDog/integrations-core/pull/6765))
* Fix name KeyError ([#6788](https://github.com/DataDog/integrations-core/pull/6788))
* Properly handle potential embedded null characters ([#6640](https://github.com/DataDog/integrations-core/pull/6640))
* Remove iDRAC/poweredge profile inheritance ([#6754](https://github.com/DataDog/integrations-core/pull/6754))
* Make profiles compatible with previous parsing ([#6750](https://github.com/DataDog/integrations-core/pull/6750))

## 3.2.2 / 2020-05-21 / Agent 7.20.0

***Fixed***:

* Fix error handling in getnext ([#6701](https://github.com/DataDog/integrations-core/pull/6701))

## 3.2.1 / 2020-05-19

***Fixed***:

* Add missing auto_conf ([#6687](https://github.com/DataDog/integrations-core/pull/6687))

## 3.2.0 / 2020-05-17

***Added***:

* Add diskStatus tag to Isilon profile ([#6660](https://github.com/DataDog/integrations-core/pull/6660))
* Add BPG metrics to more profiles ([#6655](https://github.com/DataDog/integrations-core/pull/6655))
* Add voice metrics and profiles ([#6629](https://github.com/DataDog/integrations-core/pull/6629))

## 3.1.0 / 2020-05-14

***Added***:

* Add `chatsworth` legacy metrics ([#6624](https://github.com/DataDog/integrations-core/pull/6624))
* Add ifHighSpeed ([#6602](https://github.com/DataDog/integrations-core/pull/6602))
* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Improve autodiscovery support ([#6526](https://github.com/DataDog/integrations-core/pull/6526))

***Fixed***:

* Exit discovery thread when check is gc-ed ([#6484](https://github.com/DataDog/integrations-core/pull/6484))
* Don't use ifDescr for metric tagging ([#6601](https://github.com/DataDog/integrations-core/pull/6601))
* Optimize away useless GET calls ([#6456](https://github.com/DataDog/integrations-core/pull/6456))

## 3.0.0 / 2020-05-04

***Changed***:

* Throw error if two profiles have the same sysObjectID ([#6501](https://github.com/DataDog/integrations-core/pull/6501))

***Added***:

* Add base BGP4 and Cisco-CSR1000v profiles ([#6315](https://github.com/DataDog/integrations-core/pull/6315))
* Collect OSPF routing metrics ([#6554](https://github.com/DataDog/integrations-core/pull/6554))
* Add F5 Big IP local traffic management (LTM) metrics ([#5963](https://github.com/DataDog/integrations-core/pull/5963))
* Add more HP metrics ([#6542](https://github.com/DataDog/integrations-core/pull/6542))
* Add more idrac/dell metrics ([#6540](https://github.com/DataDog/integrations-core/pull/6540))
* Add additional Cisco metrics ([#6539](https://github.com/DataDog/integrations-core/pull/6539))
* Add more metrics to Palo Alto profile ([#6541](https://github.com/DataDog/integrations-core/pull/6541))
* Add upsOutletGroupStatusGroupState metric to APC UPS profile ([#6555](https://github.com/DataDog/integrations-core/pull/6555))
* Add ifspeed metric to interface profile ([#6499](https://github.com/DataDog/integrations-core/pull/6499))
* Add Isilon profile ([#6518](https://github.com/DataDog/integrations-core/pull/6518))
* Add APC UPS profile ([#6505](https://github.com/DataDog/integrations-core/pull/6505))
* Add env metric to cisco base profile ([#6517](https://github.com/DataDog/integrations-core/pull/6517))
* Submit throughput as a rate ([#6384](https://github.com/DataDog/integrations-core/pull/6384))
* Add more Cisco ASA metrics ([#6335](https://github.com/DataDog/integrations-core/pull/6335))
* Add MIB resolution to `OID` model ([#6242](https://github.com/DataDog/integrations-core/pull/6242))

***Fixed***:

* Change default timeout to 5 ([#6546](https://github.com/DataDog/integrations-core/pull/6546))
* Remove empty values in config ([#6455](https://github.com/DataDog/integrations-core/pull/6455))
* Use `OID` model in `OIDResolver` ([#6469](https://github.com/DataDog/integrations-core/pull/6469))
* Isolate parsing logic into a dedicated sub-package ([#6398](https://github.com/DataDog/integrations-core/pull/6398))
* Isolate PySNMP inspection hacks ([#6461](https://github.com/DataDog/integrations-core/pull/6461))
* Drop outdated `warning` parameter in `parse_metrics` ([#6412](https://github.com/DataDog/integrations-core/pull/6412))
* Fix debug output ([#6400](https://github.com/DataDog/integrations-core/pull/6400))
* Check types on all modules ([#6392](https://github.com/DataDog/integrations-core/pull/6392))
* Fix misleading `metric_tags` naming on `ParsedMetric` ([#6387](https://github.com/DataDog/integrations-core/pull/6387))

## 2.6.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Small profiles cleanups ([#6233](https://github.com/DataDog/integrations-core/pull/6233))
* Remove duplicated idrac metrics from poweredge profile ([#6232](https://github.com/DataDog/integrations-core/pull/6232))
* Only load installed profiles once ([#6231](https://github.com/DataDog/integrations-core/pull/6231))
* Fix tag matching documentation ([#6226](https://github.com/DataDog/integrations-core/pull/6226))

## 2.6.0 / 2020-03-24

***Added***:

* Support regular expressions in dynamic tags ([#6096](https://github.com/DataDog/integrations-core/pull/6096))
* Aruba, Arista and PDU profiles ([#6002](https://github.com/DataDog/integrations-core/pull/6002))
* Load all profiles by default ([#6051](https://github.com/DataDog/integrations-core/pull/6051))
* Add checkpoint firewall profile ([#6021](https://github.com/DataDog/integrations-core/pull/6021))
* Add types to compat module ([#6029](https://github.com/DataDog/integrations-core/pull/6029))
* Refactor and add types to `OIDResolver` ([#6017](https://github.com/DataDog/integrations-core/pull/6017))
* Add `OID` helper class ([#6000](https://github.com/DataDog/integrations-core/pull/6000))
* Add Cisco ASA 5525 profile and refactor cisco base profile ([#5958](https://github.com/DataDog/integrations-core/pull/5958))
* Move PySNMP imports to a dedicated module ([#5990](https://github.com/DataDog/integrations-core/pull/5990))
* Add Palo Alto and generic host resources SNMP profiles ([#5914](https://github.com/DataDog/integrations-core/pull/5914))

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Implement `str()` for `OID` instances ([#6046](https://github.com/DataDog/integrations-core/pull/6046))
* Move metric types to new module ([#6044](https://github.com/DataDog/integrations-core/pull/6044))
* Isolate logic for converting SNMP values to metrics ([#6031](https://github.com/DataDog/integrations-core/pull/6031))
* Move PySNMP imports to a separate `pysnmp_types` module ([#6013](https://github.com/DataDog/integrations-core/pull/6013))
* Drop unused log argument on InstanceConfig ([#6007](https://github.com/DataDog/integrations-core/pull/6007))
* Add OIDs to router profiles ([#5991](https://github.com/DataDog/integrations-core/pull/5991))
* Validate and cast `discovery_interval` to a number ([#5887](https://github.com/DataDog/integrations-core/pull/5887))

## 2.5.0 / 2020-02-27 / Agent 7.18.0

***Added***:

* Query discovered devices in threads ([#5462](https://github.com/DataDog/integrations-core/pull/5462))

***Fixed***:

* Fix issue with tags leaking between discovered instances ([#5899](https://github.com/DataDog/integrations-core/pull/5899))

## 2.4.1 / 2020-02-25

***Fixed***:

* Handle case when servers report two values for entries in `metric_tags` ([#5853](https://github.com/DataDog/integrations-core/pull/5853))

## 2.4.0 / 2020-02-22

***Added***:

* Add extension mechanism for SNMP profiles ([#5821](https://github.com/DataDog/integrations-core/pull/5821))
* Add snmp_host tag by default to profiles ([#5812](https://github.com/DataDog/integrations-core/pull/5812))
* Add hpe proliant profile ([#5724](https://github.com/DataDog/integrations-core/pull/5724))
* Tag metrics by profile ([#5787](https://github.com/DataDog/integrations-core/pull/5787))
* Add `ignored_ip_addresses` option to ignore specific IP addresses when scanning a network. ([#5785](https://github.com/DataDog/integrations-core/pull/5785))
* Add basic types to SNMP integration ([#5782](https://github.com/DataDog/integrations-core/pull/5782))
* Use all matching profiles instead of only the most specific one ([#5768](https://github.com/DataDog/integrations-core/pull/5768))
* Add a new metric_tags configuration ([#5765](https://github.com/DataDog/integrations-core/pull/5765))
* Add profile for HP iLO4 devices ([#5637](https://github.com/DataDog/integrations-core/pull/5637))
* Fetch sysUpTimeInstance automatically ([#5752](https://github.com/DataDog/integrations-core/pull/5752))
* Add Dell Poweredge profile ([#5723](https://github.com/DataDog/integrations-core/pull/5723))

***Fixed***:

* Switch back to most specific profile matching ([#5813](https://github.com/DataDog/integrations-core/pull/5813))

## 2.3.2 / 2020-01-15 / Agent 7.17.0

***Fixed***:

* Tweak behavior related to discovery ([#5466](https://github.com/DataDog/integrations-core/pull/5466))

## 2.3.1 / 2020-01-13

***Fixed***:

* Fix usage of old OID list attributes on InstanceConfig ([#5412](https://github.com/DataDog/integrations-core/pull/5412))

## 2.3.0 / 2020-01-07

***Added***:

* Remove MIB requirement in profiles ([#5397](https://github.com/DataDog/integrations-core/pull/5397))
* Implement table browsing with OIDs ([#5368](https://github.com/DataDog/integrations-core/pull/5368))
* Update license years ([#5384](https://github.com/DataDog/integrations-core/pull/5384))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))
* Add a profile for Meraki cloud devices ([#5215](https://github.com/DataDog/integrations-core/pull/5215))

## 2.2.0 / 2020-01-02

***Added***:

* Add profile for Cisco Nexus switches ([#5363](https://github.com/DataDog/integrations-core/pull/5363))
* Add profile for Intel IDRAC devices ([#5227](https://github.com/DataDog/integrations-core/pull/5227))

***Fixed***:

* Fetch table OIDs per table ([#5192](https://github.com/DataDog/integrations-core/pull/5192))

## 2.1.0 / 2019-11-27 / Agent 7.16.0

***Added***:

* Add Cisco 3850 profile ([#5090](https://github.com/DataDog/integrations-core/pull/5090))

***Fixed***:

* Disable MIB autofetch ([#5094](https://github.com/DataDog/integrations-core/pull/5094))

## 2.0.1 / 2019-11-21

***Fixed***:

* Handle total_time_to_temporal_percent missing ([#5055](https://github.com/DataDog/integrations-core/pull/5055))

## 2.0.0 / 2019-11-15

***Changed***:

* Modify profile layout ([#4997](https://github.com/DataDog/integrations-core/pull/4997))

***Added***:

* Add interface statuses to profiles ([#5004](https://github.com/DataDog/integrations-core/pull/5004))
* Ignore metrics that are not retrieved ([#5003](https://github.com/DataDog/integrations-core/pull/5003))
* Match profile with sysobject_id prefix ([#4990](https://github.com/DataDog/integrations-core/pull/4990))
* Count the number of discovered devices ([#4978](https://github.com/DataDog/integrations-core/pull/4978))
* Generic network router profile ([#4937](https://github.com/DataDog/integrations-core/pull/4937))
* Allow tagging through different MIBs ([#4853](https://github.com/DataDog/integrations-core/pull/4853))

## 1.14.1 / 2019-10-16 / Agent 6.15.0

***Fixed***:

* Fix allowed host failure retry logic ([#4782](https://github.com/DataDog/integrations-core/pull/4782))

## 1.14.0 / 2019-10-14

***Added***:

* Store discovered hosts ([#4712](https://github.com/DataDog/integrations-core/pull/4712))

## 1.13.0 / 2019-10-11

***Added***:

* Automatically fetch MIBs that we don't know about ([#4732](https://github.com/DataDog/integrations-core/pull/4732))

## 1.12.0 / 2019-10-10

***Added***:

* Add profile for F5 BIG-IP devices ([#4674](https://github.com/DataDog/integrations-core/pull/4674))

## 1.11.0 / 2019-09-19

***Added***:

* Use bulk call when possible ([#4530](https://github.com/DataDog/integrations-core/pull/4530))
* Remove failing discovered hosts ([#4526](https://github.com/DataDog/integrations-core/pull/4526))
* Basic discovery mechanism and test ([#4511](https://github.com/DataDog/integrations-core/pull/4511))
* Allow autoconfiguration of instances by sysObjectId ([#4391](https://github.com/DataDog/integrations-core/pull/4391))

***Fixed***:

* Handle bytes in network_address ([#4577](https://github.com/DataDog/integrations-core/pull/4577))

## 1.10.0 / 2019-08-24 / Agent 6.14.0

***Added***:

* Support referencing metrics by profile ([#4329](https://github.com/DataDog/integrations-core/pull/4329))
* Upgrade pyasn1 ([#4289](https://github.com/DataDog/integrations-core/pull/4289))
* Reimplement config load logic ([#4160](https://github.com/DataDog/integrations-core/pull/4160))

## 1.9.0 / 2019-07-13 / Agent 6.13.0

***Added***:

* Add support for string types ([#4087](https://github.com/DataDog/integrations-core/pull/4087))

## 1.8.0 / 2019-07-04

***Added***:

* Match OIDs with leading dots ([#3854](https://github.com/DataDog/integrations-core/pull/3854))

## 1.7.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3565](https://github.com/DataDog/integrations-core/pull/3565))

## 1.6.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Add metrics config globally ([#3230](https://github.com/DataDog/integrations-core/pull/3230))

## 1.5.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Improve performance by querying only necessary columns from a table ([#3059](https://github.com/DataDog/integrations-core/pull/3059))
* Support Python 3 ([#3016](https://github.com/DataDog/integrations-core/pull/3016))

***Fixed***:

* Log the correct information about snmpnext result ([#3021](https://github.com/DataDog/integrations-core/pull/3021))

## 1.4.2 / 2018-10-12 / Agent 6.6.0

***Fixed***:

* Fix `enforce_mib_constraints` parameter having no effect. ([#2340](https://github.com/DataDog/integrations-core/pull/2340))

## 1.4.1 / 2018-09-04 / Agent 6.5.0

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.4.0 / 2018-05-11

***Added***:

* Enhance error handling when metrics aren't defined or device cannot be reached ([#1406](https://github)com/DataDog/integrations-core/issues/1406)

## 1.3.1 / 2018-02-13

***Fixed***:

* Fix warning service check reporting ([#1041](https://github)com/DataDog/integrations-core/issues/1041)

## 1.3.0 / 2017-10-10

***Added***:

* Add support for SNMPv3 Contexts ([#723](https://github)com/DataDog/integrations-core/issues/723)

## 1.2.0 / 2017-07-18

***Changed***:

* Drop dependency on pycrypto ([#426](https://github)com/DataDog/integrations-core/issues/426)

## 1.1.0 / 2017-04-24

***Added***:

* Add individual metric tagging to OID and MIB Non-tabular data ([#248](https://github)com/DataDog/integrations-core/issues/248)

## 1.0.0 / 2017-03-22

***Added***:

* adds snmp integration.
