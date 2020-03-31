# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from collections import defaultdict
from datetime import datetime, timedelta

from dateutil import parser, tz
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.serialization import json

from .config import Config
from .utils import normalize_api_data_inplace

DOCKERIO_PREFIX = "docker.io/"

# min_severity tag allows to query number of vulns for a severity target easily
SEVERITY_TAGS = {
    "low": ["severity:low", "min_severity:low"],
    "medium": ["severity:medium", "min_severity:low", "min_severity:medium"],
    "high": ["severity:high", "min_severity:low", "min_severity:medium", "min_severity:high"],
    "critical": [
        "severity:critical",
        "min_severity:low",
        "min_severity:medium",
        "min_severity:high",
        "min_severity:critical",
    ],
}


class TwistlockCheck(AgentCheck):
    NAMESPACE = 'twistlock'

    HTTP_CONFIG_REMAPPER = {'ssl_verify': {'name': 'tls_verify'}}

    def __init__(self, name, init_config, instances):
        super(TwistlockCheck, self).__init__(name, init_config, instances)

        self.last_run = datetime.utcnow()

        self.config = None
        if instances:
            self.config = Config(instances[0])

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Instance missing "url" value.')

        if not self.config:
            self.config = Config(instance)

        if not self.config.username or not self.config.password:
            raise Exception('The Twistlock check requires both a username and a password')

        # alert if a scan hasn't been able to run in a few hours and then in a day
        # only calculate this once per check run
        self.current_date = datetime.now(tz.tzutc())
        self.warning_date = self.current_date - timedelta(hours=7)
        self.critical_date = self.current_date - timedelta(days=1)

        self.report_license_expiration()
        self.report_registry_scan()
        self.report_images_scan()
        self.report_hosts_scan()
        self.report_container_compliance()

        self.report_vulnerabilities()

        self.last_run = datetime.utcnow()

    def report_license_expiration(self):
        service_check_name = "{}.license_ok".format(self.NAMESPACE)
        try:
            license = self._retrieve_json("/api/v1/settings/license")
            if "expiration_date" not in license:
                raise Exception("expiration_date not found.")
        except Exception as e:
            self.warning("cannot retrieve license data: %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=self.config.tags)
            raise e

        # alert if your license will expire in 30 days and then in a week
        expiration_date = parser.isoparse(license.get("expiration_date"))
        current_date = datetime.now(tz.tzutc())
        warning_date = current_date + timedelta(days=30)
        critical_date = current_date + timedelta(days=7)

        licence_status = AgentCheck.OK
        if expiration_date < warning_date:
            licence_status = AgentCheck.WARNING
        if expiration_date < critical_date:
            licence_status = AgentCheck.CRITICAL
        self.service_check(
            service_check_name, licence_status, tags=self.config.tags, message=license.get("expiration_date")
        )

    def report_registry_scan(self):
        namespace = "{}.registry".format(self.NAMESPACE)
        service_check_name = "{}.can_connect".format(self.NAMESPACE)
        try:
            scan_result = self._retrieve_json("/api/v1/registry")
            self.service_check(service_check_name, AgentCheck.OK, tags=self.config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=self.config.tags)
            return None

        for image in scan_result:
            if '_id' not in image:
                continue

            image_name = image['_id']
            if image_name.startswith(DOCKERIO_PREFIX):
                image_name = image_name[len(DOCKERIO_PREFIX) :]
            image_tags = ["scanned_image:{}".format(image_name)] + self.config.tags

            self._report_layer_count(image, namespace, image_tags)
            self._report_service_check(
                image, namespace, tags=image_tags, message="Last scan: {}".format(image.get("scanTime"))
            )
            self._report_vuln_info(namespace, image, image_tags)
            self._report_compliance_information(namespace, image, image_tags)

    def report_images_scan(self):
        namespace = "{}.images".format(self.NAMESPACE)
        service_check_name = "{}.can_connect".format(self.NAMESPACE)
        try:
            scan_result = self._retrieve_json("/api/v1/images")
            self.service_check(service_check_name, AgentCheck.OK, tags=self.config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=self.config.tags)
            return None

        for image in scan_result:
            # if it's not a valid image result, skip it
            if '_id' not in image:
                continue

            instances = image.get('instances')
            instance = instances[0]
            image_name = instance.get('image')
            if not image_name:
                continue
            if image_name.startswith(DOCKERIO_PREFIX):
                image_name = image_name[len(DOCKERIO_PREFIX) :]
            image_tags = ["scanned_image:{}".format(image_name)] + self.config.tags

            self._report_layer_count(image, namespace, image_tags)
            self._report_service_check(
                image, namespace, tags=image_tags, message="Last scan: {}".format(image.get("scanTime"))
            )
            self._report_vuln_info(namespace, image, image_tags)
            self._report_compliance_information(namespace, image, image_tags)

    def report_hosts_scan(self):
        namespace = "{}.hosts".format(self.NAMESPACE)
        service_check_name = "{}.can_connect".format(self.NAMESPACE)
        try:
            scan_result = self._retrieve_json("/api/v1/hosts")
            self.service_check(service_check_name, AgentCheck.OK, tags=self.config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=self.config.tags)
            return None

        for host in scan_result:
            # if there's no hostname, skip it
            if 'hostname' not in host:
                continue

            hostname = host['hostname']
            host_tags = ["scanned_host:{}".format(hostname)] + self.config.tags

            self._report_service_check(
                host, namespace, tags=host_tags, message="Last scan: {}".format(host.get("scanTime"))
            )
            self._report_vuln_info(namespace, host, host_tags)
            self._report_compliance_information(namespace, host, host_tags)

    def report_container_compliance(self):
        namespace = "{}.containers".format(self.NAMESPACE)
        service_check_name = "{}.can_connect".format(self.NAMESPACE)
        try:
            scan_result = self._retrieve_json("/api/v1/containers")
            self.service_check(service_check_name, AgentCheck.OK, tags=self.config.tags)
        except Exception as e:
            self.warning("cannot retrieve registry data: %s", e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=self.config.tags)
            return None

        for container in scan_result:
            # if there's no id, skip it
            if '_id' not in container:
                continue

            container_tags = []
            name = container.get('name')
            if name:
                container_tags += ["container_name:{}".format(name)]
            image_name = container.get('imageName')
            if image_name:
                container_tags += ["image_name:{}".format(image_name)]
            container_tags += self.config.tags

            self._report_service_check(
                container, namespace, tags=container_tags, message="Last scan: {}".format(container.get("scanTime"))
            )
            self._report_compliance_information(namespace, container, container_tags)

    def report_vulnerabilities(self):
        vuln_containers = self._retrieve_json('/api/v1/stats/vulnerabilities')

        for vuln_container in vuln_containers:
            host_vulns = vuln_container.get('hostVulnerabilities')
            image_vulns = vuln_container.get('imageVulnerabilities')
            if not host_vulns and not image_vulns:
                continue

            if host_vulns:
                for host_vuln in host_vulns:
                    self._analyze_vulnerability(host_vuln, host=True)
            if image_vulns:
                for image_vuln in image_vulns:
                    self._analyze_vulnerability(image_vuln, image=True)

    def _analyze_vulnerability(self, vuln, host=False, image=False):
        cve_id = vuln.get('id')
        # if it doesn't have a cve id, it's probably an invalid record
        if not cve_id:
            return

        description = vuln.get('description')

        published = vuln.get('published')

        published_date = datetime.fromtimestamp(int(published))

        if published_date < self.last_run:
            if host:
                vuln_type = 'hosts'
            elif image:
                vuln_type = 'images'
            else:
                vuln_type = 'systems'

            msg_text = """
            There is a new CVE affecting your {}:
            {}
            """.format(
                vuln_type, description
            )

            event = {
                'timestamp': time.mktime(published_date.timetuple()),
                'event_type': 'twistlock',
                'msg_title': cve_id,
                'msg_text': msg_text,
                "tags": self.config.tags,
                "aggregation_key": cve_id,
                'host': self.hostname,
            }

            self.event(event)

    def _report_vuln_info(self, namespace, data, tags):
        # CVE vulnerabilities
        summary = defaultdict(int)
        severity_types = ["critical", "high", "medium", "low"]
        for severity_type in severity_types:
            summary[severity_type] = 0

        cves = data.get('vulnerabilities', []) or []
        for cve in cves:
            summary[cve['severity']] += 1
            cve_tags = ['cve:{}'.format(cve['cve'])] + SEVERITY_TAGS.get(cve['severity'], []) + tags
            if 'packageName' in cve:
                cve_tags += ["package:{}".format(cve['packageName'])]
            self.gauge('{}.cve.details'.format(namespace), float(1), cve_tags)
        # Send counts to avoid no-data on zeroes
        for severity, count in iteritems(summary):
            cve_tags = SEVERITY_TAGS.get(severity, []) + tags
            self.gauge('{}.cve.count'.format(namespace), float(count), cve_tags)

    def _report_compliance_information(self, namespace, data, tags):
        compliance = defaultdict(int)
        vulns = data.get('complianceDistribution', {}) or {}
        severity_types = ["critical", "high", "medium", "low"]
        for severity_type in severity_types:
            compliance[severity_type] += vulns.get(severity_type, 0)
            compliance_tags = SEVERITY_TAGS.get(severity_type, []) + tags
            self.gauge('{}.compliance.count'.format(namespace), compliance[severity_type], compliance_tags)

    def _report_layer_count(self, data, namespace, tags):
        # Layer count and size
        layer_count = 0
        layer_sizes = 0
        for layer in data.get('history', []):
            layer_count += 1
            layer_sizes += layer.get('sizeBytes', 0)
        self.gauge('{}.size'.format(namespace), float(layer_sizes), tags)
        self.gauge('{}.layer_count'.format(namespace), float(layer_count), tags)

    def _report_service_check(self, data, prefix, tags=None, message=""):
        # Last scan service check
        scan_date = parser.isoparse(data.get("scanTime"))
        scan_status = AgentCheck.OK
        if scan_date < self.warning_date:
            scan_status = AgentCheck.WARNING
        if scan_date < self.critical_date:
            scan_status = AgentCheck.CRITICAL
        self.service_check('{}.is_scanned'.format(prefix), scan_status, tags=tags, message=message)

    def _retrieve_json(self, path):
        url = self.config.url + path
        project = self.config.project
        qparams = {'project': project} if project else None
        response = self.http.get(url, params=qparams)
        try:
            # it's possible to get a null response from the server
            # {} is a bit easier to deal with
            j = json.loads(response.content) or {}
            if 'err' in j:
                err_msg = "Error in response: {}".format(j.get("err"))
                self.log.error(err_msg)
                raise Exception(err_msg)
            normalize_api_data_inplace(j)
            return j
        except Exception as e:
            self.log.debug("cannot get a response: %s response is: %s", e, response.text)
            raise e
