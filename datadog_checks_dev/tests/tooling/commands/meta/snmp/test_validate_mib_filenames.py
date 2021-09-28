# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

MIB_CONTENT_WITH_COMMENT_HEADER = '''-- *****************************************************************
-- JNX-IF-CAPABILITY.mib: Juniper IF-MIB AGENT-CAPABILITIES
--
-- Copyright (c) 2013, Juniper Networks, Inc.
-- All rights reserved.
--
-- *****************************************************************

JNX-IF-CAPABILITY DEFINITIONS ::= BEGIN
'''

MIB_CONTENT = 'JNX-IF-CAPABILITY DEFINITIONS ::= BEGIN'


def test__extract_mib_name_from_mib_file():
    from datadog_checks.dev.tooling.commands.meta.snmp.validate_mib_filenames import _extract_mib_name

    assert _extract_mib_name(MIB_CONTENT) == 'JNX-IF-CAPABILITY'


def test__extract_mib_name_from_mib_file_with_header():
    from datadog_checks.dev.tooling.commands.meta.snmp.validate_mib_filenames import _extract_mib_name

    assert _extract_mib_name(MIB_CONTENT_WITH_COMMENT_HEADER) == 'JNX-IF-CAPABILITY'
