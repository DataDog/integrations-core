# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime

from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.base.utils.serialization import from_json, to_json


class Faults:
    """
    Collect faults from the APIC
    """

    def __init__(self, check, api, instance, namespace):
        self.check = check
        self.api = api
        self.instance = instance
        self.namespace = namespace

        self.log = check.log
        self.read_persistent_cache = check.read_persistent_cache
        self.send_log = check.send_log
        self.write_persistent_cache = check.write_persistent_cache

        # Config for submitting faultInst faults as logs
        self.send_faultinsts = self.instance.get('send_faultinsts', False)
        # Config for submitting faultDelegate faults as logs
        self.send_faultdelegates = self.instance.get('send_faultdelegates', False)

    def faultinsts_enabled(self):
        return self.send_faultinsts

    def faultdelegates_enabled(self):
        return self.send_faultdelegates

    def collect(self):
        if self.faultinsts_enabled():
            data = self.read_persistent_cache("maxtimestamp_{}".format("faultInst"))
            maxtimestamp = from_json(data) if data else None
            faults = self.api.get_faultinsts(maxtimestamp)
            self.submit_faults("faultInst", faults)
        if self.faultdelegates_enabled():
            data = self.read_persistent_cache("maxtimestamp_{}".format("faultDelegate"))
            maxtimestamp = from_json(data) if data else None
            faults = self.api.get_faultdelegates(maxtimestamp)
            self.submit_faults("faultDelegate", faults)

    def submit_faults(self, faultCategory, faults):
        if (len(faults) == 0):
            return

        maxtimestamp = 0.0
        for fault in faults:
            payload = {}
            if faultCategory in fault:
                payload = fault[faultCategory]["attributes"]
                payload["aciFaultCategory"] = faultCategory
            else:
                self.log.warn("fault does not contain %s: %s", faultCategory, fault)
                continue

            maxtimestamp = max(maxtimestamp, get_timestamp(datetime.datetime.fromisoformat(payload["lastTransition"])))
            self.send_log(payload)

        self.write_persistent_cache("maxtimestamp_{}".format(faultCategory), to_json(maxtimestamp))
