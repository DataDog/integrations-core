# stdlib
import os
import re
import subprocess
import mock
from distutils.version import LooseVersion # pylint: disable=E0611,E0401

# 3p
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest

# project
from tests.checks.common import AgentCheckTest, Fixtures

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

VARNISH_DEFAULT_VERSION = "4.1.7"
VARNISHADM_PATH = "varnishadm"
SECRETFILE_PATH = "secretfile"
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'ci')

# Varnish < 4.x varnishadm output
def debug_health_mock(*args, **kwargs):
    if args[0][0] == VARNISHADM_PATH or args[0][1] == VARNISHADM_PATH:
        return (Fixtures.read_file('debug_health_output', sdk_dir=FIXTURE_DIR), "", 0)
    else:
        return (Fixtures.read_file('stats_output', sdk_dir=FIXTURE_DIR), "", 0)

# Varnish >= 4.x && <= 5.x varnishadm output
def backend_list_mock(*args, **kwargs):
    if args[0][0] == VARNISHADM_PATH or args[0][1] == VARNISHADM_PATH:
        return (Fixtures.read_file('backend_list_output', sdk_dir=FIXTURE_DIR), "", 0)
    else:
        return (Fixtures.read_file('stats_output', sdk_dir=FIXTURE_DIR), "", 0)

# Varnish >= 5.x varnishadm output
def backend_list_mock_v5(*args, **kwargs):
    if args[0][0] == VARNISHADM_PATH or args[0][1] == VARNISHADM_PATH:
        return (Fixtures.read_file('backend_list_output', sdk_dir=FIXTURE_DIR), "", 0)
    else:
        return (Fixtures.read_file('stats_output_json', sdk_dir=FIXTURE_DIR), "", 0)

# Varnish >= 4.x && <= 5.x Varnishadm manually set backend to sick
def backend_manual_unhealthy_mock(*args, **kwargs):
    if args[0][0] == VARNISHADM_PATH or args[0][1] == VARNISHADM_PATH:
        return (Fixtures.read_file('backend_manually_unhealthy', sdk_dir=FIXTURE_DIR), "", 0)
    else:
        return (Fixtures.read_file('stats_output', sdk_dir=FIXTURE_DIR), "", 0)


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

    def test_inclusion_filter(self):
        config = self._get_config_by_version()
        config['instances'][0]['metrics_filter'] = ['SMA.*']

        self.run_check_twice(config)
        for mname in COMMON_METRICS:
            if 'SMA.' in mname:
                self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])
            else:
                self.assertMetric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])

    def test_exclusion_filter(self):
        # FIXME: Bugfix not released yet for version 5 so skip this test for this version:
        # See  https://github.com/varnishcache/varnish-cache/issues/2320
        config = self._get_config_by_version()
        config['instances'][0]['metrics_filter'] = ['^SMA.Transient.c_req']
        self.load_check(config)
        version, _ = self.check._get_version_info([self._get_varnish_stat_path()])
        if str(version) == '5.0.0':
            raise SkipTest('varnish bugfix for exclusion blob not released yet for version 5 so skip this test')

        self.run_check_twice(config)
        for mname in COMMON_METRICS:
            if 'SMA.Transient.c_req' in mname:
                self.assertMetric(mname, count=0, tags=['cluster:webs', 'varnish_name:default'])
            elif 'varnish.uptime' not in mname:
                self.assertMetric(mname, count=1, tags=['cluster:webs', 'varnish_name:default'])

    # Test the varnishadm output for version >= 4.x with manually set health
    @mock.patch('_varnish.geteuid')
    @mock.patch('_varnish.Varnish._get_version_info')
    @mock.patch('_varnish.get_subprocess_output', side_effect=backend_manual_unhealthy_mock)
    def test_command_line_manually_unhealthy(self, mock_subprocess, mock_version, mock_geteuid):
        mock_version.return_value = LooseVersion('4.0.0'), 'xml'
        mock_geteuid.return_value = 0

        config = self._get_config_by_version()
        config['instances'][0]['varnishadm'] = VARNISHADM_PATH
        config['instances'][0]['secretfile'] = SECRETFILE_PATH

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], [VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'debug.health'])
        self.assertServiceCheckCritical("varnish.backend_healthy", tags=['backend:default'], count=1)

        mock_version.return_value = LooseVersion('4.1.0'), 'xml'
        mock_geteuid.return_value = 1

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], ['sudo', VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'backend.list', '-p'])



    # Test the Varnishadm output for version >= 4.x
    @mock.patch('_varnish.geteuid')
    @mock.patch('_varnish.Varnish._get_version_info')
    @mock.patch('_varnish.get_subprocess_output', side_effect=backend_list_mock)
    def test_command_line_post_varnish4(self, mock_subprocess, mock_version, mock_geteuid):
        mock_version.return_value = LooseVersion('4.0.0'), 'xml'
        mock_geteuid.return_value = 0

        config = self._get_config_by_version()
        config['instances'][0]['varnishadm'] = VARNISHADM_PATH
        config['instances'][0]['secretfile'] = SECRETFILE_PATH

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], [VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'debug.health'])
        self.assertServiceCheckOK("varnish.backend_healthy", tags=['backend:backend2'], count=1)

        mock_version.return_value = LooseVersion('4.1.0'), 'xml'
        mock_geteuid.return_value = 1

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], ['sudo', VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'backend.list', '-p'])

    # Test the Varnishadm output for version >= 5.x
    @mock.patch('_varnish.geteuid')
    @mock.patch('_varnish.Varnish._get_version_info')
    @mock.patch('_varnish.get_subprocess_output', side_effect=backend_list_mock_v5)
    def test_command_line_post_varnish5(self, mock_subprocess, mock_version, mock_geteuid):
        mock_version.return_value = LooseVersion('5.0.0'), 'json'
        mock_geteuid.return_value = 0

        config = self._get_config_by_version()
        config['instances'][0]['varnishadm'] = VARNISHADM_PATH
        config['instances'][0]['secretfile'] = SECRETFILE_PATH

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], [VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'backend.list', '-p'])
        self.assertServiceCheckOK("varnish.backend_healthy", tags=['backend:backend2'], count=1)

        mock_version.return_value = LooseVersion('5.0.0'), 'json'
        mock_geteuid.return_value = 1

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], ['sudo', VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'backend.list', '-p'])

    # Test the varnishadm output for Varnish < 4.x
    @mock.patch('_varnish.geteuid')
    @mock.patch('_varnish.Varnish._get_version_info')
    @mock.patch('_varnish.get_subprocess_output', side_effect=debug_health_mock)
    def test_command_line(self, mock_subprocess, mock_version, mock_geteuid):
        mock_version.return_value = LooseVersion('4.0.0'), 'xml'
        mock_geteuid.return_value = 0

        config = self._get_config_by_version()
        config['instances'][0]['varnishadm'] = VARNISHADM_PATH
        config['instances'][0]['secretfile'] = SECRETFILE_PATH

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], [VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'debug.health'])
        self.assertServiceCheckOK("varnish.backend_healthy", tags=['backend:default'], count=1)

        mock_version.return_value = LooseVersion('4.1.0'), 'xml'
        mock_geteuid.return_value = 1

        self.run_check(config)
        args, _ = mock_subprocess.call_args
        self.assertEquals(args[0], ['sudo', VARNISHADM_PATH, '-S', SECRETFILE_PATH, 'backend.list', '-p'])

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
