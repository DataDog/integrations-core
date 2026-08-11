# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.config.utils import SCRUBBED_VALUE, scrub_config


@pytest.fixture
def full_config():
    return {
        'orgs': {
            'a': {'api_key': 'A', 'app_key': 'B'},
            'b': {'api_key': 'C'},
        },
        'github': {'token': 'gh-secret'},
        'pypi': {'auth': 'pypi-secret'},
        'trello': {'token': 'trello-secret'},
        'ai': {'anthropic_api_key': 'sk-test'},
    }


def test_scrub_wildcard_siblings(full_config):
    scrub_config(full_config)

    assert full_config['orgs']['a']['api_key'] == SCRUBBED_VALUE
    assert full_config['orgs']['a']['app_key'] == SCRUBBED_VALUE
    assert full_config['orgs']['b']['api_key'] == SCRUBBED_VALUE


def test_scrub_top_level_secrets(full_config):
    scrub_config(full_config)

    assert full_config['github']['token'] == SCRUBBED_VALUE
    assert full_config['pypi']['auth'] == SCRUBBED_VALUE
    assert full_config['trello']['token'] == SCRUBBED_VALUE
    assert full_config['ai']['anthropic_api_key'] == SCRUBBED_VALUE


def test_scrub_non_secret_fields_untouched(full_config):
    full_config['orgs']['a']['site'] = 'datadoghq.com'
    scrub_config(full_config)

    assert full_config['orgs']['a']['site'] == 'datadoghq.com'


def test_scrub_missing_org_keys_does_not_crash():
    config = {'orgs': {'a': {'api_key': 'A'}}}
    scrub_config(config)

    assert config['orgs']['a']['api_key'] == SCRUBBED_VALUE


def test_scrub_non_dict_org_value_does_not_crash():
    config = {'orgs': {'bad': 'text'}}
    scrub_config(config)

    assert config['orgs']['bad'] == 'text'


def test_scrub_mixed_dict_and_non_dict_org_values():
    config = {'orgs': {'a': {'api_key': 'A'}, 'b': 'text'}}
    scrub_config(config)

    assert config['orgs']['a']['api_key'] == SCRUBBED_VALUE
    assert config['orgs']['b'] == 'text'


def test_scrub_missing_top_level_section_does_not_crash():
    scrub_config({})


def test_scrub_missing_nested_section_does_not_crash():
    scrub_config({'github': {}})
    scrub_config({'orgs': {}})


def test_scrub_already_empty_string():
    config = {'github': {'token': ''}}
    scrub_config(config)

    assert config['github']['token'] == SCRUBBED_VALUE
