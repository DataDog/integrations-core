import re

from datadog_checks.base import ConfigurationError


def normalize_pattern(pattern):
    # Ensure dots are treated as literal
    pattern = pattern.replace('\\.', '.').replace('.', '\\.')
    # Get rid of any explicit start modifiers
    pattern = pattern.lstrip('^')
    # We only search on `<CATEGORY>.<KEY>`
    pattern = re.sub(r'^sonarqube(\\.)?', '', pattern)
    # Match from the start by default
    pattern = '^{}'.format(pattern)
    return pattern


class SonarqubeConfig:
    def __init__(self, instance, log):
        self._instance = instance
        self._log = log
        self.projects = None
        self.web_endpoint = None
        self.tags = None
        self.default_tag = None
        self.default_metrics_limit = None
        self.default_metrics_include = None
        self.default_metrics_exclude = None
        self._validate_web_endpoint()
        self._validate_tags()
        self._validate_projects()
        if self.projects is None:
            self._validate_default_tag()
            self._validate_default_include()
            self._validate_default_exclude()
            self._validate_components()
        if self.projects is None:
            raise ConfigurationError('`projects` setting must be defined')

    def _validate_config(self):
        self._validate_web_endpoint()
        self._validate_tags()
        self._validate_projects()
        if self.projects is None:
            self._validate_default_tag()
            self._validate_default_include()
            self._validate_default_exclude()
            self._validate_components()

    def _validate_web_endpoint(self):
        self.web_endpoint = self._instance.get('web_endpoint')
        if self.web_endpoint is None:
            raise ConfigurationError('`web_endpoint` setting must be defined')
        if not isinstance(self.web_endpoint, str):
            raise ConfigurationError('`web_endpoint` setting must be a string')

    def _validate_tags(self):
        tags = self._instance.get('tags', [])
        if not isinstance(tags, list):
            raise ConfigurationError('`tags` setting must be a list')
        self.tags = ['endpoint:{}'.format(self.web_endpoint)] + tags

    def _validate_projects(self):
        self._log.debug('validating `projects`: %s', self._instance)
        projects = self._instance.get('projects', None)
        if projects is not None and isinstance(projects, dict):
            self._log.debug('`projects` found in config: %s', projects)
            self.projects = {'keys': [], 'discovery': projects.get('discovery', {})}
            self.default_tag = projects.get('default_tag', 'component')
            self._log.debug('default_tag: %s', self.default_tag)
            self.default_metrics_limit = projects.get('default_metrics_limit', 100)
            self._log.debug('default_metrics_limit: %s', self.default_metrics_limit)
            self.default_metrics_include = projects.get('default_metrics_include', ['^.*'])
            self._log.debug('default_metrics_include: %s', self.default_metrics_include)
            self.default_metrics_exclude = projects.get('default_metrics_exclude', ['^.*\\.new_.*'])
            self._log.debug('default_metrics_exclude: %s', self.default_metrics_exclude)
            keys = projects.get('keys', [])
            self._log.debug('keys: %s', keys)
            for keys_item in keys:
                if isinstance(keys_item, dict):
                    self.projects['keys'].append({list(keys_item.keys())[0]: list(keys_item.values())[0]})
                elif isinstance(keys_item, str):
                    self.projects['keys'].append({keys_item: {}})
                else:
                    self._log.warning('`project` key setting must be a string or a dict: %s', keys_item)
                    raise ConfigurationError('`project` key setting must be a string or a dict')
            self._log.debug("projects: %s", self.projects)

    def _validate_default_tag(self):
        self.default_tag = self._instance.get('default_tag', 'component')
        if not isinstance(self.default_tag, str):
            raise ConfigurationError('`default_tag` setting must be a string')

    def _validate_default_include(self):
        default_include = self._instance.get('default_include', [])
        if not isinstance(default_include, list):
            raise ConfigurationError('`default_include` setting must be a list')

    def _validate_default_exclude(self):
        default_exclude = self._instance.get('default_exclude', [])
        if not isinstance(default_exclude, list):
            raise ConfigurationError('`default_exclude` setting must be a list')

    def _validate_components(self):
        self._log.debug('validating `components`: %s', self._instance)
        components = self._instance.get('components', None)
        if components is not None and isinstance(components, dict):
            self._log.debug('`components` found in config: %s', components)
            self.projects = {'keys': []}
            default_tag = self._instance.get('default_tag', 'component')
            self._log.debug('default_tag: %s', default_tag)
            self.default_metrics_limit = 100
            self._log.debug('default_metrics_limit: %s', self.default_metrics_limit)
            self.default_metrics_include = [
                normalize_pattern(item) for item in self._instance.get('default_include', [])
            ]
            self.default_metrics_include = self.default_metrics_include if self.default_metrics_include else [r'.*']
            self._log.debug('default_metrics_include: %s', self.default_metrics_include)
            self.default_metrics_exclude = [
                normalize_pattern(item) for item in self._instance.get('default_exclude', [])
            ]
            self.default_metrics_exclude = self.default_metrics_exclude + [r'^.*\.new_.*']
            self._log.debug('default_metrics_exclude: %s', self.default_metrics_exclude)
            for component_key, component_config in components.items():
                self._log.debug('component_key: %s, component_config: %s', component_key, component_config)
                component_config['tag'] = component_config.get('tag', default_tag)
                component_config['metrics'] = {}
                include = component_config.get('include', None)
                exclude = component_config.get('exclude', None)
                if include or exclude:
                    component_config['metrics']['discovery'] = {}
                    if include is not None:
                        component_config['metrics']['discovery']['include'] = [
                            normalize_pattern(item) for item in include
                        ]
                    if exclude is not None:
                        component_config['metrics']['discovery']['exclude'] = [
                            normalize_pattern(item) for item in exclude
                        ] + [r'^.*\.new_.*']
                self.projects['keys'].append({component_key: component_config})
            self._log.debug(self.projects)
