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
        self.send_faultinst_faults = self.instance.get('send_faultinst_faults', False)
        # Config for submitting faultDelegate faults as logs
        self.send_faultdelegate_faults = self.instance.get('send_faultdelegate_faults', False)

    def faultinst_faults_enabled(self):
        return self.send_faultinst_faults

    def faultdelegate_faults_enabled(self):
        return self.send_faultdelegate_faults

    def collect(self):
        if self.faultinst_faults_enabled():
            data = self.read_persistent_cache("maxtimestamp_{}".format("faultInst"))
            maxtimestamp = from_json(data) if data else None
            faults = self.api.get_faultinst_faults(maxtimestamp)
            self.submit_faults("faultInst", faults)
        if self.faultdelegate_faults_enabled():
            data = self.read_persistent_cache("maxtimestamp_{}".format("faultDelegate"))
            maxtimestamp = from_json(data) if data else None
            faults = self.api.get_faultdelegate_faults(maxtimestamp)
            self.submit_faults("faultDelegate", faults)

    def submit_faults(self, faultCategory, faults):
        if len(faults) == 0:
            return

        maxtimestamp = 0.0
        for fault in faults:
            payload = {}
            if faultCategory in fault:
                payload = fault[faultCategory]["attributes"]
                payload["aciFaultCategory"] = faultCategory
            else:
                self.log.warning("fault does not contain %s: %s", faultCategory, fault)
                continue

            # Rename severity field because the backend seems to give precedence to severity over any status
            # remapper when determining the actual status, and renaming the severity field in a pipeline
            # processor doesn't work, possibly because of how JSON logs are preprocessed.
            # (See https://docs.datadoghq.com/logs/log_configuration/pipelines/?tab=status#status-attribute).
            payload["aciSeverity"] = payload.pop("severity")

            maxtimestamp = max(maxtimestamp, get_timestamp(datetime.datetime.fromisoformat(payload["lastTransition"])))
            self.send_log(payload)

        self.write_persistent_cache("maxtimestamp_{}".format(faultCategory), to_json(maxtimestamp))
