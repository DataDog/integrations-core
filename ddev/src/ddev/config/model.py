# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

FIELD_TO_PARSE = object()


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

    def raise_error(self, message, *, extra_steps=(), stack_depth=1):
        import inspect

        # raise_error will be the current frame i.e., sys._getframe(0) as the stack is inspected here
        #
        # In order to get details about the actual exception point, the first entry of the stack is used
        #   by default i.e., sys._getframe(1). This can be extracted using index 1 of inspect.stack() response
        #
        # Providing an option to specify the stack depth will allow getting the correct function deatils inspite
        #   of abstracting error checks
        #
        # In this case to use stack depth of 2 thereby providing the correct function names for calling functions
        #   that use _check_string_instance and _check_dict_instance which inturn uses raise_error
        field = inspect.stack()[stack_depth].function
        raise ConfigurationError(message, location=" -> ".join([*self.steps, field, *extra_steps]))

    def _check_string_instance(self, obj, extra_steps=()):
        if not isinstance(obj, str):
            self.raise_error("must be a string", stack_depth=2, extra_steps=extra_steps)

    def _check_dict_instance(self, obj, extra_steps=()):
        if not isinstance(obj, dict):
            self.raise_error("must be a table", stack_depth=2, extra_steps=extra_steps)


class RootConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    @property
    def repo(self):
        if self._field_repo is FIELD_TO_PARSE:
            repo = self.raw_data['repo'] if 'repo' in self.raw_data else 'core'
            self._check_string_instance(obj=repo)
            if repo not in self.repos:
                self.raise_error('unknown repository')

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
            self._check_string_instance(obj=agent)
            if agent not in self.agents:
                self.raise_error('unknown Agent')

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
            self._check_string_instance(obj=org)
            if org not in self.orgs:
                self.raise_error('unknown Org')

            self.raw_data['org'] = org
            self._field_org = OrgConfig({'name': org, 'config': self.orgs[org]}, ('org',))

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
                self._check_dict_instance(obj=repos)
                if not repos:
                    self.raise_error('must define at least one repository')

                for name, data in repos.items():
                    self._check_string_instance(obj=data, extra_steps=(name,))

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
                self._check_dict_instance(obj=agents)
                if not agents:
                    self.raise_error('must define at least one Agent')

                for name, data in agents.items():
                    self._check_dict_instance(obj=data, extra_steps=(name,))

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
                self._check_dict_instance(obj=orgs)
                if not orgs:
                    self.raise_error('must define at least one Org')

                for name, data in orgs.items():
                    self._check_dict_instance(obj=data, extra_steps=(name,))

                self._field_orgs = orgs
            else:
                self._field_orgs = self.raw_data['orgs'] = {
                    'default': {
                        'api_key': os.getenv('DD_API_KEY', ''),
                        'app_key': os.getenv('DD_APP_KEY', ''),
                        'site': os.getenv('DD_SITE', 'datadoghq.com'),
                        'dd_url': os.getenv('DD_DD_URL', 'https://app.datadoghq.com'),
                        'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL', ''),
                    },
                }

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
                self._check_dict_instance(obj=github)
            else:
                github = {}
                self.raw_data['github'] = github
            self._field_github = GitHubConfig(github, ('github',))

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
                self._check_dict_instance(obj=pypi)
            else:
                pypi = {}
                self.raw_data['pypi'] = pypi
            self._field_pypi = PyPIConfig(pypi, ('pypi',))

        return self._field_pypi

    @pypi.setter
    def pypi(self, value):
        self.raw_data['pypi'] = value
        self._field_pypi = FIELD_TO_PARSE

    @property
    def trello(self):
        # TODO: Remove trello
        if self._field_trello is FIELD_TO_PARSE:
            if 'trello' in self.raw_data:
                trello = self.raw_data['trello']
                self._check_dict_instance(obj=trello)
            else:
                trello = {}
                self.raw_data['trello'] = trello
            self._field_trello = TrelloConfig(trello, ('trello',))

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
                self._check_dict_instance(obj=terminal)
            else:
                terminal = {}
                self.raw_data['terminal'] = terminal
            self._field_terminal = TerminalConfig(terminal, ('terminal',))

        return self._field_terminal

    @terminal.setter
    def terminal(self, value):
        self.raw_data['terminal'] = value
        self._field_terminal = FIELD_TO_PARSE


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
                self._check_string_instance(obj=name)
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
                self._check_string_instance(obj=path)
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
                self._check_string_instance(obj=name)
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
                self._check_dict_instance(obj=config)
                self._field_config = config
            else:
                self.raise_error('required field')

        return self._field_config

    @config.setter
    def config(self, value):
        self.raw_data['config'] = value
        self._field_config = FIELD_TO_PARSE


class OrgConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_name = FIELD_TO_PARSE
        self._field_config = FIELD_TO_PARSE

    @property
    def name(self):
        if self._field_name is FIELD_TO_PARSE:
            if 'name' in self.raw_data:
                name = self.raw_data['name']
                self._check_string_instance(obj=name)
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
                self._check_dict_instance(obj=config)
                self._field_config = config
            else:
                self.raise_error('required field')

        return self._field_config

    @config.setter
    def config(self, value):
        self.raw_data['config'] = value
        self._field_config = FIELD_TO_PARSE


class GitHubConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_user = FIELD_TO_PARSE
        self._field_token = FIELD_TO_PARSE

    @property
    def user(self):
        if self._field_user is FIELD_TO_PARSE:
            if 'user' in self.raw_data:
                user = self.raw_data['user']
                self._check_string_instance(obj=user)
                self._field_user = user
            else:
                self._field_user = self.raw_data['user'] = os.environ.get('DD_GITHUB_USER', '')

        return self._field_user

    @user.setter
    def user(self, value):
        self.raw_data['user'] = value
        self._field_user = FIELD_TO_PARSE

    @property
    def token(self):
        if self._field_token is FIELD_TO_PARSE:
            if 'token' in self.raw_data:
                token = self.raw_data['token']
                self._check_string_instance(obj=token)
                self._field_token = token
            else:
                self._field_token = self.raw_data['token'] = os.environ.get('DD_GITHUB_TOKEN', '')

        return self._field_token

    @token.setter
    def token(self, value):
        self.raw_data['token'] = value
        self._field_token = FIELD_TO_PARSE


class PyPIConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_user = FIELD_TO_PARSE
        self._field_auth = FIELD_TO_PARSE

    @property
    def user(self):
        if self._field_user is FIELD_TO_PARSE:
            if 'user' in self.raw_data:
                user = self.raw_data['user']
                self._check_string_instance(obj=user)
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
            if 'auth' in self.raw_data:
                auth = self.raw_data['auth']
                self._check_string_instance(obj=auth)
                self._field_auth = auth
            else:
                self._field_auth = self.raw_data['auth'] = ''

        return self._field_auth

    @auth.setter
    def auth(self, value):
        self.raw_data['auth'] = value
        self._field_auth = FIELD_TO_PARSE


class TrelloConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_key = FIELD_TO_PARSE
        self._field_token = FIELD_TO_PARSE

    @property
    def key(self):
        if self._field_key is FIELD_TO_PARSE:
            if 'key' in self.raw_data:
                key = self.raw_data['key']
                self._check_string_instance(obj=key)
                self._field_key = key
            else:
                self._field_key = self.raw_data['key'] = ''

        return self._field_key

    @key.setter
    def key(self, value):
        self.raw_data['key'] = value
        self._field_key = FIELD_TO_PARSE

    @property
    def token(self):
        if self._field_token is FIELD_TO_PARSE:
            if 'token' in self.raw_data:
                token = self.raw_data['token']
                self._check_string_instance(obj=token)
                self._field_token = token
            else:
                self._field_token = self.raw_data['token'] = ''

        return self._field_token

    @token.setter
    def token(self, value):
        self.raw_data['token'] = value
        self._field_token = FIELD_TO_PARSE


class TerminalConfig(LazilyParsedConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._field_styles = FIELD_TO_PARSE

    @property
    def styles(self):
        if self._field_styles is FIELD_TO_PARSE:
            if 'styles' in self.raw_data:
                styles = self.raw_data['styles']
                self._check_dict_instance(obj=styles)
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
                self._check_string_instance(obj=info)
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
                self._check_string_instance(obj=success)
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
                self._check_string_instance(obj=error)
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
                self._check_string_instance(obj=warning)
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
                self._check_string_instance(obj=waiting)
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
                self._check_string_instance(obj=debug)
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
                self._check_string_instance(obj=spinner)
                self._field_spinner = spinner
            else:
                self._field_spinner = self.raw_data['spinner'] = 'simpleDotsScrolling'

        return self._field_spinner

    @spinner.setter
    def spinner(self, value):
        self.raw_data['spinner'] = value
        self._field_spinner = FIELD_TO_PARSE
