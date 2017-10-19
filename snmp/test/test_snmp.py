# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy

# 3rd party
from nose.plugins.attrib import attr

# agent
from checks import AgentCheck
from checks.metric_types import MetricTypes
from tests.checks.common import AgentCheckTest

# This test is dependent of having a fully open snmpd responding at localhost:161
# with an authentication by the Community String "public"
# This setup should normally be handled by the .travis.yml file, look there if
# you want to see how to run these tests locally

RESULTS_TIMEOUT = 10


@attr(requires='snmp')
class SNMPTestCase(AgentCheckTest):
    CHECK_NAME = 'snmp'
    CHECK_TAGS = ['snmp_device:localhost']

    AUTH_PROTOCOLS = {'MD5': 'usmHMACMD5AuthProtocol', 'SHA': 'usmHMACSHAAuthProtocol'}
    PRIV_PROTOCOLS = {'DES': 'usmDESPrivProtocol', 'AES': 'usmAesCfb128Protocol'}
    AUTH_KEY = 'doggiepass'
    PRIV_KEY = 'doggiePRIVkey'

    SNMP_CONF = {
        'ip_address': "localhost",
        'port': 11111,
        'community_string': "public",
    }

    SNMP_V3_CONF = {
        'ip_address': "localhost",
        'port': 11111,
        'user': None,
        'authKey': None,
        'privKey': None,
        'authProtocol': None,
        'privProtocol': None,
    }

    MIBS_FOLDER = {
        'init_config': {
            'mibs_folder': "/etc/mibs"
        },
        'instances' : [SNMP_CONF]
    }

    IGNORE_NONINCREASING_OID = {
        'init_config': {
            'ignore_nonincreasing_oid': True
        },
        'instances' : [SNMP_CONF]
    }

    SUPPORTED_METRIC_TYPES = [
        {
            'OID': "1.3.6.1.2.1.7.1.0",             # Counter32
            'name': "IAmACounter32"
        }, {
            'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter64
            'name': "IAmACounter64"
        }, {
            'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
            'name': "IAmAGauge32"
        }, {
            'OID': "1.3.6.1.2.1.88.1.1.1.0",        # Integer
            'name': "IAmAnInteger"
        }
    ]

    UNSUPPORTED_METRICS = [
        {
            'OID': "1.3.6.1.2.1.25.6.3.1.5.1",    # String (not supported)
            'name': "IAmString"
        }
    ]

    FORCED_METRICS = [
        {
            'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
            'name': "IAmAGauge32",
            'forced_type': 'counter'

        }, {
            'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter32
            'name': "IAmACounter64",
            'forced_type': 'gauge'
        }
    ]
    INVALID_FORCED_METRICS = [
        {
            'OID': "1.3.6.1.2.1.4.24.6.0",          # Gauge32
            'name': "IAmAGauge32",
            'forced_type': 'counter'

        }, {
            'OID': "1.3.6.1.2.1.4.31.1.1.6.1",      # Counter32
            'name': "IAmACounter64",
            'forced_type': 'histogram'
        }
    ]

    SCALAR_OBJECTS = [
        {
            'OID': "1.3.6.1.2.1.7.1.0",
            'name': "udpDatagrams"
        }, {
            'OID': "1.3.6.1.2.1.6.10.0",
            'name': "tcpInSegs"
        }, {
            'MIB': "TCP-MIB",
            'symbol': "tcpCurrEstab",
        }
    ]

    SCALAR_OBJECTS_WITH_TAGS = [
        {
            'OID': "1.3.6.1.2.1.7.1.0",
            'name': "udpDatagrams",
            'metric_tags': ['udpdgrams', 'UDP']
        }, {
            'OID': "1.3.6.1.2.1.6.10.0",
            'name': "tcpInSegs",
            'metric_tags': ['tcpinsegs', 'TCP']
        }, {
            'MIB': "TCP-MIB",
            'symbol': "tcpCurrEstab",
            'metric_tags': ['MIB', 'TCP', 'estab']
        }
    ]

    TABULAR_OBJECTS = [{
        'MIB': "IF-MIB",
        'table': "ifTable",
        'symbols': ["ifInOctets", "ifOutOctets"],
        'metric_tags': [
            {
                'tag': "interface",
                'column': "ifDescr"
            }, {
                'tag': "dumbindex",
                'index': 1
            }
        ]
    }]

    INVALID_METRICS = [
        {
            'MIB': "IF-MIB",
            'table': "noIdeaWhatIAmDoingHere",
            'symbols': ["ifInOctets", "ifOutOctets"],
        }
    ]

    PLAY_WITH_GET_NEXT_METRICS = [
        {
            "OID": "1.3.6.1.2.1.4.31.3.1.3.2",
            "name": "needFallback"
        }, {
            "OID": "1.3.6.1.2.1.4.31.3.1.3.2.1",
            "name": "noFallbackAndSameResult"
        }
    ]

    def run_check(self, config, agent_config=None, mocks=None, force_reload=False):
        if force_reload and self.check:
            self.check.stop()
        super(SNMPTestCase, self).run_check(config, agent_config, mocks, force_reload)

    def tearDown(self):
        if self.check:
            self.check.stop()

    @classmethod
    def generate_instance_config(cls, metrics, template=None):
        template = template if template else cls.SNMP_CONF
        instance_config = copy.copy(template)
        instance_config['metrics'] = metrics
        instance_config['name'] = "localhost"
        return instance_config

    @classmethod
    def generate_v3_instance_config(cls, metrics, name=None, user=None,
                                    auth=None, auth_key=None, priv=None, priv_key=None):
        instance_config = cls.generate_instance_config(metrics, cls.SNMP_V3_CONF)

        if name:
            instance_config['name'] = name
        if user:
            instance_config['user'] = user
        if auth:
            instance_config['authProtocol'] = auth
        if auth_key:
            instance_config['authKey'] = auth_key
        if priv:
            instance_config['privProtocol'] = priv
        if priv_key:
            instance_config['privKey'] = priv_key

        return instance_config

    def test_command_generator(self):
        """
        Command generator's parameters should match init_config
        """
        self.run_check(self.MIBS_FOLDER)
        cmdgen, _, _, _, _, _, _ = self.check._load_conf(self.SNMP_CONF)

        # Test command generator MIB source
        mib_folders = cmdgen.snmpEngine.msgAndPduDsp\
            .mibInstrumController.mibBuilder.getMibSources()
        full_path_mib_folders = map(lambda f: f.fullPath(), mib_folders)

        self.assertTrue("/etc/mibs" in full_path_mib_folders)
        self.assertFalse(cmdgen.ignoreNonIncreasingOid)

        # Test command generator `ignoreNonIncreasingOid` parameter
        self.run_check(self.IGNORE_NONINCREASING_OID, force_reload=True)
        cmdgen, _, _, _, _, _, _ = self.check._load_conf(self.SNMP_CONF)
        self.assertTrue(cmdgen.ignoreNonIncreasingOid)

    def test_type_support(self):
        """
        Support expected types
        """
        config = {
            'instances': [self.generate_instance_config(
                self.SUPPORTED_METRIC_TYPES + self.UNSUPPORTED_METRICS)]
        }
        self.run_check_n(config, repeat=3)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for metric in self.SUPPORTED_METRIC_TYPES:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)
        for metric in self.UNSUPPORTED_METRICS:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=0)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()

    def test_snpget(self):
        """
        When failing with 'snpget' command, SNMP check falls back to 'snpgetnext'

            > snmpget -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
            iso.3.6.1.2.1.25.6.3.1.4 = No Such Instance currently exists at this OID
            > snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.6.3.1.4
            iso.3.6.1.2.1.25.6.3.1.4.0 = INTEGER: 4
        """
        config = {
            'instances': [self.generate_instance_config(self.PLAY_WITH_GET_NEXT_METRICS)]
        }
        self.run_check_n(config, repeat=3)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.run_check(config)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for metric in self.PLAY_WITH_GET_NEXT_METRICS:
            metric_name = "snmp." + metric['name']
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()

    def test_scalar(self):
        """
        Support SNMP scalar objects
        """
        config = {
            'instances': [self.generate_instance_config(self.SCALAR_OBJECTS)]
        }
        self.run_check_n(config, repeat=3)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for metric in self.SCALAR_OBJECTS:
            metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
            self.assertMetric(metric_name, tags=self.CHECK_TAGS, count=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK, tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()

    def test_table(self):
        """
        Support SNMP tabular objects
        """
        config = {
            'instances': [self.generate_instance_config(self.TABULAR_OBJECTS)]
        }
        self.run_check_n(config, repeat=3, sleep=2)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()


    def test_table_v3_MD5_DES(self):
        """
        Support SNMP V3 priv modes: MD5 + DES
        """
        config = {
            'instances': []
        }

        # build multiple confgs
        auth = 'MD5'
        priv = 'DES'
        name = 'instance_{}_{}'.format(auth, priv)
        config['instances'].append(
            self.generate_v3_instance_config(
                self.TABULAR_OBJECTS,
                name=name,
                user='datadog{}{}'.format(auth.upper(), priv.upper()),
                auth=self.AUTH_PROTOCOLS[auth],
                auth_key=self.AUTH_KEY,
                priv=self.PRIV_PROTOCOLS[priv],
                priv_key=self.PRIV_KEY
            )
        )


        self.run_check_n(config, repeat=3, sleep=2)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()


    def test_table_v3_MD5_AES(self):
        """
        Support SNMP V3 priv modes: MD5 + AES
        """
        config = {
            'instances': []
        }

        # build multiple confgs
        auth = 'MD5'
        priv = 'AES'
        name = 'instance_{}_{}'.format(auth, priv)
        config['instances'].append(
            self.generate_v3_instance_config(
                self.TABULAR_OBJECTS,
                name=name,
                user='datadog{}{}'.format(auth.upper(), priv.upper()),
                auth=self.AUTH_PROTOCOLS[auth],
                auth_key=self.AUTH_KEY,
                priv=self.PRIV_PROTOCOLS[priv],
                priv_key=self.PRIV_KEY
            )
        )


        self.run_check_n(config, repeat=3, sleep=2)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()


    def test_table_v3_SHA_DES(self):
        """
        Support SNMP V3 priv modes: SHA + DES
        """
        config = {
            'instances': []
        }

        # build multiple confgs
        auth = 'SHA'
        priv = 'DES'
        name = 'instance_{}_{}'.format(auth, priv)
        config['instances'].append(
            self.generate_v3_instance_config(
                self.TABULAR_OBJECTS,
                name=name,
                user='datadog{}{}'.format(auth.upper(), priv.upper()),
                auth=self.AUTH_PROTOCOLS[auth],
                auth_key=self.AUTH_KEY,
                priv=self.PRIV_PROTOCOLS[priv],
                priv_key=self.PRIV_KEY
            )
        )


        self.run_check_n(config, repeat=3, sleep=2)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()


    def test_table_v3_SHA_AES(self):
        """
        Support SNMP V3 priv modes: SHA + AES
        """
        config = {
            'instances': []
        }

        # build multiple confgs
        auth = 'SHA'
        priv = 'AES'
        name = 'instance_{}_{}'.format(auth, priv)
        config['instances'].append(
            self.generate_v3_instance_config(
                self.TABULAR_OBJECTS,
                name=name,
                user='datadog{}{}'.format(auth.upper(), priv.upper()),
                auth=self.AUTH_PROTOCOLS[auth],
                auth_key=self.AUTH_KEY,
                priv=self.PRIV_PROTOCOLS[priv],
                priv_key=self.PRIV_KEY
            )
        )


        self.run_check_n(config, repeat=3, sleep=2)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for symbol in self.TABULAR_OBJECTS[0]['symbols']:
            metric_name = "snmp." + symbol
            self.assertMetric(metric_name, at_least=1)
            self.assertMetricTag(metric_name, self.CHECK_TAGS[0], at_least=1)

            for mtag in self.TABULAR_OBJECTS[0]['metric_tags']:
                tag = mtag['tag']
                self.assertMetricTagPrefix(metric_name, tag, at_least=1)

        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()


    def test_invalid_metric(self):
        """
        Invalid metrics raise a Warning and a critical service check
        """
        config = {
            'instances': [self.generate_instance_config(self.INVALID_METRICS)]
        }
        self.run_check(config)

        self.warnings = self.wait_for_async('get_warnings', 'warnings', 1, RESULTS_TIMEOUT)
        self.assertWarning("Fail to collect some metrics: No symbol IF-MIB::noIdeaWhatIAmDoingHere",
                           count=1, exact_match=False)

        # # Test service check
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.CRITICAL,
                                tags=self.CHECK_TAGS, count=1)
        self.coverage_report()

    def test_forcedtype_metric(self):
        """
        Forced Types should be reported as metrics of the forced type
        """
        config = {
            'instances': [self.generate_instance_config(self.FORCED_METRICS)]
        }
        self.run_check_twice(config)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        for metric in self.FORCED_METRICS:
            metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
            if metric.get('forced_type') == MetricTypes.COUNTER:
                # rate will be flushed as a gauge, so count should be 0.
                self.assertMetric(metric_name, tags=self.CHECK_TAGS,
                                  count=0, metric_type=MetricTypes.GAUGE)
            elif metric.get('forced_type') == MetricTypes.GAUGE:
                self.assertMetric(metric_name, tags=self.CHECK_TAGS,
                                  count=1, metric_type=MetricTypes.GAUGE)

        # # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK,
                                tags=self.CHECK_TAGS, at_least=1)
        self.coverage_report()

    def test_invalid_forcedtype_metric(self):
        """
        If a forced type is invalid a warning should be issued + a service check
        should be available
        """
        config = {
            'instances': [self.generate_instance_config(self.INVALID_FORCED_METRICS)]
        }

        self.run_check(config)

        self.warnings = self.wait_for_async('get_warnings', 'warnings', 1, RESULTS_TIMEOUT)
        self.assertWarning("Invalid forced-type specified:", count=1, exact_match=False)

        # # Test service check
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.CRITICAL,
                                tags=self.CHECK_TAGS, count=1)
        self.coverage_report()

    def test_scalar_with_tags(self):
        """
        Support SNMP scalar objects with tags
        """
        config = {
            'instances': [self.generate_instance_config(self.SCALAR_OBJECTS_WITH_TAGS)]
        }
        self.run_check_n(config, repeat=3)
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)

        # Test metrics
        for metric in self.SCALAR_OBJECTS_WITH_TAGS:
            metric_name = "snmp." + (metric.get('name') or metric.get('symbol'))
            tags = self.CHECK_TAGS + metric.get('metric_tags')
            self.assertMetric(metric_name, tags=tags, count=1)
        # Test service check
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.OK, tags=self.CHECK_TAGS, at_least=1)

        self.coverage_report()

    def test_network_failure(self):
        """
        Network failure is reported in service check
        """
        instance = self.generate_instance_config(self.SCALAR_OBJECTS)

        # Change port so connection will fail
        instance['port'] = 162

        config = {
            'instances': [instance]
        }
        self.run_check(config)
        self.warnings = self.wait_for_async('get_warnings', 'warnings', 1, RESULTS_TIMEOUT)

        self.assertWarning("No SNMP response received before timeout for instance localhost", count=1)

        # Test service check
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1, RESULTS_TIMEOUT)
        self.assertServiceCheck("snmp.can_check", status=AgentCheck.CRITICAL,
                                tags=self.CHECK_TAGS, count=1)

        self.coverage_report()
