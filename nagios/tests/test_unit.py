# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import tempfile

import pytest
from mock import MagicMock

from datadog_checks.nagios import NagiosCheck
from datadog_checks.nagios.nagios import (
    InvalidDataTemplate,
    NagiosEventLogTailer,
    NagiosPerfDataTailer,
    _get_host_metric_prefix,
    _get_service_metric_prefix,
)

from .common import CHECK_NAME, CUSTOM_TAGS, NAGIOS_TEST_HOST_TEMPLATE, NAGIOS_TEST_LOG, NAGIOS_TEST_SVC_TEMPLATE

pytestmark = pytest.mark.unit


def test_centreon_event_logs():
    log = (
        "[1571848012] [53365] SERVICE ALERT: SOMEHOST;Current Anonymous Users;CRITICAL;SOFT;1;"
        "CHECK_NRPE: Socket timeout after 60 seconds."
    )
    events = []
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, mock_log, "host", events.append, None, False)
    tailer.parse_line(log)
    assert len(events) == 1
    assert events[0]['event_type'] == 'SERVICE ALERT'
    assert events[0]['host'] == 'SOMEHOST'


def write_temp_file(content=""):
    f = tempfile.NamedTemporaryFile(mode="w+")
    f.write(content)
    f.flush()
    return f


def write_config_file(*lines):
    return write_temp_file("\n".join(lines) + "\n")


def build_service_perfdata_line(servicedesc, perfdata, hostname="myhost"):
    fields = [
        "DATATYPE::SERVICEPERFDATA",
        "TIMET::1339511440",
        "HOSTNAME::{}".format(hostname),
        "SERVICEDESC::{}".format(servicedesc),
        "SERVICEPERFDATA::{}".format(perfdata),
        "SERVICECHECKCOMMAND::check_x",
        "HOSTSTATE::UP",
        "HOSTSTATETYPE::HARD",
        "SERVICESTATE::OK",
        "SERVICESTATETYPE::HARD",
    ]
    return "\t".join(fields)


def make_service_perfdata_check(tags=None):
    perf_file = write_temp_file("")
    conf = write_config_file(
        "service_perfdata_file={}".format(perf_file.name),
        "service_perfdata_file_template={}".format(NAGIOS_TEST_SVC_TEMPLATE),
    )
    instance = {
        'nagios_conf': conf.name,
        'collect_events': False,
        'collect_host_performance_data': False,
        'collect_service_performance_data': True,
        'tags': list(tags) if tags else [],
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    return check, instance, perf_file


# --- NagiosCheck.__init__ instance/config selection ---


def test_init_uses_only_the_first_instance():
    # Kills core/NumberReplacer mutants at nagios.py:78 (self.instances[0] -> [1] / [-1]).
    log_a = write_temp_file("")
    log_b = write_temp_file("")
    instance_a = {'nagios_log': log_a.name, 'collect_events': False}
    instance_b = {'nagios_log': log_b.name, 'collect_events': False}
    check = NagiosCheck(CHECK_NAME, {}, [instance_a, instance_b])
    assert log_a.name in check.nagios_tails
    assert log_b.name not in check.nagios_tails


def test_init_nagios_conf_takes_precedence_over_perf_cfg():
    # Kills core/AddNot at nagios.py:84 ('nagios_conf' in instance branch selection).
    conf = write_config_file("log_file=/tmp/does-not-need-to-exist.log")
    perf_cfg = write_config_file("host_perfdata_file=/tmp/also-unused.log")
    instance = {
        'nagios_conf': conf.name,
        'nagios_perf_cfg': perf_cfg.name,
        'collect_events': False,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert conf.name in check.nagios_tails
    assert perf_cfg.name not in check.nagios_tails
    assert instance['collect_host_performance_data'] is False


def test_init_perf_cfg_branch_forces_performance_data_collection_on():
    # Kills core/ReplaceTrueWithFalse mutants at nagios.py:92-93 (retrocompat flags forced to True).
    perf_cfg = write_config_file("log_file=/tmp/does-not-need-to-exist.log")
    instance = {
        'nagios_perf_cfg': perf_cfg.name,
        'collect_events': False,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    NagiosCheck(CHECK_NAME, {}, [instance])
    assert instance['collect_host_performance_data'] is True
    assert instance['collect_service_performance_data'] is True


def test_init_conf_instance_key_takes_precedence_over_nagios_log():
    # Kills core mutants at nagios.py:95 (AddNot), :97 (Is_IsNot/AddNot) and :100 (Delete_Not/AddNot).
    conf = write_config_file("unrelated_key=1")
    log_file = write_temp_file("")
    instance = {
        'nagios_conf': conf.name,
        'nagios_log': log_file.name,
        'collect_events': False,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert conf.name in check.nagios_tails
    assert log_file.name not in check.nagios_tails


def test_init_creates_event_tailer_when_log_file_present_and_events_enabled_by_default():
    # Kills core/AddNot and core/ReplaceTrueWithFalse mutants at nagios.py:104 (log_file presence/default) and
    # core/ReplaceFalseWithTrue at nagios.py:113 (passive_checks default).
    log_file = write_temp_file("")
    conf = write_config_file("log_file={}".format(log_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    tailers = check.nagios_tails[conf.name]
    assert len(tailers) == 1
    assert isinstance(tailers[0], NagiosEventLogTailer)
    assert tailers[0]._passive_checks is False


def test_init_skips_event_tailer_when_log_file_key_is_missing():
    # Kills core/ReplaceAndWithOr at nagios.py:104 (log_file-present AND collect_events, not OR).
    conf = write_config_file("host_perfdata_file=/tmp/does-not-need-to-exist.log")
    instance = {
        'nagios_conf': conf.name,
        'collect_events': True,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert check.nagios_tails[conf.name] == []


def test_init_creates_host_perfdata_tailer_when_all_conditions_met():
    # Kills core/AddNot at nagios.py:116 (host_perfdata_file key presence check).
    perf_file = write_temp_file("")
    conf = write_config_file(
        "host_perfdata_file={}".format(perf_file.name),
        "host_perfdata_file_template={}".format(NAGIOS_TEST_HOST_TEMPLATE),
    )
    instance = {
        'nagios_conf': conf.name,
        'collect_events': False,
        'collect_host_performance_data': True,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    tailers = check.nagios_tails[conf.name]
    assert len(tailers) == 1
    assert tailers[0]._get_metric_prefix is _get_host_metric_prefix


def test_init_host_perfdata_tailer_requires_opt_in():
    # Kills core/ReplaceFalseWithTrue at nagios.py:119 (collect_host_performance_data default).
    perf_file = write_temp_file("")
    conf = write_config_file(
        "host_perfdata_file={}".format(perf_file.name),
        "host_perfdata_file_template={}".format(NAGIOS_TEST_HOST_TEMPLATE),
    )
    instance = {'nagios_conf': conf.name, 'collect_events': False, 'collect_service_performance_data': False}
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert check.nagios_tails[conf.name] == []


def test_init_host_perfdata_tailer_requires_both_file_and_template_keys():
    # Kills core/ReplaceAndWithOr mutants at nagios.py:117-118 (host_perfdata AND-chain).
    perf_file = write_temp_file("")
    conf = write_config_file("host_perfdata_file={}".format(perf_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_events': False,
        'collect_host_performance_data': True,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert check.nagios_tails[conf.name] == []


def test_init_creates_service_perfdata_tailer_when_all_conditions_met():
    # Kills core/AddNot at nagios.py:134 (service_perfdata_file key presence check).
    check, instance, _perf_file = make_service_perfdata_check()
    tailers = check.nagios_tails[instance['nagios_conf']]
    assert len(tailers) == 1
    assert tailers[0]._get_metric_prefix is _get_service_metric_prefix


def test_init_service_perfdata_tailer_requires_opt_in():
    # Kills core/ReplaceFalseWithTrue at nagios.py:137 (collect_service_performance_data default).
    perf_file = write_temp_file("")
    conf = write_config_file(
        "service_perfdata_file={}".format(perf_file.name),
        "service_perfdata_file_template={}".format(NAGIOS_TEST_SVC_TEMPLATE),
    )
    instance = {'nagios_conf': conf.name, 'collect_events': False, 'collect_host_performance_data': False}
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert check.nagios_tails[conf.name] == []


def test_init_service_perfdata_tailer_requires_both_file_and_template_keys():
    # Kills core/ReplaceAndWithOr mutants at nagios.py:135-136 (service_perfdata AND-chain).
    perf_file = write_temp_file("")
    conf = write_config_file("service_perfdata_file={}".format(perf_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_events': False,
        'collect_host_performance_data': False,
        'collect_service_performance_data': True,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    assert check.nagios_tails[conf.name] == []


# --- NagiosCheck.parse_nagios_config ---


def test_parse_nagios_config_extracts_matching_keys():
    # Kills core/ZeroIterationForLoop mutants at nagios.py:160 and :164 and core/AddNot at nagios.py:166.
    check = NagiosCheck(CHECK_NAME, {}, [{}])
    conf = write_config_file("log_file=/tmp/somelog")
    result = check.parse_nagios_config(conf.name)
    assert result == {'log_file': '/tmp/somelog'}


def test_parse_nagios_config_skips_blank_lines_and_keeps_reading():
    # Kills core/ReplaceContinueWithBreak at nagios.py:163 (blank-line handling must not abort parsing).
    check = NagiosCheck(CHECK_NAME, {}, [{}])
    conf = write_config_file("", "log_file=/tmp/somelog")
    result = check.parse_nagios_config(conf.name)
    assert result == {'log_file': '/tmp/somelog'}


def test_parse_nagios_config_wraps_errors_reading_missing_file():
    # Kills core/ExceptionReplacer at nagios.py:169 (must catch and wrap the underlying file error).
    check = NagiosCheck(CHECK_NAME, {}, [{}])
    with pytest.raises(Exception, match="Could not parse Nagios config file"):
        check.parse_nagios_config("/nonexistent/path/to/nagios.cfg")


# --- NagiosCheck.check ---


def test_check_invokes_each_registered_tailer(aggregator):
    # Kills core/ZeroIterationForLoop at nagios.py:190 and core/Delete_Not/AddNot at nagios.py:188.
    log_file = write_temp_file("")
    conf = write_config_file("log_file={}".format(log_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    log_file.write("[1339511440] SERVICE ALERT: host;svc;OK;HARD;1;output\n")
    log_file.flush()
    check.check(instance)
    assert len(aggregator.events) == 1


def test_check_raises_when_instance_key_is_not_registered():
    # Kills core/ReplaceOrWithAnd at nagios.py:188 (must raise even when instance_key is truthy but unknown).
    log_file = write_temp_file("")
    conf = write_config_file("log_file={}".format(log_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    with pytest.raises(Exception, match="No Nagios configuration file specified"):
        check.check({'nagios_conf': '/some/other/unregistered.cfg'})


def test_check_recovers_when_tailed_file_is_temporarily_removed():
    # Kills core/ExceptionReplacer mutants at nagios.py:193 (RuntimeError/StopIteration must stay caught).
    log_file = write_temp_file("")
    conf = write_config_file("log_file={}".format(log_file.name))
    instance = {
        'nagios_conf': conf.name,
        'collect_host_performance_data': False,
        'collect_service_performance_data': False,
    }
    check = NagiosCheck(CHECK_NAME, {}, [instance])
    renamed_path = log_file.name + "_renamed"
    os.rename(log_file.name, renamed_path)
    try:
        check.check(instance)  # must not raise: the tailer should log and recover instead
    finally:
        os.rename(renamed_path, log_file.name)


# --- NagiosTailer base class ---


def test_tailer_starts_with_zero_lines_parsed():
    # Kills core/NumberReplacer mutants at nagios.py:209 (_line_parsed initial value).
    log_file = write_temp_file("")
    tailer = NagiosEventLogTailer(log_file.name, MagicMock(), "host", lambda e: None, [], False)
    assert tailer._line_parsed == 0


def test_tailer_check_resets_and_recounts_parsed_lines():
    # Kills core/NumberReplacer mutants at nagios.py:230 and :234 (increment step and reset value).
    log_file = write_temp_file("")
    tailer = NagiosEventLogTailer(log_file.name, MagicMock(), "host", lambda e: None, [], False)
    log_file.write("line1\nline2\nline3\n")
    log_file.flush()
    tailer.check()
    assert tailer._line_parsed == 3


def test_tailer_gen_starts_at_end_of_file_ignoring_preexisting_content():
    # Kills core/ReplaceTrueWithFalse at nagios.py:223 (move_end must skip content written before construction).
    log_file = write_temp_file("preexisting\n")
    tailer = NagiosEventLogTailer(log_file.name, MagicMock(), "host", lambda e: None, [], False)
    assert tailer._line_parsed == 0
    log_file.write("new\n")
    log_file.flush()
    tailer.check()
    assert tailer._line_parsed == 1


def test_tailer_gen_processes_all_pending_lines_in_a_single_pass():
    # Kills core/ReplaceFalseWithTrue at nagios.py:223 (line_by_line must not stop after only one matched line).
    log_file = write_temp_file("")
    events = []
    tailer = NagiosEventLogTailer(log_file.name, MagicMock(), "host", events.append, [], False)
    log_file.write(
        "[1339511440] SERVICE ALERT: host;svc;OK;HARD;1;out\n[1339511441] SERVICE ALERT: host;svc;OK;HARD;1;out\n"
    )
    log_file.flush()
    tailer.check()
    assert tailer._line_parsed == 2
    assert len(events) == 2


# --- NagiosEventLogTailer.parse_line / create_event ---


def test_parse_line_returns_false_for_unmatched_line():
    # Kills core/ReplaceFalseWithTrue at nagios.py:267 (no regex match must report no event found).
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, MagicMock(), "host", lambda e: None, None, False)
    assert tailer.parse_line("this line matches neither nagios log regex") is False


def test_parse_line_skips_passive_service_check_by_default():
    # Kills core mutants at nagios.py:273 (Delete_Not, ReplaceComparisonOperator_Eq_Is) and :274 (ReplaceFalseWithTrue).
    events = []
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, MagicMock(), "host", events.append, None, False)
    line = "[1339511440] PASSIVE SERVICE CHECK: host;svc;0;output"
    assert tailer.parse_line(line) is False
    assert events == []


def test_parse_line_processes_non_passive_event_types_normally():
    # Kills core/ReplaceComparisonOperator_Eq_Lt and _Eq_LtE mutants at nagios.py:273.
    events = []
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, MagicMock(), "host", events.append, None, False)
    line = "[1305832665] ACKNOWLEDGE_HOST_PROBLEM: host;1;1;0;author;comment"
    assert tailer.parse_line(line) is True
    assert len(events) == 1


def test_parse_line_logs_full_line_minus_trailing_char_for_unknown_event_type():
    # Kills core mutants at nagios.py:278 (unary/number ops on line[:-1]) and :279 (ReplaceFalseWithTrue).
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, mock_log, "host", lambda e: None, None, False)
    line = "[1339511440] TOTALLY UNKNOWN EVENT: a;b;c"
    assert tailer.parse_line(line) is False
    mock_log.warning.assert_called_once_with("Ignoring unknown nagios event for line: %s", line[:-1])


def test_parse_line_logs_full_line_minus_trailing_char_for_ignored_event_type():
    # Kills core mutants at nagios.py:282 (unary/number ops on line[:-1]) and :283 (ReplaceFalseWithTrue).
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, mock_log, "host", lambda e: None, None, False)
    line = "[1305832665] PROCESS_SERVICE_CHECK_RESULT: host;svc;0;comment"
    assert tailer.parse_line(line) is False
    mock_log.debug.assert_any_call("Ignoring Nagios event for line: %s", line[:-1])


def test_parse_line_returns_false_and_logs_on_malformed_event_fields():
    # Kills core/ExceptionReplacer at nagios.py:296 and core/ReplaceFalseWithTrue at nagios.py:298.
    events = []
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, mock_log, "host", events.append, None, False)
    line = "[1339511440] SERVICE ALERT: onlyonefield"
    assert tailer.parse_line(line) is False
    assert events == []
    mock_log.exception.assert_called_once()


def test_create_event_rewrites_localhost_to_configured_hostname():
    # Kills core/ReplaceComparisonOperator_Eq_Gt and _Eq_Is mutants at nagios.py:332.
    events = []
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, MagicMock(), "myhostname", events.append, None, False)
    line = "[1339511440] HOST ALERT: localhost;DOWN;HARD;1;output message"
    assert tailer.parse_line(line) is True
    assert events[0]['host'] == "myhostname"


def test_create_event_leaves_non_localhost_host_untouched():
    # Kills core/ReplaceComparisonOperator_Eq_GtE mutant at nagios.py:332.
    events = []
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, MagicMock(), "myhostname", events.append, None, False)
    line = "[1339511440] HOST ALERT: zzz-remote-host;DOWN;HARD;1;output message"
    assert tailer.parse_line(line) is True
    assert events[0]['host'] == "zzz-remote-host"


# --- NagiosPerfDataTailer ---


def test_compile_file_template_wraps_regex_errors():
    # Kills core/ExceptionReplacer at nagios.py:371 (compile error must be wrapped in InvalidDataTemplate).
    log_file = write_temp_file("")
    with pytest.raises(InvalidDataTemplate):
        NagiosPerfDataTailer(
            log_file.name,
            "$UNCLOSED(",
            MagicMock(),
            "host",
            lambda *a, **kw: None,
            [],
            'SERVICEPERFDATA',
            _get_service_metric_prefix,
        )


def test_perfdata_parse_line_ignores_lines_that_do_not_match_template():
    # Kills core/Delete_Not and core/AddNot at nagios.py:375 (non-matching line must be skipped, not processed).
    perf_file = write_temp_file("")
    tailer = NagiosPerfDataTailer(
        perf_file.name,
        NAGIOS_TEST_SVC_TEMPLATE,
        MagicMock(),
        "host",
        lambda *a, **kw: None,
        [],
        'SERVICEPERFDATA',
        _get_service_metric_prefix,
    )
    result = tailer.parse_line("this line does not match the configured template at all")
    assert result is None


def test_perfdata_parse_line_warns_when_perfdata_field_is_empty():
    # Kills core/Delete_Not and core/AddNot at nagios.py:385 (missing-perfdata-field warning branch).
    perf_file = write_temp_file("")
    mock_log = MagicMock()
    tailer = NagiosPerfDataTailer(
        perf_file.name,
        NAGIOS_TEST_SVC_TEMPLATE,
        mock_log,
        "host",
        lambda *a, **kw: None,
        [],
        'SERVICEPERFDATA',
        _get_service_metric_prefix,
    )
    tailer.parse_line(build_service_perfdata_line("My Service", ""))
    mock_log.warning.assert_called_once()


def test_perfdata_parse_line_skips_malformed_pair_and_continues_to_next(aggregator):
    # Kills core/AddNot at nagios.py:392 and core/ReplaceContinueWithBreak at nagios.py:393.
    check, instance, perf_file = make_service_perfdata_check(tags=CUSTOM_TAGS)
    perf_file.write(build_service_perfdata_line("My Service", "not-a-pair validmetric=7") + "\n")
    perf_file.flush()
    check.check(instance)
    aggregator.assert_metric("nagios.my_service.validmetric", value=7.0, tags=CUSTOM_TAGS, count=1)


def test_perfdata_metric_name_joins_prefix_and_label(aggregator):
    # Kills core/ReplaceBinaryOperator_Add_* mutants at nagios.py:411 (metric_prefix + [label]).
    check, instance, perf_file = make_service_perfdata_check(tags=CUSTOM_TAGS)
    perf_file.write(build_service_perfdata_line("My Service", "used=42") + "\n")
    perf_file.flush()
    check.check(instance)
    aggregator.assert_metric("nagios.my_service.used", value=42.0, tags=CUSTOM_TAGS, count=1)


def test_perfdata_metric_with_slash_label_uses_device_name_instead_of_suffix(aggregator):
    # Kills core/AddNot mutant at nagios.py:401 ('/' in label check for device-style labels).
    check, instance, perf_file = make_service_perfdata_check(tags=CUSTOM_TAGS)
    perf_file.write(build_service_perfdata_line("My Service", "/var=10") + "\n")
    perf_file.flush()
    check.check(instance)
    aggregator.assert_metric("nagios.my_service", value=10.0, tags=CUSTOM_TAGS + ["device:/var"], count=1)


def test_perfdata_metric_includes_optional_warn_crit_min_max_tags(aggregator):
    # Kills core/ZeroIterationForLoop at nagios.py:417 and core/AddNot/ReplaceAndWithOr at nagios.py:419.
    check, instance, perf_file = make_service_perfdata_check(tags=CUSTOM_TAGS)
    perf_file.write(build_service_perfdata_line("My Service", "latency=5;10;20;0;30") + "\n")
    perf_file.flush()
    check.check(instance)
    expected_tags = ["warn:10", "crit:20", "min:0", "max:30"] + CUSTOM_TAGS
    aggregator.assert_metric("nagios.my_service.latency", value=5.0, tags=expected_tags, count=1)


def test_perfdata_metric_omits_tags_for_present_but_empty_optional_fields(aggregator):
    # Kills core/ReplaceComparisonOperator_NotEq_GtE at nagios.py:419 (empty warn/min segments must stay untagged).
    check, instance, perf_file = make_service_perfdata_check(tags=CUSTOM_TAGS)
    perf_file.write(build_service_perfdata_line("My Service", "latency=5;;20;;30") + "\n")
    perf_file.flush()
    check.check(instance)
    expected_tags = ["crit:20", "max:30"] + CUSTOM_TAGS
    aggregator.assert_metric("nagios.my_service.latency", value=5.0, tags=expected_tags, count=1)
