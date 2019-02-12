# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import Counter
from datetime import datetime, timedelta

from datadog_checks.checks import AgentCheck

from .config import Config
from .utils import retrieve_json

REGISTRY_SCAN_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SCAN_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
LICENCE_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

DOCKERIO_PREFIX = "docker.io/"

# min_severity tag allows to query number of vulns for a severity target easily
SEVERITY_TAGS = {
    "low": ["severity:low", "min_severity:low"],
    "medium": ["severity:medium", "min_severity:low", "min_severity:medium"],
    "high": ["severity:high", "min_severity:low", "min_severity:medium", "min_severity:high"],
    "critical": ["severity:critical", "min_severity:low", "min_severity:medium",
                 "min_severity:high", "min_severity:critical"]
}


class TwistlockCheck(AgentCheck):
    NAMESPACE = 'twistlock'

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Instance missing "url" value.')

        config = Config(instance)

        current_date = datetime.now()
        self._warning_date = current_date - timedelta(hours=7)
        self._critical_date = current_date - timedelta(days=1)

        self._report_license_expiration(config)
        self._report_registry_scan(config)
        self._report_images_scan(config)
        self._report_hosts_scan(config)

    def _report_license_expiration(self, config):
        service_check_name = self.NAMESPACE + ".license_ok"
        try:
            license = retrieve_json(config, "/api/v1/settings/license")
        except Exception as e:
            self.warning("cannot retrieve license data: {}".format(e))
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=config.tags)
            return None

        expiration_date = datetime.strptime(license.get("expiration_date"), LICENCE_DATE_FORMAT)
        current_date = datetime.now()
        warning_date = current_date + timedelta(days=30)
        critical_date = current_date + timedelta(days=7)

        licence_status = AgentCheck.OK
        if expiration_date < warning_date:
            licence_status = AgentCheck.WARNING
        if expiration_date < critical_date:
            licence_status = AgentCheck.CRITICAL
        self.service_check(service_check_name, licence_status,
                           tags=config.tags, message=license.get("expiration_date"))

    def _report_registry_scan(self, config):
        namespace = self.NAMESPACE + ".registry"
        service_check_name = self.NAMESPACE + ".can_connect"
        try:
            scan_result = retrieve_json(config, "/api/v1/registry")
            self.service_check(service_check_name, AgentCheck.OK, tags=config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: {}".format(e))
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=config.tags)
            return None

        current_date = datetime.now()
        warning_date = current_date - timedelta(hours=7)
        critical_date = current_date - timedelta(days=1)

        for image in scan_result:
            if '_id' not in image:
                continue

            image_name = image['_id']
            if image_name.startswith(DOCKERIO_PREFIX):
                image_name = image_name[len(DOCKERIO_PREFIX):]

            image_tags = ["scanned_image:" + image_name] + config.tags

            # Layer count and size
            layer_count = 0
            layer_sizes = 0
            for layer in image.get('info', {}).get('history', []):
                layer_count += 1
                layer_sizes += layer.get('sizeBytes', 0)
            self.gauge(namespace + '.image.size', float(layer_sizes), image_tags)
            self.gauge(namespace + '.image.layer_count', float(layer_count), image_tags)

            # Last scan service check
            scan_date = datetime.strptime(image.get("scanTime"), REGISTRY_SCAN_DATE_FORMAT)
            scan_status = AgentCheck.OK
            if scan_date < warning_date:
                scan_status = AgentCheck.WARNING
            if scan_date < critical_date:
                scan_status = AgentCheck.CRITICAL
            self.service_check(namespace + '.image.is_scanned', scan_status,
                               tags=image_tags, message="Last scan: " + image.get("scanTime"))

            # CVE vulnerabilities
            summary = Counter({"critical": 0, "high": 0, "medium": 0, "low": 0})
            cves = image.get('info', {}).get('cveVulnerabilities', []) or []
            for cve in cves:
                summary[cve['severity']] += 1
                tags = [
                    'cve:' + cve['cve'],
                ] + SEVERITY_TAGS.get(cve['severity'], []) + image_tags
                if 'packageName' in cve:
                    tags += ["package:" + cve['packageName']]
                self.gauge(namespace + '.image.cve.details', float(1), tags)
            # Send counts to avoid no-data on zeroes
            for severity, count in summary.iteritems():
                tags = SEVERITY_TAGS.get(severity, []) + image_tags
                self.gauge(namespace + '.image.cve.count', float(count), tags)

    def _report_images_scan(self, config):
        namespace = self.NAMESPACE + ".images"
        service_check_name = self.NAMESPACE + ".can_connect"
        try:
            scan_result = retrieve_json(config, "/api/v1/images")
            self.service_check(service_check_name, AgentCheck.OK, tags=config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: {}".format(e))
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=config.tags)
            return None

        current_date = datetime.now()
        warning_date = current_date - timedelta(hours=7)
        critical_date = current_date - timedelta(days=1)

        for image in scan_result:
            if '_id' not in image:
                continue


            instances = image.get('instances')
            instance = instances[0]
            image_name = instance.get('image')
            if not image_name:
                continue
            if image_name.startswith(DOCKERIO_PREFIX):
                image_name = image_name[len(DOCKERIO_PREFIX):]

            image_tags = ["scanned_image:" + image_name] + config.tags

            # Layer count and size
            layer_count = 0
            layer_sizes = 0
            for layer in image.get('info', {}).get('history', []):
                layer_count += 1
                layer_sizes += layer.get('sizeBytes', 0)
            self.gauge(namespace + '.image.size', float(layer_sizes), image_tags)
            self.gauge(namespace + '.image.layer_count', float(layer_count), image_tags)

            # Last scan service check
            scan_date = datetime.strptime(image.get("scanTime"), SCAN_DATE_FORMAT)
            scan_status = AgentCheck.OK
            if scan_date < warning_date:
                scan_status = AgentCheck.WARNING
            if scan_date < critical_date:
                scan_status = AgentCheck.CRITICAL
            self.service_check(namespace + '.image.is_scanned', scan_status,
                               tags=image_tags, message="Last scan: " + image.get("scanTime"))

            # CVE vulnerabilities
            summary = Counter({"critical": 0, "high": 0, "medium": 0, "low": 0})
            cves = image.get('info', {}).get('cveVulnerabilities', []) or []
            for cve in cves:
                summary[cve['severity']] += 1
                tags = [
                    'cve:' + cve['cve'],
                ] + SEVERITY_TAGS.get(cve['severity'], []) + image_tags
                if 'packageName' in cve:
                    tags += ["package:" + cve['packageName']]
                self.gauge(namespace + '.image.cve.details', float(1), tags)
            # Send counts to avoid no-data on zeroes
            for severity, count in summary.iteritems():
                tags = SEVERITY_TAGS.get(severity, []) + image_tags
                self.gauge(namespace + '.image.cve.count', float(count), tags)

    def _report_hosts_scan(self, config):
        namespace = self.NAMESPACE + ".hosts"
        service_check_name = self.NAMESPACE + ".can_connect"
        try:
            scan_result = retrieve_json(config, "/api/v1/hosts")
            self.service_check(service_check_name, AgentCheck.OK, tags=config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: {}".format(e))
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=config.tags)
            return None

        for host in scan_result:
            if 'hostname' not in host:
                continue

            hostname = host['hostname']

            host_tags = ["scanned_host:" + hostname] + config.tags

            self._report_service_check(host,
                                       namespace + '.host',
                                       SCAN_DATE_FORMAT,
                                       tags=host_tags,
                                       message="Last scan: " + host.get("scanTime"))

            # CVE vulnerabilities
            summary = Counter({"critical": 0, "high": 0, "medium": 0, "low": 0})
            cves = host.get('info', {}).get('cveVulnerabilities', []) or []
            for cve in cves:
                summary[cve['severity']] += 1
                tags = [
                    'cve:' + cve['cve'],
                ] + SEVERITY_TAGS.get(cve['severity'], []) + host_tags
                if 'packageName' in cve:
                    tags += ["package:" + cve['packageName']]
                self.gauge(namespace + '.host.cve.details', float(1), tags)
            # Send counts to avoid no-data on zeroes
            for severity, count in summary.iteritems():
                tags = SEVERITY_TAGS.get(severity, []) + host_tags
                self.gauge(namespace + '.host.cve.count', float(count), tags)


    def _report_service_check(self, data, prefix, format, tags=[], message=""):
        # Last scan service check
        scan_date = datetime.strptime(data.get("scanTime"), format)
        scan_status = AgentCheck.OK
        if scan_date < self._warning_date:
            scan_status = AgentCheck.WARNING
        if scan_date < self._critical_date:
            scan_status = AgentCheck.CRITICAL
        self.service_check(prefix + '.is_scanned',
                           scan_status,
                           tags=tags,
                           message=message)

    def _report_cve_vulnerabilities(self):
        pass
