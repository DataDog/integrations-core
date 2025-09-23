# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime

from datadog_checks.base.utils.serialization import from_json, to_json
from datadog_checks.base.utils.time import get_timestamp


class Faults:
    """
    Collect faults from the APIC
    """

    # Custom facets need to be namespaced because facets must have unique paths and a path cannot
    # be shared between different facet groups.  Most Cisco ACI fault fields are used as facets
    # so all fields will be moved under the namespace here rather than creating a remapper in the
    # pipeline for each field.
    ATTR_NAMESPACE = "cisco_aci"

    FAULTINST_KEY = "faultInst"
    FAULTDELEGATE_KEY = "faultDelegate"

    def __init__(self, check, api, instance, namespace):
        self.check = check
        self.api = api
        self.instance = instance
        self.namespace = namespace

        self.log = check.log
        self.read_persistent_cache = check.read_persistent_cache
        self.send_log = check.send_log
        self.write_persistent_cache = check.write_persistent_cache

        # Config for submitting device/interface metadata to NDM
        self.send_ndm_metadata = self.instance.get('send_ndm_metadata', False)
        # Config for submitting faultInst faults as logs
        self.send_faultinst_faults = self.instance.get('send_faultinst_faults', False)
        # Config for submitting faultDelegate faults as logs
        self.send_faultdelegate_faults = self.instance.get('send_faultdelegate_faults', False)

    def ndm_metadata_enabled(self):
        return self.send_ndm_metadata

    def faultinst_faults_enabled(self):
        return self.send_faultinst_faults

    def faultdelegate_faults_enabled(self):
        return self.send_faultdelegate_faults

    def collect(self):
        if self.faultinst_faults_enabled() or self.faultdelegate_faults_enabled():
            if not self.ndm_metadata_enabled():
                self.log.warning("NDM metadata must be enabled (send_ndm_metadata) to collect faults")
                return
            self.log.info("collecting faults")
        if self.faultinst_faults_enabled():
            data = self.read_persistent_cache("max_timestamp_{}".format(Faults.FAULTINST_KEY))
            max_timestamp = from_json(data) if data else None
            faults = self.api.get_faultinst_faults(max_timestamp)
            self.submit_faults(Faults.FAULTINST_KEY, faults)
        if self.faultdelegate_faults_enabled():
            data = self.read_persistent_cache("max_timestamp_{}".format(Faults.FAULTDELEGATE_KEY))
            max_timestamp = from_json(data) if data else None
            faults = self.api.get_faultdelegate_faults(max_timestamp)
            self.submit_faults(Faults.FAULTDELEGATE_KEY, faults)

    def submit_faults(self, faultCategory, faults):
        if len(faults) == 0:
            return

        max_timestamp = 0.0
        num_skipped = 0
        for fault in faults:
            payload = {}
            if faultCategory in fault:
                payload[Faults.ATTR_NAMESPACE] = fault[faultCategory]["attributes"]
                payload[Faults.ATTR_NAMESPACE]["faultCategory"] = faultCategory
            else:
                num_skipped += 1
                self.log.debug("skipping fault that does not contain %s: %s", faultCategory, fault)
                continue

            if "lastTransition" in payload[Faults.ATTR_NAMESPACE]:
                max_timestamp = max(
                    max_timestamp,
                    get_timestamp(datetime.datetime.fromisoformat(payload[Faults.ATTR_NAMESPACE]["lastTransition"])),
                )
            self.send_log(payload)

        self.write_persistent_cache("max_timestamp_{}".format(faultCategory), to_json(max_timestamp))

        if num_skipped > 0:
            self.log.warning("skipped %d faults that did not contain %s", num_skipped, faultCategory)
