# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import exceptions, helpers


class Tenant:
    """
    Collect tenant metrics from the APIC
    """

    def __init__(self, check, api, instance, instance_hash):
        self.check = check
        self.api = api
        self.instance = instance
        self.check_tags = check.check_tags
        self.user_tags = instance.get('tags', [])
        self.instance_hash = instance_hash

        # grab some functions from the check
        self.gauge = check.gauge
        self.rate = check.rate
        self.log = check.log
        self.submit_metrics = check.submit_metrics
        self.tagger = self.check.tagger
        self.tenant_metrics = self.check.tenant_metrics

    def collect(self):
        tenants = self.instance.get('tenant', [])
        if len(tenants) == 0:
            self.log.warning('No tenants were listed in the config, skipping tenant collection')
            return

        self.log.info("collecting from %s tenants", len(tenants))
        # check if tenant exist before proceeding.
        for t in tenants:
            try:
                list_apps = self.api.get_apps(t)
                if list_apps is None:
                    break
                self.log.info("collecting %s apps from %s", len(list_apps), t)
                for app in list_apps:
                    self._submit_app_data(t, app)
                    app_name = app.get('fvAp', {}).get('attributes', {}).get('name')
                    if not app_name:
                        break
                    try:
                        list_epgs = self.api.get_epgs(t, app_name)
                        self.log.info("collecting %s endpoint groups from %s", len(list_epgs), app_name)
                        self._submit_epg_data(t, app_name, list_epgs)
                    except (exceptions.APIConnectionException, exceptions.APIParsingException):
                        pass
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
            self._submit_ten_data(t)

    def _submit_app_data(self, tenant, app):
        a = app.get('fvAp', {})
        app_name = a.get('attributes', {}).get('name')
        if not app_name:
            return
        stats = self.api.get_app_stats(tenant, app_name)
        tags = self.tagger.get_application_tags(a)
        self.submit_raw_obj(stats, tags, 'application')

    def _submit_epg_data(self, tenant, app, epgs):
        for epg_data in epgs:
            epg = epg_data.get('fvAEPg', {})
            epg_name = epg.get('attributes', {}).get('name')
            if not epg_name:
                continue
            stats = self.api.get_epg_stats(tenant, app, epg_name)
            tags = self.tagger.get_endpoint_group_tags(epg)
            self.submit_raw_obj(stats, tags, 'endpoint_group')

    def _submit_ten_data(self, tenant):
        if not tenant:
            return
        try:
            stats = self.api.get_tenant_stats(tenant)
            tags = ["tenant:" + tenant]
            self.submit_raw_obj(stats, tags, 'tenant')
        except (exceptions.APIConnectionException, exceptions.APIParsingException):
            pass

    def submit_raw_obj(self, raw_stats, tags, obj_type):
        got_health = False
        for s in raw_stats:
            name = list(s.keys())[0]
            # we only want to collect the 15 minutes metrics.
            if '15min' not in name:
                self.log.debug("Skipping metric: %s because it does not contain 15min in its name", name)
                continue

            attrs = s.get(name, {}).get("attributes", {})
            if 'index' in attrs:
                self.log.debug("Skipping metric: %s because it contains index in its attributes", name)
                continue

            self.log.debug("submitting metrics for: %s", name)
            metrics = {}

            tenant_metrics = self.tenant_metrics.get(obj_type, {})

            for n, ms in tenant_metrics.items():
                if n not in name:
                    continue
                for cisco_metric, dd_metric in ms.items():
                    mval = s.get(name, {}).get("attributes", {}).get(cisco_metric)
                    json_attrs = s.get(name, {}).get("attributes", {})
                    if mval and helpers.check_metric_can_be_zero(cisco_metric, mval, json_attrs):
                        metrics[dd_metric] = mval
            if 'fvOverallHealth' in name:
                got_health = True
            self.submit_metrics(metrics, tags, instance=self.instance)

        if got_health:
            return
        self.log.debug("No fvOverallHealth reported, looking for healthInst instead")
        health_insts = [s for s in raw_stats if list(s.keys())[0] == "healthInst"]
        if not health_insts:
            self.log.debug("No healthInst reported")
            return
        s = health_insts[0]
        self.log.debug("submitting metrics for: %s", 'healthInst')
        metrics = {}

        ms = self.tenant_metrics.get(obj_type, {}).get('healthInst', {})
        for cisco_metric, dd_metric in ms.items():
            mval = s.get('healthInst', {}).get("attributes", {}).get(cisco_metric)
            json_attrs = s.get('healthInst', {}).get("attributes", {})
            if mval and helpers.check_metric_can_be_zero(cisco_metric, mval, json_attrs):
                metrics[dd_metric] = mval
        self.submit_metrics(metrics, tags, instance=self.instance)
