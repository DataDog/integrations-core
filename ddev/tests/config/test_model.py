# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from ddev.config.model import ConfigurationError, RootConfig


def test_default():
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
            'dev': {'docker': 'datadog/agent-dev:master', 'local': 'latest'},
            '7': {'docker': 'datadog/agent:7', 'local': '7'},
        },
        'orgs': {
            'default': {
                'api_key': os.getenv('DD_API_KEY', ''),
                'app_key': os.getenv('DD_APP_KEY', ''),
                'site': os.getenv('DD_SITE', 'datadoghq.com'),
                'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
                'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL', ''),
            },
        },
        'github': {
            'user': os.getenv('DD_GITHUB_USER', ''),
            'token': os.getenv('DD_GITHUB_TOKEN', ''),
        },
        'pypi': {
            'user': '',
            'auth': '',
        },
        'trello': {
            'key': '',
            'token': '',
        },
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
                  unknown repository"""
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

        agent_config = {'docker': 'datadog/agent-dev:master', 'local': 'latest'}
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

        agent_config = {'docker': 'datadog/agent:7', 'local': '7'}
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
                  unknown Agent"""
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
            'config': {'docker': 'datadog/agent-dev:master', 'local': 'latest'},
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
            'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL', ''),
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

    def test_unknown(self, helpers):
        config = RootConfig({'org': 'foo'})

        with pytest.raises(
            ConfigurationError,
            match=helpers.dedent(
                """
                Error parsing config:
                org
                  unknown Org"""
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
                'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL', ''),
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
            'dev': {'docker': 'datadog/agent-dev:master', 'local': 'latest'},
            '7': {'docker': 'datadog/agent:7', 'local': '7'},
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
                'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL', ''),
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
    def test_default(self):
        config = RootConfig({})

        assert config.github.user == config.github.user == os.getenv('DD_GITHUB_USER', '')
        assert config.github.token == config.github.token == os.getenv('DD_GITHUB_TOKEN', '')
        assert config.raw_data == {
            'github': {
                'user': os.getenv('DD_GITHUB_USER', ''),
                'token': os.getenv('DD_GITHUB_TOKEN', ''),
            },
        }

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


class TestTrello:
    def test_default(self):
        config = RootConfig({})

        assert config.trello.key == config.trello.key == ''
        assert config.trello.token == config.trello.token == ''
        assert config.raw_data == {
            'trello': {
                'key': '',
                'token': '',
            },
        }

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
