from fnmatch import fnmatch

from ddev.config.utils import SCRUBBED_GLOBS, SCRUBBED_VALUE, scrub_config

SECRET_FIELD_PATHS = {
    'github.user_command',
    'github.token',
    'github.token_command',
    'pypi.auth',
    'pypi.auth_command',
    'trello.key',
    'trello.key_command',
    'trello.token',
    'trello.token_command',
    'dynamicd.llm_api_key',
    'dynamicd.llm_api_key_command',
    'orgs.default.api_key',
    'orgs.default.api_key_command',
    'orgs.default.app_key',
    'orgs.default.app_key_command',
}


def test_secret_field_paths_are_registered_in_scrubbed_globs():
    missing_paths = {
        field_path for field_path in SECRET_FIELD_PATHS if not any(fnmatch(field_path, glob) for glob in SCRUBBED_GLOBS)
    }

    assert missing_paths == set()


def test_scrub_config_covers_registered_secret_paths():
    config = {
        'github': {
            'token': 'gh-token',
            'token_command': 'python github_token.py',
            'user_command': 'python github_user.py',
        },
        'pypi': {'auth': 'pypi-auth', 'auth_command': 'python pypi_auth.py'},
        'trello': {
            'key': 'trello-key',
            'key_command': 'python trello_key.py',
            'token': 'trello-token',
            'token_command': 'python trello_token.py',
        },
        'dynamicd': {
            'llm_api_key': 'llm-api-key',
            'llm_api_key_command': 'python dynamicd_key.py',
        },
        'orgs': {
            'default': {
                'api_key': 'dd-api-key',
                'api_key_command': 'python dd_api_key.py',
                'app_key': 'dd-app-key',
                'app_key_command': 'python dd_app_key.py',
            }
        },
        'repos': {'core': '/tmp/core'},
    }

    scrub_config(config)

    assert config['github']['token'] == SCRUBBED_VALUE
    assert config['github']['token_command'] == SCRUBBED_VALUE
    assert config['github']['user_command'] == SCRUBBED_VALUE
    assert config['pypi']['auth'] == SCRUBBED_VALUE
    assert config['pypi']['auth_command'] == SCRUBBED_VALUE
    assert config['trello']['key'] == SCRUBBED_VALUE
    assert config['trello']['key_command'] == SCRUBBED_VALUE
    assert config['trello']['token'] == SCRUBBED_VALUE
    assert config['trello']['token_command'] == SCRUBBED_VALUE
    assert config['dynamicd']['llm_api_key'] == SCRUBBED_VALUE
    assert config['dynamicd']['llm_api_key_command'] == SCRUBBED_VALUE
    assert config['orgs']['default']['api_key'] == SCRUBBED_VALUE
    assert config['orgs']['default']['api_key_command'] == SCRUBBED_VALUE
    assert config['orgs']['default']['app_key'] == SCRUBBED_VALUE
    assert config['orgs']['default']['app_key_command'] == SCRUBBED_VALUE

    assert config['repos']['core'] == '/tmp/core'
