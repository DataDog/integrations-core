# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from xml.etree import ElementTree as ET

from datadog_checks.pan_firewall.interface_config import InterfaceConfig, parse_interface_config

from .common import FIXTURES, SYNTHETIC
from .helpers import load_xml

SYNTHETIC_CONFIG = SYNTHETIC / 'config_running_interface_set.xml'


def test_interface_config_of_the_synthetic_set():
    config = parse_interface_config(load_xml(SYNTHETIC_CONFIG))

    # `ethernet1/2.20` and the `ip/entry` elements have neither setting, so they are not listed.
    assert config == {
        'ethernet1/1': InterfaceConfig(comment='Uplink & <ISP> — São Paulo', link_state='up'),
        'ethernet1/1.10': InterfaceConfig(comment='Guest VLAN'),
        'ethernet1/2': InterfaceConfig(link_state='down'),
        'ae1': InterfaceConfig(comment='LACP to core'),
        'loopback.1': InterfaceConfig(comment='router-id'),
        'tunnel.3': InterfaceConfig(comment='to DC2'),
    }


def test_blank_comment_is_no_description():
    assert parse_interface_config(load_xml(SYNTHETIC_CONFIG))['ethernet1/2'].comment is None


def test_lab_capture_has_no_settings():
    # PAN-OS leaves defaults out: the lab sets no comment and no link-state.
    assert parse_interface_config(load_xml(FIXTURES / 'fw-a-probe' / 'config_running_interface.xml')) == {}


def test_reply_without_an_interface_subtree_is_empty():
    assert parse_interface_config(ET.fromstring('<response status="success"><result/></response>')) == {}
