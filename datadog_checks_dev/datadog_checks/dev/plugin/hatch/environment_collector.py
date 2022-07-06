import os
from functools import cached_property, lru_cache

from hatch.env.collectors.plugin.interface import EnvironmentCollectorInterface


class DatadogChecksEnvironmentCollector(EnvironmentCollectorInterface):
    PLUGIN_NAME = 'datadog-checks'

    @cached_property
    def in_core_repo(self):
        return (self.root.parent / 'datadog_checks_base').is_dir()

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
    def dev_package_install_command(self):
        if not self.in_core_repo:
            return self.pip_install_command('datadog-checks-dev')
        elif self.root.name != 'datadog_checks_dev':
            return self.pip_install_command('-e', '../datadog_checks_dev')

    @lru_cache(maxsize=None)
    def base_package_install_command(self, features):
        if not self.in_core_repo or os.environ.get('BASE_PACKAGE_FORCE_UNPINNED'):
            return self.pip_install_command(self.format_base_package(features))
        elif base_package_version := os.environ.get('BASE_PACKAGE_FORCE_VERSION'):
            return self.pip_install_command(self.format_base_package(features, version=base_package_version))
        elif self.root.name != 'datadog_checks_base':
            return self.pip_install_command('-e', f'../{self.format_base_package(features, local=True)}')

    @staticmethod
    def format_base_package(features, version='', local=False):
        if not features:
            features = ['deps']

        base_package = 'datadog_checks_base' if local else 'datadog-checks-base'
        formatted = f'{base_package}[{",".join(sorted(features))}]'
        if version:
            formatted = f'=={version}'

        return formatted

    @staticmethod
    def pip_install_command(*args):
        return f'python -m pip install --disable-pip-version-check -q {" ".join(args)}'

    def finalize_config(self, config):
        for env_name, env_config in config.items():
            is_template_env = env_name == 'default'
            is_test_env = env_config.setdefault('test-env', is_template_env)
            is_e2e_env = env_config.setdefault('e2e-env', is_template_env)
            if not (is_test_env or is_e2e_env):
                continue

            scripts = env_config.setdefault('scripts', {})

            install_commands = []
            if install_command := self.base_package_install_command(config.get('base-package-features')):
                install_commands.append(install_command)
            if self.dev_package_install_command:
                install_commands.append(self.dev_package_install_command)

            scripts['dd-install-packages'] = install_commands
            env_config.setdefault('post-install-commands', []).insert(0, 'dd-install-packages')

            scripts['dd-test'] = ['pytest -v --benchmark-skip {args:tests}']
            scripts['dd-benchmark'] = ['pytest -v --benchmark-only --benchmark-cprofile=tottime {args:tests}']

            # Set defaults that will be called but allow users to override while
            # retaining access to them for reuse
            scripts.setdefault('test', 'dd-test')
            scripts.setdefault('benchmark', 'dd-benchmark')

    def get_initial_config(self):
        lint_env = {
            'detached': True,
            'scripts': {
                'style': [
                    'flake8 --config=../.flake8 .',
                    'black --config ../pyproject.toml --check --diff .',
                    'isort --settings-path ../pyproject.toml --check-only --diff .',
                ],
                'fmt': [
                    'isort . --settings-path ../pyproject.toml ',
                    'black . --config ../pyproject.toml',
                    'python -c "print(\'\\n[NOTE] flake8 may still report style errors for things '
                    'black cannot fix, these will need to be fixed manually.\')"',
                    'style',
                ],
                'all': ['style'],
            },
            # We pin deps in order to make CI more stable/reliable.
            'dependencies': [
                'black==22.3.0',
                'flake8==4.0.1',
                'flake8-bugbear==21.9.2',
                'flake8-logging-format==0.6.0',
                # Keep in sync with: /datadog_checks_base/pyproject.toml
                'pydantic==1.8.2',
            ],
        }
        config = {'lint': lint_env}

        if self.check_types:
            lint_env['scripts']['typing'] = [f'mypy --config-file=../mypy.ini {" ".join(self.mypy_args)}'.rstrip()]
            lint_env['scripts']['all'].append('typing')
            lint_env['dependencies'].extend(
                [
                    # TODO: remove extra when we drop Python 2
                    'mypy[python2]==0.910',
                    # TODO: remove these when drop Python 2 and replace with --install-types --non-interactive
                    'types-python-dateutil==2.8.2',
                    'types-pyyaml==5.4.10',
                    'types-requests==2.25.11',
                    'types-six==1.16.2',
                ]
            )
            lint_env['dependencies'].extend(self.mypy_deps)

        return config
