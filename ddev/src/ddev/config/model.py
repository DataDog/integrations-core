# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections.abc import Iterator, Mapping

from ddev.config.secret_resolution import SecretResolutionError, resolve_optional_secret, resolve_required_secret

FIELD_TO_PARSE = object()


def get_github_user():
    return (
        os.environ.get('DD_GITHUB_USER', '')
        or os.environ.get('GITHUB_USER', '')
        # GitHub Actions
        or os.environ.get('GITHUB_ACTOR', '')
    )


def get_github_token():
    return os.environ.get('DD_GITHUB_TOKEN', '') or os.environ.get('GH_TOKEN', '') or os.environ.get('GITHUB_TOKEN', '')


def get_trello_key():
    return os.environ.get('DD_TRELLO_KEY', '') or os.environ.get('TRELLO_KEY', '')


def get_trello_token():
    return os.environ.get('DD_TRELLO_TOKEN', '') or os.environ.get('TRELLO_TOKEN', '')


def get_dynamicd_llm_api_key():
    return os.environ.get('DD_DYNAMICD_LLM_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')


class ConfigurationError(Exception):
    def __init__(self, *args, location):
        self.location = location
        super().__init__(*args)

    def __str__(self):
        return f'Error parsing config:\n{self.location}\n  {super().__str__()}'


def parse_config(obj):
    if isinstance(obj, LazilyParsedConfig):
        obj.parse_fields()
    elif isinstance(obj, list):
        for o in obj:
            parse_config(o)
    elif isinstance(obj, dict):
        for o in obj.values():
            parse_config(o)


class LazilyParsedConfig:
    def __init__(self, config: dict, steps: tuple = ()):
        self.raw_data = config
        self.steps = steps

    def parse_fields(self):
        for attribute in self.__dict__:
            _, prefix, name = attribute.partition('_field_')
            if prefix:
                parse_config(getattr(self, name))

    def raise_error(self, message, *, extra_steps=()):
        import inspect

        field = inspect.currentframe().f_back.f_code.co_name
        raise ConfigurationError(message, location=' -> '.join([*self.steps, field, *extra_steps]))


class RootConfig(LazilyParsedConfig):
    def __init__(self, *args, non_secret_metadata=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.non_secret_metadata = non_secret_metadata or {}

        self._field_repo = FIELD_TO_PARSE
        self._field_agent = FIELD_TO_PARSE
        self._field_org = FIELD_TO_PARSE
        self._field_repos = FIELD_TO_PARSE
        self._field_agents = FIELD_TO_PARSE
        self._field_orgs = FIELD_TO_PARSE
        self._field_github = FIELD_TO_PARSE
        self._field_pypi = FIELD_TO_PARSE
        self._field_trello = FIELD_TO_PARSE
        self._field_terminal = FIELD_TO_PARSE
        self._field_dynamicd = FIELD_TO_PARSE
        self._field_upgrade_check = FIELD_TO_PARSE

    @property
    def upgrade_check(self):
        if self._field_upgrade_check is FIELD_TO_PARSE:
            raw_update = self.raw_data.get('upgrade_check', True)
            if isinstance(raw_update, bool):
                upgrade_check = raw_update
            elif isinstance(raw_update, str):
                if raw_update.lower() == 'true':
                    upgrade_check = True
                elif raw_update.lower() == 'false':
                    upgrade_check = False
                else:
                    self.raise_error(f'must be a boolean or the string "true"/"false", got: {raw_update!r}')

            else:
                self.raise_error(f'must be a boolean or string, got type: {type(raw_update).__name__}')
            self._field_upgrade_check = upgrade_check
        return self._field_upgrade_check

    @upgrade_check.setter
    def upgrade_check(self, value):
        self.raw_data['upgrade_check'] = value
        self._field_upgrade_check = FIELD_TO_PARSE

    @property
    def repo(self):
        if self._field_repo is FIELD_TO_PARSE:
            repo = self.raw_data['repo'] if 'repo' in self.raw_data else 'core'
            if not isinstance(repo, str):
                self.raise_error('must be a string')
            elif repo not in self.repos:
                self.raise_error(f'unknown Repository: {repo!r}')

            self.raw_data['repo'] = repo
            self._field_repo = RepoConfig({'name': repo, 'path': self.repos[repo]}, ('repo',))

        return self._field_repo

    @repo.setter
    def repo(self, value):
        self.raw_data['repo'] = value
        self._field_repo = FIELD_TO_PARSE

    @property
    def agent(self):
        if self._field_agent is FIELD_TO_PARSE:
            agent = self.raw_data['agent'] if 'agent' in self.raw_data else 'dev'
            if not isinstance(agent, str):
                self.raise_error('must be a string')
            elif agent not in self.agents:
                self.raise_error(f'unknown Agent: {agent!r}')

            self.raw_data['agent'] = agent
            self._field_agent = AgentConfig({'name': agent, 'config': self.agents[agent]}, ('agent',))

        return self._field_agent

    @agent.setter
    def agent(self, value):
        self.raw_data['agent'] = value
        self._field_agent = FIELD_TO_PARSE

    @property
    def org(self):
        if self._field_org is FIELD_TO_PARSE:
            org = self.raw_data['org'] if 'org' in self.raw_data else 'default'
            if not isinstance(org, str):
                self.raise_error('must be a string')
            elif org not in self.orgs:
                self.raise_error(f'unknown Org: {org!r}')

            self.raw_data['org'] = org
            self._field_org = OrgConfig(
                {'name': org, 'config': self.raw_data['orgs'][org]},
                ('org',),
                trust_blocked_command_fields=self._trust_blocked_command_fields,
            )

        return self._field_org

    @org.setter
    def org(self, value):
        self.raw_data['org'] = value
        self._field_org = FIELD_TO_PARSE

    @property
    def repos(self):
        if self._field_repos is FIELD_TO_PARSE:
            if 'repos' in self.raw_data:
                repos = self.raw_data['repos']
                if not isinstance(repos, dict):
                    self.raise_error('must be a table')
                elif not repos:
                    self.raise_error('must define at least one repository')

                for name, data in repos.items():
                    if not isinstance(data, str):
                        self.raise_error('must be a string', extra_steps=(name,))

                self._field_repos = repos
            else:
                self._field_repos = self.raw_data['repos'] = {
                    'core': os.path.join('~', 'dd', 'integrations-core'),
                    'extras': os.path.join('~', 'dd', 'integrations-extras'),
                    'marketplace': os.path.join('~', 'dd', 'marketplace'),
                    'agent': os.path.join('~', 'dd', 'datadog-agent'),
                }

        return self._field_repos

    @repos.setter
    def repos(self, value):
        self.raw_data['repos'] = value
        self._field_repos = FIELD_TO_PARSE

    @property
    def agents(self):
        if self._field_agents is FIELD_TO_PARSE:
            if 'agents' in self.raw_data:
                agents = self.raw_data['agents']
                if not isinstance(agents, dict):
                    self.raise_error('must be a table')
                elif not agents:
                    self.raise_error('must define at least one Agent')

                for name, data in agents.items():
                    if not isinstance(data, dict):
                        self.raise_error('must be a table', extra_steps=(name,))

                self._field_agents = agents
            else:
                self._field_agents = self.raw_data['agents'] = {
                    'dev': {'docker': 'datadog/agent-dev:master', 'local': 'latest'},
                    '7': {'docker': 'datadog/agent:7', 'local': '7'},
                }

        return self._field_agents

    @agents.setter
    def agents(self, value):
        self.raw_data['agents'] = value
        self._field_agents = FIELD_TO_PARSE

    @property
    def orgs(self):
        if self._field_orgs is FIELD_TO_PARSE:
            if 'orgs' in self.raw_data:
                orgs = self.raw_data['orgs']
                if not isinstance(orgs, dict):
                    self.raise_error('must be a table')
                elif not orgs:
                    self.raise_error('must define at least one Org')

                for name, data in orgs.items():
                    if not isinstance(data, dict):
                        self.raise_error('must be a table', extra_steps=(name,))

                self._field_orgs = _OrgWriteThroughDict(
                    self.raw_data['orgs'],
                    {
                        name: OrgSettingsConfig(
                            data,
                            ('orgs', name),
                            trust_blocked_command_fields=self._trust_blocked_command_fields,
                        )
                        for name, data in orgs.items()
                    },
                )
            else:
                from ddev.e2e.agent.constants import AgentEnvVars

                self.raw_data['orgs'] = {
                    'default': {
                        'api_key': os.getenv(AgentEnvVars.API_KEY, ''),
                        'app_key': os.getenv(AgentEnvVars.APP_KEY, ''),
                        'site': os.getenv(AgentEnvVars.SITE, 'datadoghq.com'),
                        'dd_url': os.getenv(AgentEnvVars.URL, 'https://app.datadoghq.com'),
                        'log_url': os.getenv(AgentEnvVars.LOGS_URL, ''),
                    },
                }
                self._field_orgs = _OrgWriteThroughDict(
                    self.raw_data['orgs'],
                    {
                        name: OrgSettingsConfig(
                            data,
                            ('orgs', name),
                            trust_blocked_command_fields=self._trust_blocked_command_fields,
                        )
                        for name, data in self.raw_data['orgs'].items()
                    },
                )

        return self._field_orgs

    @orgs.setter
    def orgs(self, value):
        self.raw_data['orgs'] = value
        self._field_orgs = FIELD_TO_PARSE

    @property
    def github(self):
        if self._field_github is FIELD_TO_PARSE:
            if 'github' in self.raw_data:
                github = self.raw_data['github']
                if not isinstance(github, dict):
                    self.raise_error('must be a table')

                self._field_github = GitHubConfig(
                    github,
                    ('github',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )
            else:
                github = {}
                self.raw_data['github'] = github
                self._field_github = GitHubConfig(
                    github,
                    ('github',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )

        return self._field_github

    @github.setter
    def github(self, value):
        self.raw_data['github'] = value
        self._field_github = FIELD_TO_PARSE

    @property
    def pypi(self):
        if self._field_pypi is FIELD_TO_PARSE:
            if 'pypi' in self.raw_data:
                pypi = self.raw_data['pypi']
                if not isinstance(pypi, dict):
                    self.raise_error('must be a table')

                self._field_pypi = PyPIConfig(
                    pypi,
                    ('pypi',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )
            else:
                pypi = {}
                self.raw_data['pypi'] = pypi
                self._field_pypi = PyPIConfig(
                    pypi,
                    ('pypi',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )

        return self._field_pypi

    @pypi.setter
    def pypi(self, value):
        self.raw_data['pypi'] = value
        self._field_pypi = FIELD_TO_PARSE

    @property
    def trello(self):
        if self._field_trello is FIELD_TO_PARSE:
            if 'trello' in self.raw_data:
                trello = self.raw_data['trello']
                if not isinstance(trello, dict):
                    self.raise_error('must be a table')

                self._field_trello = TrelloConfig(
                    trello,
                    ('trello',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )
            else:
                trello = {}
                self.raw_data['trello'] = trello
                self._field_trello = TrelloConfig(
                    trello,
                    ('trello',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )

        return self._field_trello

    @trello.setter
    def trello(self, value):
        self.raw_data['trello'] = value
        self._field_trello = FIELD_TO_PARSE

    @property
    def terminal(self):
        if self._field_terminal is FIELD_TO_PARSE:
            if 'terminal' in self.raw_data:
                terminal = self.raw_data['terminal']
                if not isinstance(terminal, dict):
                    self.raise_error('must be a table')

                self._field_terminal = TerminalConfig(terminal, ('terminal',))
            else:
                terminal = {}
                self.raw_data['terminal'] = terminal
                self._field_terminal = TerminalConfig(terminal, ('terminal',))

        return self._field_terminal

    @terminal.setter
    def terminal(self, value):
        self.raw_data['terminal'] = value
        self._field_terminal = FIELD_TO_PARSE

    @property
    def dynamicd(self):
        if self._field_dynamicd is FIELD_TO_PARSE:
            if 'dynamicd' in self.raw_data:
                dynamicd = self.raw_data['dynamicd']
                if not isinstance(dynamicd, dict):
                    self.raise_error('must be a table')

                self._field_dynamicd = DynamicDConfig(
                    dynamicd,
                    ('dynamicd',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )
            else:
                dynamicd = {}
                self.raw_data['dynamicd'] = dynamicd
                self._field_dynamicd = DynamicDConfig(
                    dynamicd,
                    ('dynamicd',),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )

        return self._field_dynamicd

    @dynamicd.setter
    def dynamicd(self, value):
        self.raw_data['dynamicd'] = value
        self._field_dynamicd = FIELD_TO_PARSE

    @property
    def _trust_blocked_command_fields(self):
        value = self.non_secret_metadata.get('trust_blocked_command_fields', set())
        if not isinstance(value, set):
            return set()
        return value


class RepoConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_name = FIELD_TO_PARSE
        self._field_path = FIELD_TO_PARSE

    @property
    def name(self):
        if self._field_name is FIELD_TO_PARSE:
            if 'name' in self.raw_data:
                name = self.raw_data['name']
                if not isinstance(name, str):
                    self.raise_error('must be a string')

                self._field_name = name
            else:
                self.raise_error('required field')

        return self._field_name

    @name.setter
    def name(self, value):
        self.raw_data['name'] = value
        self._field_name = FIELD_TO_PARSE

    @property
    def path(self):
        if self._field_path is FIELD_TO_PARSE:
            if 'path' in self.raw_data:
                path = self.raw_data['path']
                if not isinstance(path, str):
                    self.raise_error('must be a string')

                self._field_path = path
            else:
                self.raise_error('required field')

        return self._field_path

    @path.setter
    def path(self, value):
        self.raw_data['path'] = value
        self._field_path = FIELD_TO_PARSE


class AgentConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_name = FIELD_TO_PARSE
        self._field_config = FIELD_TO_PARSE

    @property
    def name(self):
        if self._field_name is FIELD_TO_PARSE:
            if 'name' in self.raw_data:
                name = self.raw_data['name']
                if not isinstance(name, str):
                    self.raise_error('must be a string')

                self._field_name = name
            else:
                self.raise_error('required field')

        return self._field_name

    @name.setter
    def name(self, value):
        self.raw_data['name'] = value
        self._field_name = FIELD_TO_PARSE

    @property
    def config(self):
        if self._field_config is FIELD_TO_PARSE:
            if 'config' in self.raw_data:
                config = self.raw_data['config']
                if not isinstance(config, dict):
                    self.raise_error('must be a table')

                self._field_config = config
            else:
                self.raise_error('required field')

        return self._field_config

    @config.setter
    def config(self, value):
        self.raw_data['config'] = value
        self._field_config = FIELD_TO_PARSE


class _OrgWriteThroughDict(dict):
    """A dict of OrgSettingsConfig objects that writes new entries back to raw_data['orgs'].

    This preserves the pre-secret-provider write-through behaviour so that
    ``model.orgs['new_org'] = {}`` is reflected in ``model.raw_data['orgs']``
    and therefore in the saved config file.
    """

    __slots__ = ('_raw_orgs',)

    def __init__(self, raw_orgs: dict, items: dict):
        super().__init__(items)
        self._raw_orgs = raw_orgs

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._raw_orgs[key] = value.raw_data if isinstance(value, OrgSettingsConfig) else value


class OrgSettingsConfig(LazilyParsedConfig, Mapping):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_api_key = FIELD_TO_PARSE
        self._field_api_key_command = FIELD_TO_PARSE
        self._field_app_key = FIELD_TO_PARSE
        self._field_app_key_command = FIELD_TO_PARSE

    def parse_fields(self):
        parse_config(self.api_key_command)
        parse_config(self.app_key_command)

    @property
    def api_key(self):
        if self._field_api_key is FIELD_TO_PARSE:
            literal_api_key = None
            if 'api_key' in self.raw_data:
                literal_api_key = self.raw_data['api_key']
                if not isinstance(literal_api_key, str):
                    self.raise_error('must be a string')

            command = self.api_key_command

            try:
                self._field_api_key = resolve_optional_secret(
                    field_path='.'.join((*self.steps, 'api_key')),
                    command=command,
                    literal=literal_api_key,
                    env_var='DD_API_KEY',
                    env_value=os.environ.get('DD_API_KEY', ''),
                    env_label='DD_API_KEY',
                    command_blocked_by_trust='.'.join((*self.steps, 'api_key_command'))
                    in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_api_key

    @property
    def api_key_command(self):
        if self._field_api_key_command is FIELD_TO_PARSE:
            if 'api_key_command' not in self.raw_data:
                self._field_api_key_command = None
            else:
                api_key_command = self.raw_data['api_key_command']
                if not isinstance(api_key_command, str):
                    self.raise_error('must be a string')

                self._field_api_key_command = api_key_command

        return self._field_api_key_command

    @property
    def app_key(self):
        if self._field_app_key is FIELD_TO_PARSE:
            literal_app_key = None
            if 'app_key' in self.raw_data:
                literal_app_key = self.raw_data['app_key']
                if not isinstance(literal_app_key, str):
                    self.raise_error('must be a string')

            command = self.app_key_command

            try:
                self._field_app_key = resolve_optional_secret(
                    field_path='.'.join((*self.steps, 'app_key')),
                    command=command,
                    literal=literal_app_key,
                    env_var='DD_APP_KEY',
                    env_value=os.environ.get('DD_APP_KEY', ''),
                    env_label='DD_APP_KEY',
                    command_blocked_by_trust='.'.join((*self.steps, 'app_key_command'))
                    in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_app_key

    @property
    def app_key_command(self):
        if self._field_app_key_command is FIELD_TO_PARSE:
            if 'app_key_command' not in self.raw_data:
                self._field_app_key_command = None
            else:
                app_key_command = self.raw_data['app_key_command']
                if not isinstance(app_key_command, str):
                    self.raise_error('must be a string')

                self._field_app_key_command = app_key_command

        return self._field_app_key_command

    def __getitem__(self, key):
        if key == 'api_key':
            return self.api_key
        if key == 'app_key':
            return self.app_key
        return self.raw_data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.raw_data)

    def __len__(self) -> int:
        return len(self.raw_data)

    def __setitem__(self, key, value):
        self.raw_data[key] = value
        field_attr = f'_field_{key}'
        if hasattr(self, field_attr):
            setattr(self, field_attr, FIELD_TO_PARSE)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Mapping):
            return False
        return dict(self.items()) == dict(other.items())


class OrgConfig(LazilyParsedConfig):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_name = FIELD_TO_PARSE
        self._field_config = FIELD_TO_PARSE

    @property
    def name(self):
        if self._field_name is FIELD_TO_PARSE:
            if 'name' in self.raw_data:
                name = self.raw_data['name']
                if not isinstance(name, str):
                    self.raise_error('must be a string')

                self._field_name = name
            else:
                self.raise_error('required field')

        return self._field_name

    @name.setter
    def name(self, value):
        self.raw_data['name'] = value
        self._field_name = FIELD_TO_PARSE

    @property
    def config(self):
        if self._field_config is FIELD_TO_PARSE:
            if 'config' in self.raw_data:
                config = self.raw_data['config']
                if not isinstance(config, dict):
                    self.raise_error('must be a table')

                self._field_config = OrgSettingsConfig(
                    config,
                    ('orgs', self.name),
                    trust_blocked_command_fields=self._trust_blocked_command_fields,
                )
            else:
                self.raise_error('required field')

        return self._field_config

    @config.setter
    def config(self, value):
        self.raw_data['config'] = value
        self._field_config = FIELD_TO_PARSE


class GitHubConfig(LazilyParsedConfig):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_user = FIELD_TO_PARSE
        self._field_user_command = FIELD_TO_PARSE
        self._field_token = FIELD_TO_PARSE
        self._field_token_command = FIELD_TO_PARSE

    def parse_fields(self):
        # Keep command-backed token resolution lazy. Parsing all fields (used by config reset and
        # non-auth paths) should validate structure without forcing required-secret evaluation.
        if 'user_command' in self.raw_data:
            if 'user' in self.raw_data and not isinstance(self.raw_data['user'], str):
                raise ConfigurationError('must be a string', location=' -> '.join([*self.steps, 'user']))
        else:
            parse_config(self.user)
        parse_config(self.user_command)
        parse_config(self.token_command)

    @property
    def user(self):
        if self._field_user is FIELD_TO_PARSE:
            literal_user = None
            if 'user' in self.raw_data:
                literal_user = self.raw_data['user']
                if not isinstance(literal_user, str):
                    self.raise_error('must be a string')

            command = self.user_command

            try:
                self._field_user = resolve_optional_secret(
                    field_path='github.user',
                    command=command,
                    literal=literal_user,
                    env_var='DD_GITHUB_USER',
                    env_value=get_github_user(),
                    env_label='DD_GITHUB_USER|GITHUB_USER|GITHUB_ACTOR',
                    command_blocked_by_trust='github.user_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_user

    @user.setter
    def user(self, value):
        self.raw_data['user'] = value
        self._field_user = FIELD_TO_PARSE

    @property
    def user_command(self):
        if self._field_user_command is FIELD_TO_PARSE:
            if 'user_command' not in self.raw_data:
                self._field_user_command = None
            else:
                user_command = self.raw_data['user_command']
                if not isinstance(user_command, str):
                    self.raise_error('must be a string')

                self._field_user_command = user_command

        return self._field_user_command

    @user_command.setter
    def user_command(self, value):
        self.raw_data['user_command'] = value
        self._field_user_command = FIELD_TO_PARSE

    @property
    def token(self):
        if self._field_token is FIELD_TO_PARSE:
            literal_token = None
            if 'token' in self.raw_data:
                literal_token = self.raw_data['token']
                if not isinstance(literal_token, str):
                    self.raise_error('must be a string')

            command = self.token_command

            try:
                self._field_token = resolve_required_secret(
                    field_path='github.token',
                    command=command,
                    literal=literal_token,
                    env_var='DD_GITHUB_TOKEN',
                    env_value=get_github_token(),
                    env_label='DD_GITHUB_TOKEN|GH_TOKEN|GITHUB_TOKEN',
                    command_blocked_by_trust='github.token_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_token

    @token.setter
    def token(self, value):
        self.raw_data['token'] = value
        self._field_token = FIELD_TO_PARSE

    @property
    def token_command(self):
        if self._field_token_command is FIELD_TO_PARSE:
            if 'token_command' not in self.raw_data:
                self._field_token_command = None
            else:
                token_command = self.raw_data['token_command']
                if not isinstance(token_command, str):
                    self.raise_error('must be a string')

                self._field_token_command = token_command

        return self._field_token_command

    @token_command.setter
    def token_command(self, value):
        self.raw_data['token_command'] = value
        self._field_token_command = FIELD_TO_PARSE


class PyPIConfig(LazilyParsedConfig):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_user = FIELD_TO_PARSE
        self._field_auth = FIELD_TO_PARSE
        self._field_auth_command = FIELD_TO_PARSE

    def parse_fields(self):
        parse_config(self.user)
        if 'auth_command' in self.raw_data:
            if 'auth' in self.raw_data and not isinstance(self.raw_data['auth'], str):
                raise ConfigurationError('must be a string', location=' -> '.join([*self.steps, 'auth']))
        else:
            parse_config(self.auth)
        parse_config(self.auth_command)

    @property
    def user(self):
        if self._field_user is FIELD_TO_PARSE:
            if 'user' in self.raw_data:
                user = self.raw_data['user']
                if not isinstance(user, str):
                    self.raise_error('must be a string')

                self._field_user = user
            else:
                self._field_user = self.raw_data['user'] = ''

        return self._field_user

    @user.setter
    def user(self, value):
        self.raw_data['user'] = value
        self._field_user = FIELD_TO_PARSE

    @property
    def auth(self):
        if self._field_auth is FIELD_TO_PARSE:
            literal_auth = None
            if 'auth' in self.raw_data:
                literal_auth = self.raw_data['auth']
                if not isinstance(literal_auth, str):
                    self.raise_error('must be a string')
            elif 'auth_command' not in self.raw_data:
                self._field_auth = self.raw_data['auth'] = ''
                return self._field_auth

            command = self.auth_command

            try:
                self._field_auth = resolve_optional_secret(
                    field_path='pypi.auth',
                    command=command,
                    literal=literal_auth,
                    env_var='PYPI_AUTH',
                    env_value='',
                    env_label='(none)',
                    command_blocked_by_trust='pypi.auth_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_auth

    @auth.setter
    def auth(self, value):
        self.raw_data['auth'] = value
        self._field_auth = FIELD_TO_PARSE

    @property
    def auth_command(self):
        if self._field_auth_command is FIELD_TO_PARSE:
            if 'auth_command' not in self.raw_data:
                self._field_auth_command = None
            else:
                auth_command = self.raw_data['auth_command']
                if not isinstance(auth_command, str):
                    self.raise_error('must be a string')

                self._field_auth_command = auth_command

        return self._field_auth_command

    @auth_command.setter
    def auth_command(self, value):
        self.raw_data['auth_command'] = value
        self._field_auth_command = FIELD_TO_PARSE


class TrelloConfig(LazilyParsedConfig):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_key = FIELD_TO_PARSE
        self._field_key_command = FIELD_TO_PARSE
        self._field_token = FIELD_TO_PARSE
        self._field_token_command = FIELD_TO_PARSE

    def parse_fields(self):
        # Keep required secret resolution lazy for trello credentials.
        parse_config(self.key_command)
        parse_config(self.token_command)

    @property
    def key(self):
        if self._field_key is FIELD_TO_PARSE:
            literal_key = None
            if 'key' in self.raw_data:
                literal_key = self.raw_data['key']
                if not isinstance(literal_key, str):
                    self.raise_error('must be a string')

            command = self.key_command

            try:
                self._field_key = resolve_required_secret(
                    field_path='trello.key',
                    command=command,
                    literal=literal_key,
                    env_var='DD_TRELLO_KEY',
                    env_value=get_trello_key(),
                    env_label='DD_TRELLO_KEY|TRELLO_KEY',
                    command_blocked_by_trust='trello.key_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_key

    @key.setter
    def key(self, value):
        self.raw_data['key'] = value
        self._field_key = FIELD_TO_PARSE

    @property
    def token(self):
        if self._field_token is FIELD_TO_PARSE:
            literal_token = None
            if 'token' in self.raw_data:
                literal_token = self.raw_data['token']
                if not isinstance(literal_token, str):
                    self.raise_error('must be a string')

            command = self.token_command

            try:
                self._field_token = resolve_required_secret(
                    field_path='trello.token',
                    command=command,
                    literal=literal_token,
                    env_var='DD_TRELLO_TOKEN',
                    env_value=get_trello_token(),
                    env_label='DD_TRELLO_TOKEN|TRELLO_TOKEN',
                    command_blocked_by_trust='trello.token_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_token

    @token.setter
    def token(self, value):
        self.raw_data['token'] = value
        self._field_token = FIELD_TO_PARSE

    @property
    def key_command(self):
        if self._field_key_command is FIELD_TO_PARSE:
            if 'key_command' not in self.raw_data:
                self._field_key_command = None
            else:
                key_command = self.raw_data['key_command']
                if not isinstance(key_command, str):
                    self.raise_error('must be a string')

                self._field_key_command = key_command

        return self._field_key_command

    @key_command.setter
    def key_command(self, value):
        self.raw_data['key_command'] = value
        self._field_key_command = FIELD_TO_PARSE

    @property
    def token_command(self):
        if self._field_token_command is FIELD_TO_PARSE:
            if 'token_command' not in self.raw_data:
                self._field_token_command = None
            else:
                token_command = self.raw_data['token_command']
                if not isinstance(token_command, str):
                    self.raise_error('must be a string')

                self._field_token_command = token_command

        return self._field_token_command

    @token_command.setter
    def token_command(self, value):
        self.raw_data['token_command'] = value
        self._field_token_command = FIELD_TO_PARSE


class DynamicDConfig(LazilyParsedConfig):
    def __init__(self, *args, trust_blocked_command_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._trust_blocked_command_fields = trust_blocked_command_fields or set()

        self._field_llm_api_key = FIELD_TO_PARSE
        self._field_llm_api_key_command = FIELD_TO_PARSE

    def parse_fields(self):
        # Keep command-backed llm key resolution lazy.
        parse_config(self.llm_api_key_command)

    @property
    def llm_api_key(self):
        if self._field_llm_api_key is FIELD_TO_PARSE:
            literal_key = None
            if 'llm_api_key' in self.raw_data:
                literal_key = self.raw_data['llm_api_key']
                if not isinstance(literal_key, str):
                    self.raise_error('must be a string')

            command = self.llm_api_key_command

            try:
                self._field_llm_api_key = resolve_required_secret(
                    field_path='dynamicd.llm_api_key',
                    command=command,
                    literal=literal_key,
                    env_var='ANTHROPIC_API_KEY',
                    env_value=get_dynamicd_llm_api_key(),
                    env_label='DD_DYNAMICD_LLM_API_KEY|ANTHROPIC_API_KEY',
                    command_blocked_by_trust='dynamicd.llm_api_key_command' in self._trust_blocked_command_fields,
                )
            except SecretResolutionError as e:
                self.raise_error(str(e))

        return self._field_llm_api_key

    @llm_api_key.setter
    def llm_api_key(self, value):
        self.raw_data['llm_api_key'] = value
        self._field_llm_api_key = FIELD_TO_PARSE

    @property
    def llm_api_key_command(self):
        if self._field_llm_api_key_command is FIELD_TO_PARSE:
            if 'llm_api_key_command' not in self.raw_data:
                self._field_llm_api_key_command = None
            else:
                llm_api_key_command = self.raw_data['llm_api_key_command']
                if not isinstance(llm_api_key_command, str):
                    self.raise_error('must be a string')

                self._field_llm_api_key_command = llm_api_key_command

        return self._field_llm_api_key_command

    @llm_api_key_command.setter
    def llm_api_key_command(self, value):
        self.raw_data['llm_api_key_command'] = value
        self._field_llm_api_key_command = FIELD_TO_PARSE


class TerminalConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_styles = FIELD_TO_PARSE

    @property
    def styles(self):
        if self._field_styles is FIELD_TO_PARSE:
            if 'styles' in self.raw_data:
                styles = self.raw_data['styles']
                if not isinstance(styles, dict):
                    self.raise_error('must be a table')

                self._field_styles = StylesConfig(styles, self.steps + ('styles',))
            else:
                styles = {}
                self.raw_data['styles'] = styles
                self._field_styles = StylesConfig(styles, self.steps + ('styles',))

        return self._field_styles

    @styles.setter
    def styles(self, value):
        self.raw_data['styles'] = value
        self._field_styles = FIELD_TO_PARSE


class StylesConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_info = FIELD_TO_PARSE
        self._field_success = FIELD_TO_PARSE
        self._field_error = FIELD_TO_PARSE
        self._field_warning = FIELD_TO_PARSE
        self._field_waiting = FIELD_TO_PARSE
        self._field_debug = FIELD_TO_PARSE
        self._field_spinner = FIELD_TO_PARSE

    @property
    def info(self):
        if self._field_info is FIELD_TO_PARSE:
            if 'info' in self.raw_data:
                info = self.raw_data['info']
                if not isinstance(info, str):
                    self.raise_error('must be a string')

                self._field_info = info
            else:
                self._field_info = self.raw_data['info'] = 'bold'

        return self._field_info

    @info.setter
    def info(self, value):
        self.raw_data['info'] = value
        self._field_info = FIELD_TO_PARSE

    @property
    def success(self):
        if self._field_success is FIELD_TO_PARSE:
            if 'success' in self.raw_data:
                success = self.raw_data['success']
                if not isinstance(success, str):
                    self.raise_error('must be a string')

                self._field_success = success
            else:
                self._field_success = self.raw_data['success'] = 'bold cyan'

        return self._field_success

    @success.setter
    def success(self, value):
        self.raw_data['success'] = value
        self._field_success = FIELD_TO_PARSE

    @property
    def error(self):
        if self._field_error is FIELD_TO_PARSE:
            if 'error' in self.raw_data:
                error = self.raw_data['error']
                if not isinstance(error, str):
                    self.raise_error('must be a string')

                self._field_error = error
            else:
                self._field_error = self.raw_data['error'] = 'bold red'

        return self._field_error

    @error.setter
    def error(self, value):
        self.raw_data['error'] = value
        self._field_error = FIELD_TO_PARSE

    @property
    def warning(self):
        if self._field_warning is FIELD_TO_PARSE:
            if 'warning' in self.raw_data:
                warning = self.raw_data['warning']
                if not isinstance(warning, str):
                    self.raise_error('must be a string')

                self._field_warning = warning
            else:
                self._field_warning = self.raw_data['warning'] = 'bold yellow'

        return self._field_warning

    @warning.setter
    def warning(self, value):
        self.raw_data['warning'] = value
        self._field_warning = FIELD_TO_PARSE

    @property
    def waiting(self):
        if self._field_waiting is FIELD_TO_PARSE:
            if 'waiting' in self.raw_data:
                waiting = self.raw_data['waiting']
                if not isinstance(waiting, str):
                    self.raise_error('must be a string')

                self._field_waiting = waiting
            else:
                self._field_waiting = self.raw_data['waiting'] = 'bold magenta'

        return self._field_waiting

    @waiting.setter
    def waiting(self, value):
        self.raw_data['waiting'] = value
        self._field_waiting = FIELD_TO_PARSE

    @property
    def debug(self):
        if self._field_debug is FIELD_TO_PARSE:
            if 'debug' in self.raw_data:
                debug = self.raw_data['debug']
                if not isinstance(debug, str):
                    self.raise_error('must be a string')

                self._field_debug = debug
            else:
                self._field_debug = self.raw_data['debug'] = 'bold'

        return self._field_debug

    @debug.setter
    def debug(self, value):
        self.raw_data['debug'] = value
        self._field_debug = FIELD_TO_PARSE

    @property
    def spinner(self):
        if self._field_spinner is FIELD_TO_PARSE:
            if 'spinner' in self.raw_data:
                spinner = self.raw_data['spinner']
                if not isinstance(spinner, str):
                    self.raise_error('must be a string')

                self._field_spinner = spinner
            else:
                self._field_spinner = self.raw_data['spinner'] = 'simpleDotsScrolling'

        return self._field_spinner

    @spinner.setter
    def spinner(self, value):
        self.raw_data['spinner'] = value
        self._field_spinner = FIELD_TO_PARSE
