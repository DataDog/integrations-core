# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
SCRUBBED_VALUE = '*****'
SCRUBBED_GLOBS = (
    'github.token',
    'github.user_fetch_command',
    'github.token_fetch_command',
    'pypi.auth',
    'pypi.auth_fetch_command',
    'trello.token',
    'trello.key_fetch_command',
    'trello.token_fetch_command',
    'orgs.*.api_key',
    'orgs.*.app_key',
    'orgs.*.api_key_fetch_command',
    'orgs.*.app_key_fetch_command',
    'dynamicd.llm_api_key',
    'dynamicd.llm_api_key_fetch_command',
)
TOP_LEVEL_SCRUB_KEYS = {
    'github': ('token', 'user_fetch_command', 'token_fetch_command'),
    'pypi': ('auth', 'auth_fetch_command'),
    'trello': ('token', 'key_fetch_command', 'token_fetch_command'),
    'dynamicd': ('llm_api_key', 'llm_api_key_fetch_command'),
}
ORG_SCRUB_KEYS = ('api_key', 'app_key', 'api_key_fetch_command', 'app_key_fetch_command')


def _scrub_keys(mapping: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in mapping:
            mapping[key] = SCRUBBED_VALUE


def scrub_config(config: dict):
    for section, keys in TOP_LEVEL_SCRUB_KEYS.items():
        section_data = config.get(section, {})
        if isinstance(section_data, dict):
            _scrub_keys(section_data, keys)

    orgs = config.get('orgs', {})
    if isinstance(orgs, dict):
        for org_data in orgs.values():
            if isinstance(org_data, dict):
                _scrub_keys(org_data, ORG_SCRUB_KEYS)
