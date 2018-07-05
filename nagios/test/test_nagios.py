# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import tempfile
import time
import pytest

from datadog_checks.nagios import Nagios
from .common import (
    CHECK_NAME, CUSTOM_TAGS, NAGIOS_TEST_LOG, NAGIOS_TEST_HOST, NAGIOS_TEST_ALT_HOST_TEMPLATE,
    NAGIOS_TEST_HOST_TEMPLATE, NAGIOS_TEST_SVC, NAGIOS_TEST_SVC_TEMPLATE, NAGIOS_TEST_ALT_SVC_TEMPLATE,
)


@pytest.mark.integration
class TestEventLogTailer:
    def test_line_parser(self, aggregator):
        """
        Parse lines
        """

        # Get the config
        config, nagios_cfg = get_config("log_file={}\n".format(NAGIOS_TEST_LOG), events=True)

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        nagios_tailer = nagios.nagios_tails[nagios_cfg.name][0]
        counters = {}

        for line in open(NAGIOS_TEST_LOG).readlines():
            parsed = nagios_tailer._parse_line(line)
            if parsed:
                event = aggregator.events[-1]
                t = event["event_type"]
                assert t in line
                assert int(event["timestamp"]) > 0, line
                assert event["host"] is not None, line
                counters[t] = counters.get(t, 0) + 1

                if t == "SERVICE ALERT":
                    assert event["event_soft_hard"] in ("SOFT", "HARD"), line
                    assert event["event_state"] in ("CRITICAL", "WARNING", "UNKNOWN", "OK"), line
                    assert event["check_name"] is not None
                elif t == "SERVICE NOTIFICATION":
                    assert event["event_state"] in (
                        "ACKNOWLEDGEMENT",
                        "OK",
                        "CRITICAL",
                        "WARNING",
                        "ACKNOWLEDGEMENT (CRITICAL)",
                    ), line
                elif t == "SERVICE FLAPPING ALERT":
                    assert event["flap_start_stop"] in ("STARTED", "STOPPED"), line
                    assert event["check_name"] is not None
                elif t == "ACKNOWLEDGE_SVC_PROBLEM":
                    assert event["check_name"] is not None
                    assert event["ack_author"] is not None
                    assert int(event["sticky_ack"]) >= 0
                    assert int(event["notify_ack"]) >= 0
                elif t == "ACKNOWLEDGE_HOST_PROBLEM":
                    assert event["ack_author"] is not None
                    assert int(event["sticky_ack"]) >= 0
                    assert int(event["notify_ack"]) >= 0
                elif t == "HOST DOWNTIME ALERT":
                    assert event["host"] is not None
                    assert event["downtime_start_stop"] in ("STARTED", "STOPPED")

        assert counters["SERVICE ALERT"] == 301
        assert counters["SERVICE NOTIFICATION"] == 120
        assert counters["HOST ALERT"] == 3
        assert counters["SERVICE FLAPPING ALERT"] == 7
        assert counters["CURRENT HOST STATE"] == 8
        assert counters["CURRENT SERVICE STATE"] == 52
        assert counters["SERVICE DOWNTIME ALERT"] == 3
        assert counters["HOST DOWNTIME ALERT"] == 5
        assert counters["ACKNOWLEDGE_SVC_PROBLEM"] == 4
        assert "ACKNOWLEDGE_HOST_PROBLEM" not in counters

    def test_continuous_bulk_parsing(self, aggregator):
        """
        Make sure the tailer continues to parse nagios as the file grows
        """
        test_data = open(NAGIOS_TEST_LOG).read()
        ITERATIONS = 1
        log_file = tempfile.NamedTemporaryFile(mode="a+b")

        # Get the config
        config, nagios_cfg = get_config("log_file={}\n".format(log_file.name), events=True)

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        for i in range(ITERATIONS):
            log_file.write(test_data)
            log_file.flush()
            nagios.check(config['instances'][0])

        log_file.close()
        assert len(aggregator.events) == ITERATIONS * 503


@pytest.mark.integration
class TestPerfDataTailer:
    POINT_TIME = (int(time.time()) / 15) * 15

    DB_LOG_SERVICEPERFDATA = [
        "time=0.06",
        "db0=33;180;190;0;200",
        "db1=1;150;190;0;200",
        "db2=0;120;290;1;200",
        "db3=0;110;195;5;100"
    ]

    DB_LOG_DATA = [
        "DATATYPE::SERVICEPERFDATA",
        "TIMET::{}".format(POINT_TIME),
        "HOSTNAME::myhost0",
        "SERVICEDESC::Pgsql Backends",
        "SERVICEPERFDATA::" + " ".join(DB_LOG_SERVICEPERFDATA),
        "SERVICECHECKCOMMAND::check_nrpe_1arg!check_postgres_backends",
        "HOSTSTATE::UP",
        "HOSTSTATETYPE::HARD",
        "SERVICESTATE::OK",
        "SERVICESTATETYPE::HARD",
    ]

    DISK_LOG_SERVICEPERFDATA = [
        "/=5477MB;6450;7256;0;8063",
        "/dev=0MB;2970;3341;0;3713",
        "/dev/shm=0MB;3080;3465;0;3851",
        "/var/run=0MB;3080;3465;0;3851",
        "/var/lock=0MB;3080;3465;0;3851",
        "/lib/init/rw=0MB;3080;3465;0;3851",
        "/mnt=290MB;338636;380966;0;423296",
        "/data=39812MB;40940;46057;0;51175",
    ]

    DISK_LOG_DATA = [
        "DATATYPE::SERVICEPERFDATA",
        "TIMET::{}".format(POINT_TIME),
        "HOSTNAME::myhost2",
        "SERVICEDESC::Disk Space",
        "SERVICEPERFDATA::" + " ".join(DISK_LOG_SERVICEPERFDATA),
        "SERVICECHECKCOMMAND::check_all_disks!20%!10%",
        "HOSTSTATE::UP",
        "HOSTSTATETYPE::HARD",
        "SERVICESTATE::OK",
        "SERVICESTATETYPE::HARD",
    ]

    HOST_LOG_SERVICEPERFDATA = ["rta=0.978000ms;5000.000000;5000.000000;0.000000", "pl=0%;100;100;0"]

    HOST_LOG_DATA = [
        "DATATYPE::HOSTPERFDATA",
        "TIMET::{}".format(POINT_TIME),
        "HOSTNAME::myhost1",
        "HOSTPERFDATA::" + " ".join(HOST_LOG_SERVICEPERFDATA),
        "HOSTCHECKCOMMAND::check-host-alive",
        "HOSTSTATE::UP",
        "HOSTSTATETYPE::HARD",
    ]

    def test_service_perfdata(self, aggregator):
        """
        Collect Nagios Service PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()

        # Get the config
        config, _ = get_config(
            "service_perfdata_file={}\n"
            "service_perfdata_file_template={}".format(self.log_file.name, NAGIOS_TEST_SVC_TEMPLATE),
            service_perf=True,
            tags=CUSTOM_TAGS,
        )

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        # Write content to log file and run check
        self._write_log('\t'.join(self.DB_LOG_DATA))
        nagios.check(config['instances'][0])

        # Test metrics
        for metric_data in self.DB_LOG_SERVICEPERFDATA:
            name, info = metric_data.split("=")
            metric_name = "nagios.pgsql_backends." + name

            values = info.split(";")
            value = float(values[0])
            expected_tags = list(CUSTOM_TAGS)
            if len(values) == 5:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])
                expected_tags.append('max:' + values[4])
            aggregator.assert_metric(metric_name, value=value, tags=expected_tags, count=1)

        aggregator.assert_all_metrics_covered()

    def test_service_perfdata_special_cases(self, aggregator):
        """
        Handle special cases in PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()
        # Get the config
        config, _ = get_config(
            "service_perfdata_file={}\n"
            "service_perfdata_file_template={}".format(self.log_file.name, NAGIOS_TEST_SVC_TEMPLATE),
            service_perf=True,
            tags=CUSTOM_TAGS,
        )

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        # Write content to log file and run check
        self._write_log('\t'.join(self.DISK_LOG_DATA))
        nagios.check(config['instances'][0])

        # Test metrics
        for metric_data in self.DISK_LOG_SERVICEPERFDATA:
            name, info = metric_data.split("=")
            values = info.split(";")
            value = int(values[0][:-2])
            expected_tags = ['unit:{}'.format(values[0][-2:]), 'device:{}'.format(name)] + CUSTOM_TAGS
            if len(values) == 5:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])
                expected_tags.append('max:' + values[4])

            aggregator.assert_metric("nagios.disk_space", value=value, tags=expected_tags, count=1)

        aggregator.assert_all_metrics_covered()

    def test_host_perfdata(self, aggregator):
        """
        Collect Nagios Host PerfData metrics
        """
        self.log_file = tempfile.NamedTemporaryFile()

        # Get the config
        config, _ = get_config(
            "host_perfdata_file={}\n"
            "host_perfdata_file_template={}".format(self.log_file.name, NAGIOS_TEST_HOST_TEMPLATE),
            host_perf=True,
            tags=CUSTOM_TAGS,
        )

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        # Write content to log file and run check
        self._write_log('\t'.join(self.HOST_LOG_DATA))
        nagios.check(config['instances'][0])

        # Test metric
        for metric_data in self.HOST_LOG_SERVICEPERFDATA:
            name, info = metric_data.split("=")
            metric_name = "nagios.host." + name

            values = info.split(";")

            index = values[0].find("ms") if values[0].find("ms") != -1 else values[0].find("%")
            index = len(values[0]) - index
            value = float(values[0][:-index])
            expected_tags = ['unit:' + values[0][-index:]] + CUSTOM_TAGS
            if len(values) == 4:
                expected_tags.append('warn:' + values[1])
                expected_tags.append('crit:' + values[2])
                expected_tags.append('min:' + values[3])

            aggregator.assert_metric(metric_name, value=value, tags=expected_tags, count=1)

        aggregator.assert_all_metrics_covered()

    def test_alt_service_perfdata(self, aggregator):
        """
        Collect Nagios Service PerfData metrics - alternative template
        """
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()

        # Get the config
        config, _ = get_config(
            "service_perfdata_file={}\n"
            "service_perfdata_file_template={}".format(perfdata_file.name, NAGIOS_TEST_ALT_SVC_TEMPLATE),
            service_perf=True,
        )

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        with open(NAGIOS_TEST_SVC, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        nagios.check(config['instances'][0])

        # Test metrics
        expected_metrics = [
            {
                'name': 'nagios.current_users.users',
                'timestamp': 1339511440,
                'value': 1.0,
                'hostname': 'localhost',
                'tags': ['warn:20', 'crit:50', 'min:0'],
            },
            {
                'name': 'nagios.ping.pl',
                'timestamp': 1339511500,
                'value': 0.0,
                'hostname': 'localhost',
                'tags': ['unit:%', 'warn:20', 'crit:60', 'min:0'],
            },
            {
                'name': 'nagios.ping.rta',
                'timestamp': 1339511500,
                'value': 0.065,
                'hostname': 'localhost',
                'tags': ['unit:ms', 'warn:100.000000', 'crit:500.000000', 'min:0.000000'],
            },
            {
                'name': 'nagios.root_partition',
                'timestamp': 1339511560,
                'value': 2470.0,
                'hostname': 'localhost',
                'tags': ['unit:MB', 'warn:5852', 'crit:6583', 'min:0', 'max:7315', 'device:/'],
            },
        ]

        for metric in expected_metrics:
            aggregator.assert_metric(metric['name'], metric['value'], tags=metric['tags'], hostname=metric['hostname'])

        aggregator.assert_all_metrics_covered()

    def test_alt_host_perfdata(self, aggregator):
        """
        Collect Nagios Host PerfData metrics - alternative template
        """
        self.log_file = tempfile.NamedTemporaryFile()
        perfdata_file = tempfile.NamedTemporaryFile()

        # Get the config
        config, _ = get_config(
            "host_perfdata_file={}\n"
            "host_perfdata_file_template={}".format(perfdata_file.name, NAGIOS_TEST_ALT_HOST_TEMPLATE),
            host_perf=True,
        )

        # Set up the check
        nagios = Nagios(CHECK_NAME, {}, {}, config['instances'])

        # Run the check once
        nagios.check(config['instances'][0])

        with open(NAGIOS_TEST_HOST, "r") as f:
            nagios_perf = f.read()

        perfdata_file.write(nagios_perf)
        perfdata_file.flush()

        nagios.check(config['instances'][0])

        # Test metrics
        expected_metrics = [
            {
                'name': 'nagios.host.pl',
                'timestamp': 1339511440,
                'value': 0.0,
                'hostname': 'localhost',
                'tags': ['unit:%', 'warn:80', 'crit:100', 'min:0'],
            },
            {
                'name': 'nagios.host.rta',
                'timestamp': 1339511440,
                'value': 0.048,
                'hostname': 'localhost',
                'tags': ['unit:ms', 'warn:3000.000000', 'crit:5000.000000', 'min:0.000000'],
            },
        ]

        for metric in expected_metrics:
            aggregator.assert_metric(metric['name'], metric['value'], tags=metric['tags'], hostname=metric['hostname'])

        aggregator.assert_all_metrics_covered()

    def _write_log(self, log_data):
        """
        Write log data to log file
        """
        self.log_file.write(log_data + "\n")
        self.log_file.flush()


def get_config(nagios_conf, events=False, service_perf=False, host_perf=False, tags=None):
    """
    Helper to generate a valid Nagios configuration
    """
    tags = [] if tags is None else tags

    NAGIOS_CFG = tempfile.NamedTemporaryFile(mode="a+b")
    NAGIOS_CFG.write(nagios_conf)
    NAGIOS_CFG.flush()

    CONFIG = {
        'instances': [
            {
                'nagios_conf': NAGIOS_CFG.name,
                'collect_events': events,
                'collect_service_performance_data': service_perf,
                'collect_host_performance_data': host_perf,
                'tags': list(tags),
            }
        ]
    }

    return CONFIG, NAGIOS_CFG
