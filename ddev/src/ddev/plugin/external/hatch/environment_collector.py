import os
from functools import cached_property

from hatch.env.collectors.plugin.interface import EnvironmentCollectorInterface


class DatadogChecksEnvironmentCollector(EnvironmentCollectorInterface):
    PLUGIN_NAME = 'datadog-checks'

    @cached_property
    def in_core_repo(self):
        return (self.root.parent / 'datadog_checks_base').is_dir()

    @cached_property
    def is_base_package(self):
        return self.root.name == 'datadog_checks_base'

    @cached_property
    def is_test_package(self):
        return self.root.name == 'datadog_checks_dev'

    @cached_property
    def is_dev_package(self):
        return self.root.name == 'ddev'

    @cached_property
    def package_directory(self):
        name = self.root.name
        if name == 'ddev':
            return 'src/ddev'

        if name == 'datadog_checks_base':
            directory = 'base'
        elif name == 'datadog_checks_dev':
            directory = 'dev'
        elif name == 'datadog_checks_downloader':
            directory = 'downloader'
        else:
            directory = name.replace('-', '_')

        return f'datadog_checks/{directory}'

    @cached_property
    def check_types(self):
        return self.config.get('check-types', False)

    @cached_property
    def mypy_args(self):
        return self.config.get('mypy-args', [])

    @cached_property
    def mypy_deps(self):
        return self.config.get('mypy-deps', [])

    @cached_property
    def test_package_install_command(self):
        if not self.in_core_repo:
            return self.pip_install_command('datadog-checks-dev')
        elif not (self.is_test_package or self.is_dev_package):
            return self.pip_install_command('-e', '../datadog_checks_dev')

    def base_package_install_command(self, features):
        from ddev.testing.constants import TestEnvVars

        if base_package_version := os.environ.get(TestEnvVars.BASE_PACKAGE_VERSION):
            return self.pip_install_command(self.format_base_package(features, version=base_package_version))
        elif not self.in_core_repo:
            return self.pip_install_command(self.format_base_package(features))
        elif not (self.is_base_package or self.is_dev_package):
            return self.pip_install_command('-e', self.format_base_package(features, local=True))

    @staticmethod
    def format_base_package(features, version='', local=False):
        if not features:
            features = ['deps']

        base_package = '../datadog_checks_base' if local else 'datadog-checks-base'
        formatted = f'{base_package}[{",".join(sorted(features))}]'
        if version:
            formatted += f'=={version}'

        return formatted

    @staticmethod
    def pip_install_command(*args):
        return f'python -m pip install --disable-pip-version-check {{verbosity:flag:-1}} {" ".join(args)}'

    def finalize_config(self, config):

        for env_name, env_config in config.items():
            is_template_env = env_name == 'default'
            is_test_env = env_config.setdefault('test-env', is_template_env)
            is_e2e_env = env_config.setdefault('e2e-env', is_template_env)
            env_config.setdefault('benchmark-env', env_name == 'bench')
            env_config.setdefault('latest-env', env_name == 'latest')
            if not (is_test_env or is_e2e_env):
                continue

            if not (self.is_test_package or self.is_dev_package):
                env_config.setdefault('features', ['deps'])

            base_package_features = env_config.get('base-package-features', self.config.get('base-package-features'))
            install_commands = []
            if install_command := self.base_package_install_command(base_package_features):
                install_commands.append(install_command)

            if self.test_package_install_command:
                install_commands.append(self.test_package_install_command)

            scripts = env_config.setdefault('scripts', {})
            scripts['_dd-install-packages'] = install_commands
            env_config.setdefault('post-install-commands', []).insert(0, '_dd-install-packages')

            scripts['_dd-test'] = ['pytest -vv --benchmark-skip {args:tests}']
            scripts['_dd-test-cov'] = [
                f'pytest -vv --benchmark-skip --cov {self.package_directory} --cov tests '
                f'--cov-config=../.coveragerc --cov-report= --cov-append {{args:tests}}',
            ]
            scripts['_dd-benchmark'] = ['pytest -vv --benchmark-only --benchmark-cprofile=tottime {args:tests}']

            # Set defaults that will be called but allow users to override while
            # retaining access to them for reuse
            scripts.setdefault('test', '_dd-test')
            scripts.setdefault('test-cov', '_dd-test-cov')
            scripts.setdefault('benchmark', '_dd-benchmark')

    def get_initial_config(self):
        settings_dir = '.' if self.is_dev_package else '..'
        lint_env = {
            'detached': True,
            'scripts': {
                'style': [
                    f'black --config {settings_dir}/pyproject.toml --check --diff .',
                    f'ruff --config {settings_dir}/pyproject.toml .',
                ],
                'fmt': [
                    f'black . --config {settings_dir}/pyproject.toml',
                    f'ruff --config {settings_dir}/pyproject.toml --fix .',
                    'python -c "print(\'\\n[NOTE] ruff may still report style errors for things '
                    'black cannot fix, these will need to be fixed manually.\')"',
                    'style',
                ],
                'all': ['style'],
            },
            # We pin deps in order to make CI more stable/reliable.
            'dependencies': [
                'black==22.12.0',
                'ruff==0.0.257',
                # Keep in sync with: /datadog_checks_base/pyproject.toml
                'pydantic==2.0.2',
            ],
        }
        config = {'lint': lint_env}

        if self.check_types:
            lint_env['scripts']['typing'] = [
                f'mypy --config-file=../pyproject.toml {" ".join(self.mypy_args)}'.rstrip()
            ]
            lint_env['scripts']['all'].append('typing')
            lint_env['dependencies'].extend(
                [
                    # TODO: remove extra when we drop Python 2
                    'mypy[python2]==0.910; python_version<"3"',
                    'mypy[python2]==1.3.0; python_version>"3"',
                    # TODO: remove these when drop Python 2 and replace with --install-types --non-interactive
                    'types-python-dateutil==2.8.2',
                    'types-pyyaml==5.4.10',
                    'types-requests==2.25.11',
                    'types-simplejson==3.17.5',
                    'types-six==1.16.2',
                ]
            )
            lint_env['dependencies'].extend(self.mypy_deps)

        return config
