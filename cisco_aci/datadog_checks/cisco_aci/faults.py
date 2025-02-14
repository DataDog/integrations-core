# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# JMW copied and modified from fabric.py
# JMWDOWN
import time

from datadog_checks.base.utils.serialization import json

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

    def submit_faults(self, faults):
        for f in faults:
            self.log.info("JMW hack fabric.collect fault: %s", f)  # JMW debug

# sample fault
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
