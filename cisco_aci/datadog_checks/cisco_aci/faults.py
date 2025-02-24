# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# JMW copied and modified from fabric.py
# JMWDOWN
import datetime
import time

from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp

from . import aci_metrics, exceptions, helpers, ndm

VENDOR_CISCO = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100
DEVICE_USER_TAGS_PREFIX = "dd.internal.resource:ndm_device_user_tags"
INTERFACE_USER_TAGS_PREFIX = "dd.internal.resource:ndm_interface_user_tags"
# JMWUP


class Faults:
    """
    Collect faults from the APIC
    """

    def __init__(self, check, api, instance, namespace):
        self.check = check
        self.api = api
        self.instance = instance
        self.check_tags = check.check_tags
        self.namespace = namespace

        # Config for submitting device/interface metadata to NDM
        self.send_ndm_metadata = self.instance.get('send_ndm_metadata', False)

        # grab some functions from the check
        self.gauge = check.gauge
        self.rate = check.rate
        self.log = check.log
        self.submit_metrics = check.submit_metrics
        self.tagger = self.check.tagger
        self.external_host_tags = self.check.external_host_tags
        self.event_platform_event = check.event_platform_event

    # JMWDUP
    def ndm_enabled(self):
        return self.send_ndm_metadata

    def collect(self):
        self.log.info("JMWfaults.collect()")
        # JMW use this flag for faults too?
        if self.ndm_enabled():
            faults = self.api.get_faults()
            # JMW? collect_timestamp = int(time.time())
            self.submit_faults(faults)

            # JMW batch faults when sending as logs?
            # JMWFABRIC batches = ndm.batch_payloads(self.namespace, devices, interfaces, links, collect_timestamp)
            # JMWFABRIC for batch in batches:
            # JMWFABRIC     self.event_platform_event(json.dumps(batch.model_dump(exclude_none=True)), "network-devices-metadata")

# sample fault
# {
#   "faultInst": {
#     "attributes": {
#       "ack": "no",
#       "alert": "no",
#       "cause": "port-down",
#       "changeSet": "adminSt:up, autoNeg:on, bw:0, delay:1, dot1qEtherType:0x8100, fcotChannelNumber:Channel32, id:po1.1, inhBw:unspecified, isReflectiveRelayCfgSupported:Supported, layer:Layer3, linkDebounce:100, linkLog:default, mdix:auto, medium:broadcast, mode:trunk, mtu:0, name:bond1, operSt:down, portT:unknown, prioFlowCtrl:auto, reflectiveRelayEn:off, routerMac:not-applicable, snmpTrapSt:enable, spanMode:not-a-span-dest, speed:inherit, switchingSt:disabled, trunkLog:default, usage:discovery",
#       "childAction": "",
#       "code": "F0104",
#       "created": "2025-02-23T19:09:31.539-03:00",
#       "delegated": "no",
#       "descr": "Bond Interface po1.1 on node 1 of fabric ACI Fabric1 with hostname apic1 is now down",
#       "dn": "topology/pod-1/node-1/sys/caggr-[po1.1]/fault-F0104",
#       "domain": "infra",
#       "highestSeverity": "critical",
#       "lastTransition": "2025-02-23T19:11:37.877-03:00",
#       "lc": "raised",
#       "occur": "1",
#       "origSeverity": "critical",
#       "prevSeverity": "critical",
#       "rule": "cnw-aggr-if-down",
#       "severity": "critical",
#       "status": "",
#       "subject": "equipment",
#       "title": "",
#       "type": "operational"
#     }
#   }
# }
    def submit_faults(self, faults):
        for fault in faults:
            self.log.info("JMW faults submit_faults() fault: %s", fault)
            if isinstance(fault, dict):
                self.log.info("JMW fault is a dictionary")
            else:
                self.log.info("JMW fault is NOT a dictionary")
            if isinstance(fault, str):
                self.log.info("JMW fault is a str")
            else:
                self.log.info("JMW fault is NOT a str")

            # for log_element in log_elements:
            #     payload = {}
            #     payload['ddtags'] = ",".join(tags)  # JMW same for faults?
            #     payload['message'] = log_element.get("MessageText")
            #     payload['timestamp'] = get_timestamp(datetime.datetime.fromisoformat(log_element.get("OccurredAt")))  # JMWTIMESTAMP
            #     payload['status'] = log_element.get("Category")
            #     payload['stage_name'] = name
            #     self.send_log(payload)  # JMWTUE try something like this

            payload = {}
            # JMWTAGS? payload['ddtags'] = ",".join(tags)  # JMW same for faults?
            payload['ddsource'] = "cisco-aci-faults"  # JMW?

            # get created timestamp
# last_transition = fault.get("faultInst", {}).get("attributes", {}).get("lastTransition")

            faultinst = fault.get("faultInst", {})  # JMW dict
            #if isinstance(faultinst, dict):
                #self.log.info("JMW faultinst is a dictionary")
            #else:
                #self.log.info("JMW faultinst is NOT a dictionary")
            #if isinstance(faultinst, str):
                #self.log.info("JMW faultinst is a str")
            #else:
                #self.log.info("JMW faultinst is NOT a str")
            #self.log.info("JMW faultinst: %s", faultinst)

            attributes = faultinst.get("attributes", {})  # JMW dict

            payload['cause'] = attributes.get("cause")
            payload['code'] = attributes.get("code")
            payload['message'] = attributes.get("descr")
            payload['severity'] = attributes.get("severity")
            last_transition = attributes.get("lastTransition")  # JMW str
            self.log.info("JMW last_transition: %s", last_transition)

            # self.log.info("JMW submit_faults() trying to get timstamp from created ", fault.get("faultInst", {}).get("attributes", {}).get("created"))
            # self.log.info("JMW submit_faults() trying to get timstamp from lastTransition ", fault.get("faultInst", {}).get("attributes", {}).get("lastTransition"))
            # payload['timestamp'] = get_timestamp(datetime.datetime.fromisoformat(fault.get("created")))
            payload['timestamp'] = get_timestamp(datetime.datetime.fromisoformat(last_transition))
            payload['status'] = fault.get("severity")
            # JMW other fields

            self.log.info("JMW faults submit_faults() payload: %s", payload)

            # JMWNEXT       Error: 'Faults' object has no attribute 'send_log'
            self.send_log(payload)

            # exit out of for loop so we only send the first fault
            self.log.info("JMW HACK faults submit_faults() breaking out of loop")  # JMW debug
            break

# {
#   "ack": "no",
#   "alert": "no",
#   "cause": "interface-physical-down",
#   "changeSet": "accessVlan:unknown,backplaneMac:00:00:00:00:00:00,bundleBupId:0,bundleIndex:unspecified,cfgAccessVlan:unknown,cfgNativeVlan:unknown,currErrIndex:0,diags:none,encap:0,errDisTimerRunning:no,errVlanStatusHt:0,hwBdId:0,hwResourceId:0,intfT:phy,iod:0,lastErrors:8192,lastLinkStChg:1970-01-01T00:00:00.000+00:00,media:0,nativeVlan:unknown,numOfSI:0,operDceMode:off,operDuplex:auto,operEEERxWkTime:0,operEEEState:not-applicable,operEEETxWkTime:0,operErrDisQual:admin-down,operFecMode:inherit,operFlowCtrl:15,operMdix:auto,operMode:trunk,operModeDetail:trunk,operPhyEnSt:down,operRouterMac:00:00:00:00:00:00,operSpeed:inherit,operSt:down,operStQual:admin-down,operStQualCode:0,osSum:ok,portCfgWaitFlags:0,primaryVlan:unknown,resetCtr:0,txT:unknown,usage:discovery,userCfgdFlags:0,vdcId:0",
#   "childAction": "",
#   "code": "F0546",
#   "created": "2025-02-11T10:07:21.128+00:00",
#   "delegated": "no",
#   "descr": "Portisdown,reason:disabled(disabled),usedby:Discovery",
#   "dn": "topology/pod-1/node-103/sys/phys-[eth9/24]/phys/fault-F0546",
#   "domain": "access",
#   "highestSeverity": "warning",
# JMWFRI can I convert lastTransition to timestamp?  and will logging backend throw out duplicate logs w/ same timestamp?
#   "lastTransition": "2025-02-11T10:09:22.790+00:00",
#   "lc": "raised",
#   "occur": "1",
#   "origSeverity": "warning",
#   "prevSeverity": "warning",
#   "rule": "ethpm-if-port-down-no-infra",
#   "severity": "warning",
#   "status": "",
#   "subject": "port-down",
#   "title": "",
#   "type": "communications"
# }
