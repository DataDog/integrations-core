# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from tests.checks.common import AgentCheckTest, load_check
from utils.ntp import NTPUtil

class TestNtp(AgentCheckTest):
    """Basic Test for ntp integration."""
    CHECK_NAME = 'ntp'

    def test_ntp_global_settings(self):
        # Clear any existing ntp config
        NTPUtil._drop()

        config = {'instances': [{
            "host": "foo.com",
            "port": "bar",
            "version": 42,
            "timeout": 13.37}],
            'init_config': {}}

        agentConfig = {
            'version': '0.1',
            'api_key': 'toto',
            'additional_checksd': '.',
        }

        # load this config in the ntp singleton
        ntp_util = NTPUtil(config)

        # default min collection interval for that check was 20sec
        check = load_check('ntp', config, agentConfig)
        check.run()

        self.assertEqual(ntp_util.args["host"], "foo.com")
        self.assertEqual(ntp_util.args["port"], "bar")
        self.assertEqual(ntp_util.args["version"], 42)
        self.assertEqual(ntp_util.args["timeout"], 13.37)

        # Clear the singleton to prepare for next config
        NTPUtil._drop()

        config = {'instances': [{}], 'init_config': {}}
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        # load the new config
        ntp_util = NTPUtil(config)

        # default min collection interval for that check was 20sec
        check = load_check('ntp', config, agentConfig)
        try:
            check.run()
        except Exception:
            pass

        self.assertTrue(ntp_util.args["host"].endswith("datadog.pool.ntp.org"))
        self.assertEqual(ntp_util.args["port"], "ntp")
        self.assertEqual(ntp_util.args["version"], 3)
        self.assertEqual(ntp_util.args["timeout"], 1.0)

        NTPUtil._drop()
