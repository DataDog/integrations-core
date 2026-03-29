# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shlex
import sys

import pytest

from ddev.config.model import ConfigurationError, RootConfig, get_github_user
from ddev.config.secret_command import reset_secret_command_cache


@pytest.fixture(autouse=True)
def reset_secret_command_cache_between_tests():
    reset_secret_command_cache()
    yield
    reset_secret_command_cache()


def test_default(monkeypatch):
    monkeypatch.setenv('DD_GITHUB_TOKEN', 'default-token')
    config = RootConfig({})
    config.parse_fields()

    assert config.raw_data == {
        'repo': 'core',
        'agent': 'dev',
        'org': 'default',
        'repos': {
            'core': os.path.join('~', 'dd', 'integrations-core'),
            'extras': os.path.join('~', 'dd', 'integrations-extras'),
            'marketplace': os.path.join('~', 'dd', 'marketplace'),
            'agent': os.path.join('~', 'dd', 'datadog-agent'),
        },
        'agents': {
            'dev': {'docker': 'registry.datadoghq.com/agent-dev:master-py3', 'local': 'latest'},
            '7': {'docker': 'registry.datadoghq.com/agent:7', 'local': '7'},
        },
        'orgs': {
            'default': {
                'api_key': os.getenv('DD_API_KEY', ''),
                'app_key': os.getenv('DD_APP_KEY', ''),
                'site': os.getenv('DD_SITE', 'datadoghq.com'),
                'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
                'log_url': os.getenv('DD_LOGS_CONFIG_LOGS_DD_URL', ''),
            },
        },
        'github': {},
        'pypi': {
            'user': '',
            'auth': '',
        },
        'trello': {},
        'dynamicd': {},
        'terminal': {
            'styles': {
                'info': 'bold',
                'success': 'bold cyan',
                'error': 'bold red',
                'warning': 'bold yellow',
                'waiting': 'bold magenta',
                'debug': 'bold',
                'spinner': 'simpleDotsScrolling',
            },
        },
    }


class TestRepo:
    def test_default(self):
        config = RootConfig({})

        expected_path = os.path.join('~', 'dd', 'integrations-core')
        assert config.repo.name == config.repo.name == 'core'
        assert config.repo.path == config.repo.path == expected_path
        assert config.repo.raw_data == {'name': 'core', 'path': expected_path}

    def test_invalid_type(self, helpers):
        config = RootConfig({'repo': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo
                  must be a string"""
            ),
        ):
            _ = config.repo

    def test_defined(self):
        config = RootConfig({'repo': 'extras'})

        expected_path = os.path.join('~', 'dd', 'integrations-extras')
        assert config.repo.name == config.repo.name == 'extras'
        assert config.repo.path == config.repo.path == expected_path
        assert config.repo.raw_data == {'name': 'extras', 'path': expected_path}

    def test_unknown(self, helpers):
        config = RootConfig({'repo': 'foo'})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo
                  unknown Repository: 'foo'"""
            ),
        ):
            _ = config.repo

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.repo = 9000
        assert config.raw_data == {'repo': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo
                  must be a string"""
            ),
        ):
            _ = config.repo

    def test_name_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.repo.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo -> name
                  required field"""
            ),
        ):
            _ = config.repo.name

    def test_name_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.repo.name = 9000
        assert config.repo.raw_data == {'name': 9000, 'path': os.path.join('~', 'dd', 'integrations-core')}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo -> name
                  must be a string"""
            ),
        ):
            _ = config.repo.name

    def test_path_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.repo.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo -> path
                  required field"""
            ),
        ):
            _ = config.repo.path

    def test_path_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.repo.path = 9000
        assert config.repo.raw_data == {'name': 'core', 'path': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repo -> path
                  must be a string"""
            ),
        ):
            _ = config.repo.path


class TestAgent:
    def test_default(self):
        config = RootConfig({})

        agent_config = {'docker': 'registry.datadoghq.com/agent-dev:master-py3', 'local': 'latest'}
        assert config.agent.name == config.agent.name == 'dev'
        assert config.agent.config == config.agent.config == agent_config
        assert config.agent.raw_data == {'name': 'dev', 'config': agent_config}

    def test_invalid_type(self, helpers):
        config = RootConfig({'agent': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent
                  must be a string"""
            ),
        ):
            _ = config.agent

    def test_defined(self):
        config = RootConfig({'agent': '7'})

        agent_config = {'docker': 'registry.datadoghq.com/agent:7', 'local': '7'}
        assert config.agent.name == config.agent.name == '7'
        assert config.agent.config == config.agent.config == agent_config
        assert config.agent.raw_data == {'name': '7', 'config': agent_config}

    def test_unknown(self, helpers):
        config = RootConfig({'agent': 'foo'})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent
                  unknown Agent: 'foo'"""
            ),
        ):
            _ = config.agent

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.agent = 9000
        assert config.raw_data == {'agent': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent
                  must be a string"""
            ),
        ):
            _ = config.agent

    def test_name_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.agent.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent -> name
                  required field"""
            ),
        ):
            _ = config.agent.name

    def test_name_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.agent.name = 9000
        assert config.agent.raw_data == {
            'name': 9000,
            'config': {'docker': 'registry.datadoghq.com/agent-dev:master-py3', 'local': 'latest'},
        }

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent -> name
                  must be a string"""
            ),
        ):
            _ = config.agent.name

    def test_config_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.agent.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent -> config
                  required field"""
            ),
        ):
            _ = config.agent.config

    def test_config_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.agent.config = 9000
        assert config.agent.raw_data == {'name': 'dev', 'config': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agent -> config
                  must be a table"""
            ),
        ):
            _ = config.agent.config


class TestOrg:
    def test_default(self):
        config = RootConfig({})

        org_config = {
            'api_key': os.getenv('DD_API_KEY', ''),
            'app_key': os.getenv('DD_APP_KEY', ''),
            'site': os.getenv('DD_SITE', 'datadoghq.com'),
            'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
            'log_url': os.getenv('DD_LOGS_CONFIG_LOGS_DD_URL', ''),
        }
        assert config.org.name == config.org.name == 'default'
        assert config.org.config == config.org.config == org_config
        assert config.org.raw_data == {'name': 'default', 'config': org_config}

    def test_invalid_type(self, helpers):
        config = RootConfig({'org': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org
                  must be a string"""
            ),
        ):
            _ = config.org

    def test_defined(self):
        config = RootConfig({'org': 'foo', 'orgs': {'foo': {'bar': 'baz'}}})

        org_config = {'bar': 'baz'}
        assert config.org.name == config.org.name == 'foo'
        assert config.org.config == config.org.config == org_config
        assert config.org.raw_data == {'name': 'foo', 'config': org_config}

    def test_config_api_key_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_API_KEY', 'env-api-key')
        script_path = tmp_path / 'org_api_key.py'
        script_path.write_text("print('api-key-from-command')")

        config = RootConfig(
            {
                'orgs': {
                    'default': {
                        'api_key': 'literal-api-key',
                        'api_key_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                    }
                }
            }
        )

        assert config.org.config.get('api_key') == 'api-key-from-command'
        assert config.orgs['default'].get('api_key') == 'api-key-from-command'

    def test_config_app_key_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_APP_KEY', 'env-app-key')
        script_path = tmp_path / 'org_app_key.py'
        script_path.write_text("print('app-key-from-command')")

        config = RootConfig(
            {
                'orgs': {
                    'default': {
                        'app_key': 'literal-app-key',
                        'app_key_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                    }
                }
            }
        )

        assert config.org.config.get('app_key') == 'app-key-from-command'

    def test_unknown(self, helpers):
        config = RootConfig({'org': 'foo'})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org
                  unknown Org: 'foo'"""
            ),
        ):
            _ = config.org

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.org = 9000
        assert config.raw_data == {'org': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org
                  must be a string"""
            ),
        ):
            _ = config.org

    def test_name_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.org.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org -> name
                  required field"""
            ),
        ):
            _ = config.org.name

    def test_name_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.org.name = 9000
        assert config.org.raw_data == {
            'name': 9000,
            'config': {
                'api_key': os.getenv('DD_API_KEY', ''),
                'app_key': os.getenv('DD_APP_KEY', ''),
                'site': os.getenv('DD_SITE', 'datadoghq.com'),
                'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
                'log_url': os.getenv('DD_LOGS_CONFIG_LOGS_DD_URL', ''),
            },
        }

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org -> name
                  must be a string"""
            ),
        ):
            _ = config.org.name

    def test_config_set_lazy_error_missing(self, helpers):
        config = RootConfig({})

        config.org.raw_data = {}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org -> config
                  required field"""
            ),
        ):
            _ = config.org.config

    def test_config_set_lazy_error_not_string(self, helpers):
        config = RootConfig({})

        config.org.config = 9000
        assert config.org.raw_data == {'name': 'default', 'config': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org -> config
                  must be a table"""
            ),
        ):
            _ = config.org.config


class TestRepos:
    def test_default(self):
        config = RootConfig({})

        repos = {
            'core': os.path.join('~', 'dd', 'integrations-core'),
            'extras': os.path.join('~', 'dd', 'integrations-extras'),
            'marketplace': os.path.join('~', 'dd', 'marketplace'),
            'agent': os.path.join('~', 'dd', 'datadog-agent'),
        }
        assert config.repos == repos
        assert config.raw_data == {'repos': repos}

    def test_not_table(self, helpers):
        config = RootConfig({'repos': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repos
                  must be a table"""
            ),
        ):
            _ = config.repos

    def test_defined(self):
        config = RootConfig({'repos': {'foo': 'bar'}})

        repos = {'foo': 'bar'}
        assert config.repos == repos
        assert config.raw_data == {'repos': repos}

    def test_empty(self, helpers):
        config = RootConfig({'repos': {}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repos
                  must define at least one repository"""
            ),
        ):
            _ = config.repos

    def test_path_not_string(self, helpers):
        config = RootConfig({'repos': {'foo': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repos -> foo
                  must be a string"""
            ),
        ):
            _ = config.repos

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.repos = 9000
        assert config.raw_data == {'repos': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                repos
                  must be a table"""
            ),
        ):
            _ = config.repos


class TestAgents:
    def test_default(self):
        config = RootConfig({})

        agents = {
            'dev': {'docker': 'registry.datadoghq.com/agent-dev:master-py3', 'local': 'latest'},
            '7': {'docker': 'registry.datadoghq.com/agent:7', 'local': '7'},
        }
        assert config.agents == agents
        assert config.raw_data == {'agents': agents}

    def test_not_table(self, helpers):
        config = RootConfig({'agents': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agents
                  must be a table"""
            ),
        ):
            _ = config.agents

    def test_defined(self):
        config = RootConfig({'agents': {'foo': {'docker': 'bar', 'local': 'baz'}}})

        agents = {'foo': {'docker': 'bar', 'local': 'baz'}}
        assert config.agents == agents
        assert config.raw_data == {'agents': agents}

    def test_empty(self, helpers):
        config = RootConfig({'agents': {}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agents
                  must define at least one Agent"""
            ),
        ):
            _ = config.agents

    def test_config_not_table(self, helpers):
        config = RootConfig({'agents': {'foo': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agents -> foo
                  must be a table"""
            ),
        ):
            _ = config.agents

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.agents = 9000
        assert config.raw_data == {'agents': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                agents
                  must be a table"""
            ),
        ):
            _ = config.agents


class TestOrgs:
    def test_default(self):
        config = RootConfig({})

        orgs = {
            'default': {
                'api_key': os.getenv('DD_API_KEY', ''),
                'app_key': os.getenv('DD_APP_KEY', ''),
                'site': os.getenv('DD_SITE', 'datadoghq.com'),
                'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
                'log_url': os.getenv('DD_LOGS_CONFIG_LOGS_DD_URL', ''),
            },
        }
        assert config.orgs == orgs
        assert config.raw_data == {'orgs': orgs}

    def test_not_table(self, helpers):
        config = RootConfig({'orgs': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                orgs
                  must be a table"""
            ),
        ):
            _ = config.orgs

    def test_defined(self):
        config = RootConfig({'orgs': {'foo': {'bar': 'baz'}}})

        orgs = {'foo': {'bar': 'baz'}}
        assert config.orgs == orgs
        assert config.raw_data == {'orgs': orgs}

    def test_command_blocked_by_trust_falls_back_to_environment(self, monkeypatch):
        monkeypatch.setenv('DD_API_KEY', 'env-api-key')
        config = RootConfig(
            {'orgs': {'default': {'api_key_command': 'missing-executable-12345'}}},
            non_secret_metadata={'trust_blocked_command_fields': {'orgs.default.api_key_command'}},
        )

        assert config.orgs['default'].get('api_key') == 'env-api-key'

    def test_empty(self, helpers):
        config = RootConfig({'orgs': {}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                orgs
                  must define at least one Org"""
            ),
        ):
            _ = config.orgs

    def test_config_not_table(self, helpers):
        config = RootConfig({'orgs': {'foo': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                orgs -> foo
                  must be a table"""
            ),
        ):
            _ = config.orgs

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.orgs = 9000
        assert config.raw_data == {'orgs': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                orgs
                  must be a table"""
            ),
        ):
            _ = config.orgs


class TestGitHub:
    def test_default(self, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'default-token')
        config = RootConfig({})

        assert config.github.user == config.github.user == get_github_user()
        assert config.github.token == config.github.token == 'default-token'
        assert config.raw_data == {
            'github': {},
        }

    def test_token_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'env-token')
        script_path = tmp_path / 'github_token_precedence.py'
        script_path.write_text("print('token_from_command')")

        config = RootConfig(
            {
                'github': {
                    'token': 'literal-token',
                    'token_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.github.token == 'token_from_command'

    def test_user_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_USER', 'env-user')
        script_path = tmp_path / 'github_user_precedence.py'
        script_path.write_text("print('user_from_command')")

        config = RootConfig(
            {
                'github': {
                    'user': 'literal-user',
                    'user_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.github.user == 'user_from_command'

    def test_blank_literal_falls_back_to_environment(self, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'env-token')
        config = RootConfig({'github': {'token': '   '}})

        assert config.github.token == 'env-token'

    def test_missing_token_is_deterministic_required_secret_error(self, helpers, monkeypatch):
        monkeypatch.delenv('DD_GITHUB_TOKEN', raising=False)
        monkeypatch.delenv('GH_TOKEN', raising=False)
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)
        config = RootConfig({})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  \\[missing-required-secret\\] could not resolve required secret for github.token;"""
            ),
        ):
            _ = config.github.token

    def test_not_table(self, helpers):
        config = RootConfig({'github': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github
                  must be a table"""
            ),
        ):
            _ = config.github

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.github = 9000
        assert config.raw_data == {'github': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github
                  must be a table"""
            ),
        ):
            _ = config.github

    def test_user(self):
        config = RootConfig({'github': {'user': 'foo'}})

        assert config.github.user == 'foo'
        assert config.raw_data == {'github': {'user': 'foo'}}

    def test_user_not_string(self, helpers):
        config = RootConfig({'github': {'user': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> user
                  must be a string"""
            ),
        ):
            _ = config.github.user

    def test_user_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.github.user = 9000
        assert config.raw_data == {'github': {'user': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> user
                  must be a string"""
            ),
        ):
            _ = config.github.user

    def test_user_command(self):
        config = RootConfig({'github': {'user_command': 'python user.py'}})

        assert config.github.user_command == 'python user.py'
        assert config.raw_data == {'github': {'user_command': 'python user.py'}}

    def test_user_command_not_string(self, helpers):
        config = RootConfig({'github': {'user_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> user_command
                  must be a string"""
            ),
        ):
            _ = config.github.user_command

    def test_user_command_blocked_by_trust_falls_back_to_environment(self, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_USER', 'env-user')
        config = RootConfig(
            {'github': {'user_command': 'missing-executable-12345'}},
            non_secret_metadata={'trust_blocked_command_fields': {'github.user_command'}},
        )

        assert config.github.user == 'env-user'

    def test_token(self):
        config = RootConfig({'github': {'token': 'foo'}})

        assert config.github.token == 'foo'
        assert config.raw_data == {'github': {'token': 'foo'}}

    def test_token_not_string(self, helpers):
        config = RootConfig({'github': {'token': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  must be a string"""
            ),
        ):
            _ = config.github.token

    def test_token_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.github.token = 9000
        assert config.raw_data == {'github': {'token': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  must be a string"""
            ),
        ):
            _ = config.github.token

    def test_token_command(self):
        config = RootConfig({'github': {'token_command': 'python token.py'}})

        assert config.github.token_command == 'python token.py'
        assert config.raw_data == {'github': {'token_command': 'python token.py'}}

    def test_token_command_not_string(self, helpers):
        config = RootConfig({'github': {'token_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token_command
                  must be a string"""
            ),
        ):
            _ = config.github.token_command

    def test_token_command_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.github.token_command = 9000
        assert config.raw_data == {'github': {'token_command': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token_command
                  must be a string"""
            ),
        ):
            _ = config.github.token_command

    def test_token_command_uses_executor(self, tmp_path):
        script_path = tmp_path / 'github_token.py'
        script_path.write_text("print('token_from_command')")

        config = RootConfig(
            {'github': {'token_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}"}}
        )

        assert config.github.token == 'token_from_command'

    def test_token_command_output_normalized(self, tmp_path):
        script_path = tmp_path / 'github_token_ws.py'
        script_path.write_text("print('  token_with_spaces  ')")
        config = RootConfig(
            {'github': {'token_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}"}}
        )

        assert config.github.token == 'token_with_spaces'

    def test_token_command_failure_exit_code(self, helpers):
        config = RootConfig(
            {'github': {'token_command': f"{shlex.quote(sys.executable)} -c \"import sys; sys.exit(7)\""}}
        )

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  \\[secret-command-non-zero-exit\\] could not resolve required secret for github.token;"""
            ),
        ):
            _ = config.github.token

    def test_token_command_timeout(self, helpers, monkeypatch):
        monkeypatch.setattr('ddev.config.secret_command.DEFAULT_SECRET_COMMAND_TIMEOUT', 0.01)
        config = RootConfig(
            {'github': {'token_command': f"{shlex.quote(sys.executable)} -c \"import time; time.sleep(0.2)\""}}
        )

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  \\[secret-command-timeout\\] could not resolve required secret for github.token;"""
            ),
        ):
            _ = config.github.token

    def test_token_command_missing_executable(self, helpers):
        config = RootConfig({'github': {'token_command': 'missing-executable-12345'}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                github -> token
                  \\[secret-command-executable-not-found\\] could not resolve required secret for github.token;"""
            ),
        ):
            _ = config.github.token

    def test_token_command_lazy_when_other_fields_are_used(self):
        config = RootConfig({'github': {'user': 'github-user', 'token_command': 'missing-executable-12345'}})

        assert config.github.user == 'github-user'


class TestPyPI:
    def test_default(self):
        config = RootConfig({})

        assert config.pypi.user == config.pypi.user == ''
        assert config.pypi.auth == config.pypi.auth == ''
        assert config.raw_data == {
            'pypi': {
                'user': '',
                'auth': '',
            },
        }

    def test_not_table(self, helpers):
        config = RootConfig({'pypi': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi
                  must be a table"""
            ),
        ):
            _ = config.pypi

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.pypi = 9000
        assert config.raw_data == {'pypi': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi
                  must be a table"""
            ),
        ):
            _ = config.pypi

    def test_user(self):
        config = RootConfig({'pypi': {'user': 'foo'}})

        assert config.pypi.user == 'foo'
        assert config.raw_data == {'pypi': {'user': 'foo'}}

    def test_user_not_string(self, helpers):
        config = RootConfig({'pypi': {'user': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi -> user
                  must be a string"""
            ),
        ):
            _ = config.pypi.user

    def test_user_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.pypi.user = 9000
        assert config.raw_data == {'pypi': {'user': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi -> user
                  must be a string"""
            ),
        ):
            _ = config.pypi.user

    def test_auth(self):
        config = RootConfig({'pypi': {'auth': 'foo'}})

        assert config.pypi.auth == 'foo'
        assert config.raw_data == {'pypi': {'auth': 'foo'}}

    def test_auth_command_precedence_over_literal(self, tmp_path):
        script_path = tmp_path / 'pypi_auth.py'
        script_path.write_text("print('auth-from-command')")

        config = RootConfig(
            {
                'pypi': {
                    'auth': 'literal-auth',
                    'auth_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.pypi.auth == 'auth-from-command'

    def test_auth_not_string(self, helpers):
        config = RootConfig({'pypi': {'auth': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi -> auth
                  must be a string"""
            ),
        ):
            _ = config.pypi.auth

    def test_auth_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.pypi.auth = 9000
        assert config.raw_data == {'pypi': {'auth': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi -> auth
                  must be a string"""
            ),
        ):
            _ = config.pypi.auth

    def test_auth_command(self):
        config = RootConfig({'pypi': {'auth_command': 'python auth.py'}})

        assert config.pypi.auth_command == 'python auth.py'
        assert config.raw_data == {'pypi': {'auth_command': 'python auth.py'}}

    def test_auth_command_not_string(self, helpers):
        config = RootConfig({'pypi': {'auth_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                pypi -> auth_command
                  must be a string"""
            ),
        ):
            _ = config.pypi.auth_command

    def test_auth_command_blocked_by_trust_returns_literal(self):
        config = RootConfig(
            {'pypi': {'auth': 'literal-auth', 'auth_command': 'missing-executable-12345'}},
            non_secret_metadata={'trust_blocked_command_fields': {'pypi.auth_command'}},
        )

        assert config.pypi.auth == 'literal-auth'


class TestTrello:
    def test_default_uses_environment(self, monkeypatch):
        monkeypatch.setenv('DD_TRELLO_KEY', 'env-key')
        monkeypatch.setenv('DD_TRELLO_TOKEN', 'env-token')
        config = RootConfig({})

        assert config.trello.key == config.trello.key == 'env-key'
        assert config.trello.token == config.trello.token == 'env-token'
        assert config.raw_data == {
            'trello': {},
        }

    def test_key_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_TRELLO_KEY', 'env-key')
        script_path = tmp_path / 'trello_key.py'
        script_path.write_text("print('key_from_command')")

        config = RootConfig(
            {
                'trello': {
                    'key': 'literal-key',
                    'key_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.trello.key == 'key_from_command'

    def test_token_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DD_TRELLO_TOKEN', 'env-token')
        script_path = tmp_path / 'trello_token.py'
        script_path.write_text("print('token_from_command')")

        config = RootConfig(
            {
                'trello': {
                    'token': 'literal-token',
                    'token_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.trello.token == 'token_from_command'

    def test_missing_key_is_deterministic_required_secret_error(self, helpers, monkeypatch):
        monkeypatch.delenv('DD_TRELLO_KEY', raising=False)
        monkeypatch.delenv('TRELLO_KEY', raising=False)
        config = RootConfig({'trello': {'token': 'literal-token'}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> key
                  \\[missing-required-secret\\] could not resolve required secret for trello.key;"""
            ),
        ):
            _ = config.trello.key

    def test_missing_token_is_deterministic_required_secret_error(self, helpers, monkeypatch):
        monkeypatch.delenv('DD_TRELLO_TOKEN', raising=False)
        monkeypatch.delenv('TRELLO_TOKEN', raising=False)
        config = RootConfig({'trello': {'key': 'literal-key'}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> token
                  \\[missing-required-secret\\] could not resolve required secret for trello.token;"""
            ),
        ):
            _ = config.trello.token

    def test_not_table(self, helpers):
        config = RootConfig({'trello': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello
                  must be a table"""
            ),
        ):
            _ = config.trello

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.trello = 9000
        assert config.raw_data == {'trello': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello
                  must be a table"""
            ),
        ):
            _ = config.trello

    def test_key(self):
        config = RootConfig({'trello': {'key': 'foo'}})

        assert config.trello.key == 'foo'
        assert config.raw_data == {'trello': {'key': 'foo'}}

    def test_key_not_string(self, helpers):
        config = RootConfig({'trello': {'key': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> key
                  must be a string"""
            ),
        ):
            _ = config.trello.key

    def test_key_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.trello.key = 9000
        assert config.raw_data == {'trello': {'key': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> key
                  must be a string"""
            ),
        ):
            _ = config.trello.key

    def test_key_command(self):
        config = RootConfig({'trello': {'key_command': 'python key.py'}})

        assert config.trello.key_command == 'python key.py'
        assert config.raw_data == {'trello': {'key_command': 'python key.py'}}

    def test_key_command_not_string(self, helpers):
        config = RootConfig({'trello': {'key_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> key_command
                  must be a string"""
            ),
        ):
            _ = config.trello.key_command

    def test_key_command_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.trello.key_command = 9000
        assert config.raw_data == {'trello': {'key_command': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> key_command
                  must be a string"""
            ),
        ):
            _ = config.trello.key_command

    def test_token(self):
        config = RootConfig({'trello': {'token': 'foo'}})

        assert config.trello.token == 'foo'
        assert config.raw_data == {'trello': {'token': 'foo'}}

    def test_token_not_string(self, helpers):
        config = RootConfig({'trello': {'token': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> token
                  must be a string"""
            ),
        ):
            _ = config.trello.token

    def test_token_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.trello.token = 9000
        assert config.raw_data == {'trello': {'token': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> token
                  must be a string"""
            ),
        ):
            _ = config.trello.token

    def test_token_command(self):
        config = RootConfig({'trello': {'token_command': 'python token.py'}})

        assert config.trello.token_command == 'python token.py'
        assert config.raw_data == {'trello': {'token_command': 'python token.py'}}

    def test_token_command_not_string(self, helpers):
        config = RootConfig({'trello': {'token_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> token_command
                  must be a string"""
            ),
        ):
            _ = config.trello.token_command

    def test_token_command_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.trello.token_command = 9000
        assert config.raw_data == {'trello': {'token_command': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                trello -> token_command
                  must be a string"""
            ),
        ):
            _ = config.trello.token_command


class TestDynamicD:
    def test_default_uses_environment(self, monkeypatch):
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'anthropic-from-env')
        config = RootConfig({})

        assert config.dynamicd.llm_api_key == 'anthropic-from-env'
        assert config.raw_data == {'dynamicd': {}}

    def test_dd_dynamicd_env_alias_takes_precedence(self, monkeypatch):
        monkeypatch.setenv('DD_DYNAMICD_LLM_API_KEY', 'preferred')
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'fallback')
        config = RootConfig({})

        assert config.dynamicd.llm_api_key == 'preferred'

    def test_llm_api_key_command_precedence_over_literal_and_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'env-key')
        script_path = tmp_path / 'dynamicd_key.py'
        script_path.write_text("print('key_from_command')")

        config = RootConfig(
            {
                'dynamicd': {
                    'llm_api_key': 'literal-key',
                    'llm_api_key_command': f"{shlex.quote(sys.executable)} {shlex.quote(str(script_path))}",
                }
            }
        )

        assert config.dynamicd.llm_api_key == 'key_from_command'

    def test_missing_llm_api_key_is_deterministic_required_secret_error(self, helpers, monkeypatch):
        monkeypatch.delenv('DD_DYNAMICD_LLM_API_KEY', raising=False)
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        config = RootConfig({})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd -> llm_api_key
                  \\[missing-required-secret\\] could not resolve required secret for dynamicd.llm_api_key;"""
            ),
        ):
            _ = config.dynamicd.llm_api_key

    def test_not_table(self, helpers):
        config = RootConfig({'dynamicd': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd
                  must be a table"""
            ),
        ):
            _ = config.dynamicd

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.dynamicd = 9000
        assert config.raw_data == {'dynamicd': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd
                  must be a table"""
            ),
        ):
            _ = config.dynamicd

    def test_llm_api_key_not_string(self, helpers):
        config = RootConfig({'dynamicd': {'llm_api_key': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd -> llm_api_key
                  must be a string"""
            ),
        ):
            _ = config.dynamicd.llm_api_key

    def test_llm_api_key_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.dynamicd.llm_api_key = 9000
        assert config.raw_data == {'dynamicd': {'llm_api_key': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd -> llm_api_key
                  must be a string"""
            ),
        ):
            _ = config.dynamicd.llm_api_key

    def test_llm_api_key_command(self):
        config = RootConfig({'dynamicd': {'llm_api_key_command': 'python llm_key.py'}})

        assert config.dynamicd.llm_api_key_command == 'python llm_key.py'
        assert config.raw_data == {'dynamicd': {'llm_api_key_command': 'python llm_key.py'}}

    def test_llm_api_key_command_not_string(self, helpers):
        config = RootConfig({'dynamicd': {'llm_api_key_command': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd -> llm_api_key_command
                  must be a string"""
            ),
        ):
            _ = config.dynamicd.llm_api_key_command

    def test_llm_api_key_command_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.dynamicd.llm_api_key_command = 9000
        assert config.raw_data == {'dynamicd': {'llm_api_key_command': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                dynamicd -> llm_api_key_command
                  must be a string"""
            ),
        ):
            _ = config.dynamicd.llm_api_key_command

    def test_llm_api_key_command_is_lazy_until_access(self, monkeypatch):
        calls = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            return type('P', (), {'returncode': 0, 'stdout': 'secret-from-command'})()

        monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

        config = RootConfig({'dynamicd': {'llm_api_key_command': 'python key.py'}})
        config.parse_fields()

        assert calls == []

        assert config.dynamicd.llm_api_key == 'secret-from-command'
        assert len(calls) == 1


class TestSecretCommandCache:
    def test_same_command_executes_once_across_model_instances(self, monkeypatch):
        calls = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            return type('P', (), {'returncode': 0, 'stdout': 'cached-token'})()

        monkeypatch.setattr('ddev.config.secret_command.subprocess.run', fake_run)

        first = RootConfig({'github': {'token_command': 'python token.py'}})
        second = RootConfig({'github': {'token_command': 'python token.py'}})

        assert first.github.token == 'cached-token'
        assert second.github.token == 'cached-token'
        assert len(calls) == 1


class TestTerminal:
    def test_default(self):
        config = RootConfig({})

        assert config.terminal.styles.info == config.terminal.styles.info == 'bold'
        assert config.terminal.styles.success == config.terminal.styles.success == 'bold cyan'
        assert config.terminal.styles.error == config.terminal.styles.error == 'bold red'
        assert config.terminal.styles.warning == config.terminal.styles.warning == 'bold yellow'
        assert config.terminal.styles.waiting == config.terminal.styles.waiting == 'bold magenta'
        assert config.terminal.styles.debug == config.terminal.styles.debug == 'bold'
        assert config.terminal.styles.spinner == config.terminal.styles.spinner == 'simpleDotsScrolling'
        assert config.raw_data == {
            'terminal': {
                'styles': {
                    'info': 'bold',
                    'success': 'bold cyan',
                    'error': 'bold red',
                    'warning': 'bold yellow',
                    'waiting': 'bold magenta',
                    'debug': 'bold',
                    'spinner': 'simpleDotsScrolling',
                },
            },
        }

    def test_not_table(self, helpers):
        config = RootConfig({'terminal': 9000})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal
                  must be a table"""
            ),
        ):
            _ = config.terminal

    def test_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal = 9000
        assert config.raw_data == {'terminal': 9000}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal
                  must be a table"""
            ),
        ):
            _ = config.terminal

    def test_styles_not_table(self, helpers):
        config = RootConfig({'terminal': {'styles': 9000}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles
                  must be a table"""
            ),
        ):
            _ = config.terminal.styles

    def test_styles_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles = 9000
        assert config.raw_data == {'terminal': {'styles': 9000}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles
                  must be a table"""
            ),
        ):
            _ = config.terminal.styles

    def test_styles_info(self):
        config = RootConfig({'terminal': {'styles': {'info': 'foo'}}})

        assert config.terminal.styles.info == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'info': 'foo'}}}

    def test_styles_info_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'info': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> info
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.info

    def test_styles_info_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.info = 9000
        assert config.raw_data == {'terminal': {'styles': {'info': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> info
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.info

    def test_styles_success(self):
        config = RootConfig({'terminal': {'styles': {'success': 'foo'}}})

        assert config.terminal.styles.success == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'success': 'foo'}}}

    def test_styles_success_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'success': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> success
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.success

    def test_styles_success_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.success = 9000
        assert config.raw_data == {'terminal': {'styles': {'success': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> success
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.success

    def test_styles_error(self):
        config = RootConfig({'terminal': {'styles': {'error': 'foo'}}})

        assert config.terminal.styles.error == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'error': 'foo'}}}

    def test_styles_error_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'error': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> error
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.error

    def test_styles_error_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.error = 9000
        assert config.raw_data == {'terminal': {'styles': {'error': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> error
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.error

    def test_styles_warning(self):
        config = RootConfig({'terminal': {'styles': {'warning': 'foo'}}})

        assert config.terminal.styles.warning == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'warning': 'foo'}}}

    def test_styles_warning_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'warning': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> warning
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.warning

    def test_styles_warning_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.warning = 9000
        assert config.raw_data == {'terminal': {'styles': {'warning': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> warning
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.warning

    def test_styles_waiting(self):
        config = RootConfig({'terminal': {'styles': {'waiting': 'foo'}}})

        assert config.terminal.styles.waiting == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'waiting': 'foo'}}}

    def test_styles_waiting_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'waiting': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> waiting
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.waiting

    def test_styles_waiting_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.waiting = 9000
        assert config.raw_data == {'terminal': {'styles': {'waiting': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> waiting
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.waiting

    def test_styles_debug(self):
        config = RootConfig({'terminal': {'styles': {'debug': 'foo'}}})

        assert config.terminal.styles.debug == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'debug': 'foo'}}}

    def test_styles_debug_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'debug': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> debug
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.debug

    def test_styles_debug_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.debug = 9000
        assert config.raw_data == {'terminal': {'styles': {'debug': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> debug
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.debug

    def test_styles_spinner(self):
        config = RootConfig({'terminal': {'styles': {'spinner': 'foo'}}})

        assert config.terminal.styles.spinner == 'foo'
        assert config.raw_data == {'terminal': {'styles': {'spinner': 'foo'}}}

    def test_styles_spinner_not_string(self, helpers):
        config = RootConfig({'terminal': {'styles': {'spinner': 9000}}})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> spinner
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.spinner

    def test_styles_spinner_set_lazy_error(self, helpers):
        config = RootConfig({})

        config.terminal.styles.spinner = 9000
        assert config.raw_data == {'terminal': {'styles': {'spinner': 9000}}}

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                terminal -> styles -> spinner
                  must be a string"""
            ),
        ):
            _ = config.terminal.styles.spinner


class TestGitHubConfig:
    def test_default_github_config_empty_raw_data(self, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'env_token')
        config = RootConfig({})
        config.parse_fields()

        # GitHub config should be empty in raw_data when not explicitly set
        assert config.raw_data['github'] == {}

        # But properties should still work via environment variables
        assert config.github.user == get_github_user()
        assert config.github.token == 'env_token'

        # After accessing properties, raw_data should still be empty
        assert config.raw_data['github'] == {}

    def test_explicit_github_config_in_raw_data(self):
        config = RootConfig({'github': {'user': 'explicit_user', 'token': 'explicit_token'}})

        # When explicitly set, values should be in raw_data
        assert config.raw_data['github']['user'] == 'explicit_user'
        assert config.raw_data['github']['token'] == 'explicit_token'

        # Properties should return explicit values
        assert config.github.user == 'explicit_user'
        assert config.github.token == 'explicit_token'

    def test_partial_github_config_explicit_user_only(self, monkeypatch):
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'env_token')
        config = RootConfig({'github': {'user': 'explicit_user'}})

        # Only explicitly set field should be in raw_data
        assert config.raw_data['github']['user'] == 'explicit_user'
        assert 'token' not in config.raw_data['github']

        # Properties should work - explicit user, env var token
        assert config.github.user == 'explicit_user'
        assert config.github.token == 'env_token'

        # raw_data should still only have explicit field
        assert config.raw_data['github']['user'] == 'explicit_user'
        assert 'token' not in config.raw_data['github']

    def test_partial_github_config_explicit_token_only(self):
        config = RootConfig({'github': {'token': 'explicit_token'}})

        # Only explicitly set field should be in raw_data
        assert 'user' not in config.raw_data['github']
        assert config.raw_data['github']['token'] == 'explicit_token'

        # Properties should work - env var user, explicit token
        assert config.github.user == get_github_user()
        assert config.github.token == 'explicit_token'

        # raw_data should still only have explicit field
        assert 'user' not in config.raw_data['github']
        assert config.raw_data['github']['token'] == 'explicit_token'

    def test_github_config_with_environment_variables(self, monkeypatch):
        # Mock environment variables
        monkeypatch.setenv('DD_GITHUB_USER', 'env_user')
        monkeypatch.setenv('DD_GITHUB_TOKEN', 'env_token')

        config = RootConfig({})

        # Properties should return environment variable values
        assert config.github.user == 'env_user'
        assert config.github.token == 'env_token'

        # raw_data should still be empty
        assert config.raw_data['github'] == {}

    def test_github_token_uses_gh_token_alias_when_primary_env_absent(self, monkeypatch):
        monkeypatch.delenv('DD_GITHUB_TOKEN', raising=False)
        monkeypatch.setenv('GH_TOKEN', 'gh-token')
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)

        config = RootConfig({})

        assert config.github.token == 'gh-token'

    def test_missing_required_secret_error_reports_first_missing_field(self, monkeypatch):
        monkeypatch.delenv('DD_GITHUB_TOKEN', raising=False)
        monkeypatch.delenv('GH_TOKEN', raising=False)
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)

        config = RootConfig({})

        with pytest.raises(ConfigurationError) as error:
            _ = config.github.token

        message = str(error.value)
        assert 'github -> token' in message
        assert 'missing-required-secret' in message
        assert 'orgs' not in message
