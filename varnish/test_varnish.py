# stdlib
import os
import re
import subprocess

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


# This is a small extract of metrics from varnish. This is meant to test that
# the check gather metrics. This the check return everything from varnish
# without any selection/rename, their is no point in having a complete list.
COMMON_METRICS = [
    'varnish.uptime',              # metrics where the 'MAIN' prefix was removed
    'varnish.sess_conn',           # metrics where the 'MAIN' prefix was removed
    'varnish.sess_drop',           # metrics where the 'MAIN' prefix was removed
    'varnish.sess_fail',           # metrics where the 'MAIN' prefix was removed
    'varnish.client_req_400',      # metrics where the 'MAIN' prefix was removed
    'varnish.client_req_417',      # metrics where the 'MAIN' prefix was removed
    'varnish.client_req',          # metrics where the 'MAIN' prefix was removed
    'varnish.cache_hit',           # metrics where the 'MAIN' prefix was removed
    'varnish.cache_hitpass',       # metrics where the 'MAIN' prefix was removed
    'varnish.cache_miss',          # metrics where the 'MAIN' prefix was removed
    'varnish.backend_conn',        # metrics where the 'MAIN' prefix was removed
    'varnish.backend_unhealthy',   # metrics where the 'MAIN' prefix was removed
    'varnish.backend_busy',        # metrics where the 'MAIN' prefix was removed
    'varnish.fetch_eof',           # metrics where the 'MAIN' prefix was removed
    'varnish.fetch_bad',           # metrics where the 'MAIN' prefix was removed
    'varnish.fetch_none',          # metrics where the 'MAIN' prefix was removed
    'varnish.fetch_1xx',           # metrics where the 'MAIN' prefix was removed
    'varnish.pools',               # metrics where the 'MAIN' prefix was removed
    'varnish.busy_sleep',          # metrics where the 'MAIN' prefix was removed
    'varnish.busy_wakeup',         # metrics where the 'MAIN' prefix was removed
    'varnish.busy_killed',         # metrics where the 'MAIN' prefix was removed
    'varnish.sess_queued',         # metrics where the 'MAIN' prefix was removed
    'varnish.sess_dropped',        # metrics where the 'MAIN' prefix was removed
    'varnish.n_object',            # metrics where the 'MAIN' prefix was removed
    'varnish.n_vampireobject',     # metrics where the 'MAIN' prefix was removed
    'varnish.n_vcl',               # metrics where the 'MAIN' prefix was removed
    'varnish.n_vcl_avail',         # metrics where the 'MAIN' prefix was removed
    'varnish.n_vcl_discard',       # metrics where the 'MAIN' prefix was removed
    'varnish.bans',                # metrics where the 'MAIN' prefix was removed
    'varnish.bans_completed',      # metrics where the 'MAIN' prefix was removed
    'varnish.bans_obj',            # metrics where the 'MAIN' prefix was removed
    'varnish.bans_req',            # metrics where the 'MAIN' prefix was removed
    'varnish.MGT.child_start',
    'varnish.MGT.child_exit',
    'varnish.MGT.child_stop',
    'varnish.MEMPOOL.busyobj.live',
    'varnish.MEMPOOL.busyobj.pool',
    'varnish.MEMPOOL.busyobj.allocs',
    'varnish.MEMPOOL.busyobj.frees',
    'varnish.SMA.s0.c_req',
    'varnish.SMA.s0.c_fail',
    'varnish.SMA.Transient.c_req',
    'varnish.SMA.Transient.c_fail',
    'varnish.VBE.boot.default.req',
    'varnish.LCK.backend.creat',
    'varnish.LCK.backend_tcp.creat',
    'varnish.LCK.ban.creat',
    'varnish.LCK.ban.locks',
    'varnish.LCK.busyobj.creat',
    'varnish.LCK.mempool.creat',
    'varnish.LCK.vbe.creat',
    'varnish.LCK.vbe.destroy',
    'varnish.LCK.vcl.creat',
    'varnish.LCK.vcl.destroy',
    'varnish.LCK.vcl.locks',
]

VARNISH_DEFAULT_VERSION = "4.1.4"


@attr(requires='varnish')
class VarnishCheckTest(AgentCheckTest):
    CHECK_NAME = 'varnish'

    def _get_varnish_stat_path(self):
        varnish_version = os.environ.get('FLAVOR_VERSION', VARNISH_DEFAULT_VERSION).split('.', 1)[0]
        return "%s/ci/varnishstat%s" % (os.path.dirname(os.path.abspath(__file__)), varnish_version)

    def _get_config_by_version(self, name=None):
        config = {
            'instances': [{
                'varnishstat': self._get_varnish_stat_path(),
                'tags': ['cluster:webs']
            }]
        }

        if name:
            config['instances'][0]['name'] = name
        return config


    def test_check(self):
        config = self._get_config_by_version()

        self.run_check_twice(config)
        for mname in COMMON_METRICS:
            self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])

        config['instances'][0]['metrics_filter'] = ['SMA.*']
        self.run_check_twice(config)
        for mname in COMMON_METRICS:
            if 'SMA.' in mname:
                self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])
            else:
                self.assertMetric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])

        config['instances'][0]['metrics_filter'] = ['^SMA.Transient.c_req']
        self.run_check_twice(config)
        for mname in COMMON_METRICS:
            if 'SMA.Transient.c_req' in mname:
                self.assertMetric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])
            elif 'varnish.uptime' not in mname:
                self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])

    # This the docker image is in a different repository, we check that the
    # verison requested in the FLAVOR_VERSION is the on running inside the
    # container.
    def test_version(self):
        varnishstat = self._get_varnish_stat_path()
        output = subprocess.check_output([varnishstat, "-V"])
        res = re.search(r"varnish-(\d+\.\d\.\d)", output)
        if res is None:
            raise Exception("Could not retrieve varnish version from docker")

        version = res.groups()[0]
        self.assertEquals(version, os.environ.get('FLAVOR_VERSION', VARNISH_DEFAULT_VERSION))
