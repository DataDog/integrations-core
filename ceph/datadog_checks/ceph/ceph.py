# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import re

import simplejson as json
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.subprocess_output import get_subprocess_output


class Ceph(AgentCheck):
    """ Collect metrics and events from ceph """

    DEFAULT_CEPH_CMD = '/usr/bin/ceph'
    DEFAULT_CEPH_CLUSTER = 'ceph'
    DEFAULT_HEALTH_CHECKS = [
        'OSD_DOWN',
        'OSD_ORPHAN',
        'OSD_FULL',
        'OSD_NEARFULL',
        'POOL_FULL',
        'POOL_NEAR_FULL',
        'PG_AVAILABILITY',
        'PG_DEGRADED',
        'PG_DEGRADED_FULL',
        'PG_DAMAGED',
        'PG_NOT_SCRUBBED',
        'PG_NOT_DEEP_SCRUBBED',
        'CACHE_POOL_NEAR_FULL',
        'TOO_FEW_PGS',
        'TOO_MANY_PGS',
        'OBJECT_UNFOUND',
        'REQUEST_SLOW',
        'REQUEST_STUCK',
    ]
    NAMESPACE = 'ceph'

    def _collect_raw(self, ceph_cmd, ceph_cluster, instance):
        use_sudo = _is_affirmative(instance.get('use_sudo', False))
        ceph_args = []
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')
            ceph_args = 'sudo {}'.format(ceph_cmd)
        else:
            ceph_args = ceph_cmd

        ceph_args = '{} --cluster {}'.format(ceph_args, ceph_cluster)

        raw = {}
        for cmd in ('mon_status', 'status', 'df detail', 'osd pool stats', 'osd perf', 'health detail'):
            try:
                args = '{} {} -fjson'.format(ceph_args, cmd)
                output, _, _ = get_subprocess_output(args.split(), self.log)
                res = json.loads(output)
            except Exception as e:
                self.log.warning('Unable to parse data from cmd=%s: %s', cmd, e)
                continue

            name = cmd.replace(' ', '_')
            raw[name] = res

        return raw

    def _extract_tags(self, raw, instance):
        tags = instance.get('tags', [])
        if 'mon_status' in raw:
            fsid = raw['mon_status']['monmap']['fsid']
            tags.append(self.NAMESPACE + '_fsid:%s' % fsid)
            tags.append(self.NAMESPACE + '_mon_state:%s' % raw['mon_status']['state'])

        return tags

    def _publish(self, raw, func, keyspec, tags):
        try:
            for k in keyspec:
                raw = raw[k]
            func(self.NAMESPACE + '.' + k, raw, tags)
        except KeyError:
            return

    def _extract_metrics(self, raw, tags):
        raw_osd_perf = raw.get('osd_perf', {}).get('osdstats', raw.get('osd_perf', {}))

        for osdperf in raw_osd_perf.get('osd_perf_infos', []):
            local_tags = tags + ['ceph_osd:osd%s' % osdperf['id']]
            self._publish(osdperf, self.gauge, ['perf_stats', 'apply_latency_ms'], local_tags)
            self._publish(osdperf, self.gauge, ['perf_stats', 'commit_latency_ms'], local_tags)

        if not raw_osd_perf.get('osd_perf_infos'):
            self.log.debug('Error retrieving osdperf metrics. Received {}', raw.get('osd_perf', {}))
            health = {'num_near_full_osds': 0, 'num_full_osds': 0}

            # In luminous, there are no more overall summary and detail fields, but rather
            # one summary and one detail field per check type in the checks field
            # For example, for near full osds, we have:
            # "checks": {
            # "OSD_NEARFULL": {
            #     "severity": "HEALTH_WARN",
            #     "summary": {
            #         "message": "1 nearfull osd(s)"
            #     },
            #     "detail": [
            #         {
            #             "message": "osd.0 is near full"
            #         }
            #     ]
            # }
            # The percentage used per osd does not appear anymore in the message,
            # so we won't send the metric osd.pct_used
            health_detail = raw.get('health_detail', {})
            if not health_detail or not ('checks' in health_detail or 'summary' in health_detail):
                self.log.debug('Error retrieving health metrics')

            if 'checks' in health_detail:
                for check_name, check_detail in iteritems(health_detail['checks']):
                    if check_name == 'OSD_NEARFULL':
                        health['num_near_full_osds'] = len(check_detail['detail'])
                    if check_name == 'OSD_FULL':
                        health['num_full_osds'] = len(check_detail['detail'])
            else:
                # Health summary will be empty if no bad news
                if health_detail.get('summary'):
                    for osdhealth in health_detail.get('detail', []):
                        osd, pct = self._osd_pct_used(osdhealth)
                        if osd:
                            local_tags = tags + ['ceph_osd:%s' % osd.replace('.', '')]

                            if 'near' in osdhealth:
                                health['num_near_full_osds'] += 1
                                local_health = {'osd.pct_used': pct}
                                self._publish(local_health, self.gauge, ['osd.pct_used'], local_tags)
                            else:
                                health['num_full_osds'] += 1
                                local_health = {'osd.pct_used': pct}
                                self._publish(local_health, self.gauge, ['osd.pct_used'], local_tags)

            self._publish(health, self.gauge, ['num_full_osds'], tags)
            self._publish(health, self.gauge, ['num_near_full_osds'], tags)

        pool_stats = raw.get('osd_pool_stats', {})
        if not pool_stats:
            self.log.debug('Error retrieving osd_pool_stats metrics')

        for osdinfo in pool_stats:
            name = osdinfo.get('pool_name')
            local_tags = tags + ['ceph_pool:%s' % name]
            ops = 0
            try:
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'read_op_per_sec'], local_tags)
                ops += osdinfo['client_io_rate']['read_op_per_sec']
            except KeyError:
                osdinfo['client_io_rate'].update({'read_op_per_sec': 0})
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'read_op_per_sec'], local_tags)

            try:
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'write_op_per_sec'], local_tags)
                ops += osdinfo['client_io_rate']['write_op_per_sec']
            except KeyError:
                osdinfo['client_io_rate'].update({'write_op_per_sec': 0})
                self._publish(osdinfo, self.gauge, ['client_io_rate', 'write_op_per_sec'], local_tags)

            if 'op_per_sec' not in osdinfo['client_io_rate']:
                osdinfo['client_io_rate'].update({'op_per_sec': ops})
            self._publish(osdinfo, self.gauge, ['client_io_rate', 'op_per_sec'], local_tags)

            if 'op_per_sec' not in osdinfo['read_bytes_sec']:
                osdinfo['client_io_rate'].update({'read_bytes_sec': 0})
            self._publish(osdinfo, self.gauge, ['client_io_rate', 'read_bytes_sec'], local_tags)

            if 'op_per_sec' not in osdinfo['write_bytes_sec']:
                osdinfo['client_io_rate'].update({'write_bytes_sec': 0})
            self._publish(osdinfo, self.gauge, ['client_io_rate', 'write_bytes_sec'], local_tags)

        status = raw.get('status', {})

        if 'osdmap' in status.get('osdmap'):
            osdstatus = status['osdmap']['osdmap']
            self._publish(osdstatus, self.gauge, ['num_osds'], tags)
            self._publish(osdstatus, self.gauge, ['num_in_osds'], tags)
            self._publish(osdstatus, self.gauge, ['num_up_osds'], tags)
        else:
            self.log.debug('Error retrieving osdstatus metrics')

        pgstatus = status.get('pgmap', {})
        if pgstatus:
            self._publish(pgstatus, self.gauge, ['num_pgs'], tags)
        else:
            self.log.debug('Error retrieving pgstatus metrics')
        for pgstate in pgstatus.get('pgs_by_state', {}):
            s_name = pgstate.get('state_name', "").replace("+", "_")
            if s_name:
                self.gauge(self.NAMESPACE + '.pgstate.' + s_name, pgstate['count'], tags)

        mon_status = raw.get('mon_status', {})
        mons = mon_status.get('monmap', {}).get('mons', None)
        if mons is not None:
            self.gauge(self.NAMESPACE + '.num_mons', len(mons), tags)
        else:
            self.log.debug('Error retrieving mon_status metrics')

        mons_active = mon_status.get('quorum', None)
        if mons_active is not None:
            self.gauge(self.NAMESPACE + '.num_mons.active', len(mons_active), tags)
        else:
            self.log.debug('Error retrieving mon_status quorum metrics')

        try:
            stats = raw['df_detail']['stats']
            self._publish(stats, self.gauge, ['total_objects'], tags)
            used = float(stats['total_used_bytes'])
            total = float(stats['total_bytes'])
            if total > 0:
                self.gauge(self.NAMESPACE + '.aggregate_pct_used', 100.0 * used / total, tags)

            l_pools = raw['df_detail']['pools']
            self.gauge(self.NAMESPACE + '.num_pools', len(l_pools), tags)
            for pdata in l_pools:
                local_tags = list(tags + [self.NAMESPACE + '_pool:%s' % pdata['name']])
                stats = pdata['stats']
                used = float(stats['bytes_used'])
                avail = float(stats['max_avail'])
                total = used + avail
                if total > 0:
                    self.gauge(self.NAMESPACE + '.pct_used', 100.0 * used / total, local_tags)
                self.gauge(self.NAMESPACE + '.num_objects', stats['objects'], local_tags)
                self.rate(self.NAMESPACE + '.read_bytes', stats['rd_bytes'], local_tags)
                self.rate(self.NAMESPACE + '.write_bytes', stats['wr_bytes'], local_tags)

        except (KeyError, ValueError):
            self.log.debug('Error retrieving df_detail metrics')

    def _osd_pct_used(self, health):
        """Take a single health check string, return (OSD name, percentage used)"""
        # Full string looks like: osd.2 is full at 95%
        # Near full string: osd.1 is near full at 94%
        pct = re.compile(r'\d+%').findall(health)
        osd = re.compile(r'osd.\d+').findall(health)
        if len(pct) > 0 and len(osd) > 0:
            return osd[0], int(pct[0][:-1])
        else:
            return None, None

    def _perform_service_checks(self, raw, tags, health_checks):
        if 'status' in raw:
            # In ceph luminous, the field name is now `status`
            s_status = raw['status']['health'].get('status', None)
            if not s_status:
                s_status = raw['status']['health']['overall_status']

            if s_status.find('_OK') != -1:
                status = AgentCheck.OK
            elif s_status.find('_WARN') != -1:
                status = AgentCheck.WARNING
            else:
                status = AgentCheck.CRITICAL
            self.service_check(self.NAMESPACE + '.overall_status', status, tags=tags)

            # If we are in ceph luminous, the 'checks' fields contains details of the health checks that are not OK
            # Report a service check for each of the checks listed in the yaml
            if "checks" in raw['status']['health']:
                for check in health_checks:
                    status = AgentCheck.OK
                    if check in raw['status']['health']['checks']:
                        if '_WARN' in raw['status']['health']['checks'][check]['severity']:
                            status = AgentCheck.WARNING
                        else:
                            status = AgentCheck.CRITICAL
                    self.service_check(self.NAMESPACE + '.' + check.lower(), status, tags=tags)

    def check(self, instance):
        ceph_cmd = instance.get('ceph_cmd') or self.DEFAULT_CEPH_CMD
        ceph_cluster = instance.get('ceph_cluster') or self.DEFAULT_CEPH_CLUSTER
        ceph_health_checks = instance.get('collect_service_check_for') or self.DEFAULT_HEALTH_CHECKS
        custom_tags = instance.get('tags', [])
        raw = self._collect_raw(ceph_cmd, ceph_cluster, instance)
        self._perform_service_checks(raw, custom_tags, ceph_health_checks)
        tags = self._extract_tags(raw, instance)
        self._extract_metrics(raw, tags)
