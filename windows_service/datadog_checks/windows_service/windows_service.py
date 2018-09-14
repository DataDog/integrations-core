# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

""" Collect status information for Windows services
"""

from datadog_checks.checks.win.wmi import WinWMICheck
from datadog_checks.utils.containers import hash_mutable
from datadog_checks.utils.timeout import TimeoutException


class WindowsService(WinWMICheck):
    STATE_TO_VALUE = {
        'Stopped': WinWMICheck.CRITICAL,
        'Start Pending': WinWMICheck.WARNING,
        'Stop Pending': WinWMICheck.WARNING,
        'Running': WinWMICheck.OK,
        'Continue Pending': WinWMICheck.WARNING,
        'Pause Pending': WinWMICheck.WARNING,
        'Paused': WinWMICheck.WARNING,
        'Unknown': WinWMICheck.UNKNOWN
    }
    NAMESPACE = "root\\CIMV2"
    CLASS = "Win32_Service"
    SERVICE_CHECK_NAME = 'windows_service.state'

    def __init__(self, name, init_config, agentConfig, instances):
        WinWMICheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        # Connect to the WMI provider
        host = instance.get('host', "localhost")
        user = instance.get('username', "")
        password = instance.get('password', "")
        services = instance.get('services', [])
        custom_tags = instance.get('tags', [])

        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, self.NAMESPACE, self.CLASS, instance_hash)
        tags = [] if (host == "localhost" or host == ".") else [u'host:{}'.format(host)]
        tags.extend(custom_tags)

        if len(services) == 0:
            raise Exception('No services defined in windows_service.yaml')

        properties = ["Name", "State"]
        if "ALL" in services:
            self.log.debug("tracking all services")
            filters = None
        else:
            filters = map(lambda x: {"Name": tuple(('LIKE', x)) if '%' in x else tuple(('=', x))}, services)

        wmi_sampler = self._get_wmi_sampler(
            instance_key,
            self.CLASS, properties,
            filters=filters,
            host=host, namespace=self.NAMESPACE,
            username=user, password=password
        )

        try:
            # Sample, extract & submit metrics
            wmi_sampler.sample()
        except TimeoutException:
            self.log.warning(
                u"[WinService] WMI query timed out."
                u" class={wmi_class} - properties={wmi_properties} -"
                u" filters={filters} - tags={tags}".format(
                    wmi_class=self.CLASS, wmi_properties=properties,
                    filters=filters, tags=tags
                )
            )
        else:
            self._process_services(wmi_sampler, services, tags)

    def _process_services(self, wmi_sampler, services, tags):
        specific_services = {}
        for svc in services:
            if svc == "ALL":
                continue
            if '%' in svc:
                continue
            specific_services[svc.lower()] = svc

        for wmi_obj in wmi_sampler:
            sc_name = wmi_obj['Name']
            sc_name_lower = sc_name.lower()
            if sc_name_lower in specific_services:
                try:
                    specific_services.pop(sc_name_lower, None)
                except KeyError:
                    pass

            status = self.STATE_TO_VALUE.get(wmi_obj["state"], WinWMICheck.UNKNOWN)
            self.service_check("windows_service.state", status, tags=tags + ['service:{}'.format(sc_name)])
            self.log.debug("service state for %s %s" % (sc_name, str(status)))

        for lsvc, svc in specific_services.items():
            self.service_check("windows_service.state", WinWMICheck.CRITICAL, tags=tags + ['service:{}'.format(svc)])
            self.log.debug("service state for %s %s" % (svc, str(WinWMICheck.CRITICAL)))
