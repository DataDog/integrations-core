# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os

import tox
import tox.config

STYLE_CHECK_ENV_NAME = 'style'
STYLE_FORMATTER_ENV_NAME = 'format_style'
STYLE_FLAG = 'dd_check_style'
TYPES_FLAG = 'dd_check_types'
MYPY_ARGS_OPTION = 'dd_mypy_args'
MYPY_ADDITIONAL_DEPS = 'dd_mypy_deps'
E2E_READY_CONDITION = 'e2e ready if'
FIX_DEFAULT_ENVDIR_FLAG = 'ensure_default_envdir'

# Style deps:
# We pin deps in order to make CI more stable/reliable.
ISORT_DEP = 'isort==5.10.1'
BLACK_DEP = 'black==22.8.0'
FLAKE8_DEP = 'flake8==5.0.4'
FLAKE8_BUGBEAR_DEP = 'flake8-bugbear==22.9.11'
FLAKE8_LOGGING_FORMAT_DEP = 'flake8-logging-format==0.7.5'
# TODO: remove extra when we drop Python 2
MYPY_DEP = 'mypy[python2]==0.910'
# TODO: when we drop Python 2 and replace with --install-types --non-interactive
TYPES_DEPS = [
    'types-PyYAML==5.4.10',
    'types-python-dateutil==2.8.2',
    'types_requests==2.25.11',
    'types_six==1.16.2',
    'types-simplejson==3.17.5',
]
PYDANTIC_DEP = 'pydantic==1.10.2'  # Keep in sync with: /datadog_checks_base/datadog_checks/data/agent_requirements.in


@tox.hookimpl
def tox_configure(config):
    """
    For more info, see: https://tox.readthedocs.io/en/latest/plugins.html
    For an example, see: https://github.com/tox-dev/tox-travis
    """
    sections = config._cfg.sections
    base_testenv = sections.get('testenv', {})

    # Default to false so:
    # 1. we don't affect other projects using tox
    # 2. check migrations can happen gradually
    if str(base_testenv.get(STYLE_FLAG, 'false')).lower() == 'true':
        # Disable flake8 since we already include that
        config.envlist[:] = [env for env in config.envlist if not env.endswith('flake8')]

        make_envconfig = get_make_envconfig()
        reader = get_reader(config)

        add_style_checker(config, sections, make_envconfig, reader)
        add_style_formatter(config, sections, make_envconfig, reader)

    # Workaround for https://github.com/tox-dev/tox/issues/1593
    #
    # Do this only after all dynamic environments have been created
    if str(base_testenv.get(FIX_DEFAULT_ENVDIR_FLAG, 'false')).lower() == 'true':
        for env_name, env_config in config.envconfigs.items():
            if env_config.envdir == config.toxinidir:
                env_config.envdir = config.toxworkdir / env_name
                env_config.envlogdir = env_config.envdir / 'log'
                env_config.envtmpdir = env_config.envdir / 'tmp'

    # Conditionally set 'e2e ready' depending on env variables or environment markers
    for cfg in config.envconfigs.values():
        if E2E_READY_CONDITION not in cfg.description:
            continue

        data, var = cfg.description.split(' if ')
        var = var.strip()

        if var in os.environ:
            cfg.description = data
        else:
            from packaging.markers import InvalidMarker, Marker

            try:
                marker = Marker(var)
            except InvalidMarker:
                cfg.description = '{} is missing'.format(var)
            else:
                if marker.evaluate():
                    cfg.description = data
                else:
                    cfg.description = 'environment does not match: {}'.format(var)

    # Next two sections hack the sequencing of Tox's package installation.
    #
    # Tox package installation order:
    #   1. Install `deps`, which typically looks like:
    #        deps =
    #            -e../datadog_checks_base[deps]
    #            -rrequirements-dev.txt
    #   2. Install check package, editable mode
    #   3. Execute `commands` which typically looks like:
    #        commands =
    #            pip install -r requirements.in
    #            pytest -v {posargs} --benchmark-skip

    # Forcibly remove any dependencies from the `tox.ini` deps that are meant to be unpinned
    # This should have the effect of relying on a package's setup.py for installation
    # We manually pip install `datadog_checks_base[deps]` to ensure that test dependencies are installed,
    # but this should have no effect on the version of the base package.
    force_unpinned = os.getenv('TOX_FORCE_UNPINNED', None)
    if force_unpinned:
        for env in config.envlist:
            deps = [d for d in config.envconfigs[env].deps if force_unpinned not in d.name]
            config.envconfigs[env].deps = deps
            config.envconfigs[env].commands.insert(0, 'pip install datadog_checks_base[deps]'.split())

    # Workaround for tox's `--force-dep` having limited functionality when package is already installed.
    # Primarily meant for pinning datadog-checks-base to a specific version, but could be
    # applied to other packages in the future. Since we typically install checks base via
    # editable mode, we need to force the reinstall to ensure that the PyPI package installs.
    force_install = os.getenv('TOX_FORCE_INSTALL', None)
    if force_install:
        command = f'pip install --force-reinstall {force_install}'.split()

        for env in config.envlist:
            config.envconfigs[env].commands.insert(0, command)

    # This will inherit the configuration of `[testenv]` and if it doesn't support the platform then for some reason
    # running a user defined environment and a generated environment at the same time (e.g. `tox -e py38,style`) will
    # attempt to use the Python executable in the `.package` environment but will fail because the environment has
    # not been created due to the platform mismatch.
    if '.package' in config.envconfigs:
        config.envconfigs['.package'].platform = 'linux|darwin|win32'


def add_style_checker(config, sections, make_envconfig, reader):
    # testenv:style
    section = '{}{}'.format(tox.config.testenvprefix, STYLE_CHECK_ENV_NAME)

    dependencies = [
        FLAKE8_DEP,
        FLAKE8_BUGBEAR_DEP,
        FLAKE8_LOGGING_FORMAT_DEP,
        BLACK_DEP,
        ISORT_DEP,
        PYDANTIC_DEP,
    ] + TYPES_DEPS

    commands = [
        'flake8 --config=../.flake8 .',
        'black --config ../pyproject.toml --check --diff .',
        'isort --settings-path ../pyproject.toml --check-only --diff .',
    ]

    if sections['testenv'].get(TYPES_FLAG, 'false').lower() == 'true':
        # For command line options accepted by mypy, see: https://mypy.readthedocs.io/en/stable/command_line.html
        # Each integration should explicitly specify its options and which files it'd like to type check, which is
        # why we're defaulting to 'no arguments' by default.
        mypy_args = sections['testenv'].get(MYPY_ARGS_OPTION, '')
        mypy_deps = sections['testenv'].get(MYPY_ADDITIONAL_DEPS, "").splitlines()

        # Allow using multiple lines for enhanced readability in case of large amount of options/files to check.
        mypy_args = mypy_args.replace('\n', ' ')

        dependencies.append(MYPY_DEP)
        for mypy_dep in mypy_deps:
            dependencies.append(mypy_dep)

        commands.append('mypy --config-file=../mypy.ini {}'.format(mypy_args))

    sections[section] = {
        'platform': 'linux|darwin|win32',
        # Tools used here require Python 3.6+
        # more info: https://github.com/ambv/black/issues/439#issuecomment-411429907
        'basepython': 'python3',
        'skip_install': 'true',
        'deps': '\n'.join(dependencies),
        'commands': '\n'.join(commands),
    }

    # Always add the environment configurations
    config.envconfigs[STYLE_CHECK_ENV_NAME] = make_envconfig(
        config, STYLE_CHECK_ENV_NAME, section, reader._subs, config
    )

    # Intentionally add to envlist when seeing what is available
    if config.option.env is None or config.option.env == STYLE_CHECK_ENV_NAME:
        config.envlist_default.append(STYLE_CHECK_ENV_NAME)


def add_style_formatter(config, sections, make_envconfig, reader):
    # testenv:format_style
    section = '{}{}'.format(tox.config.testenvprefix, STYLE_FORMATTER_ENV_NAME)
    dependencies = [
        FLAKE8_DEP,
        BLACK_DEP,
        ISORT_DEP,
    ]
    sections[section] = {
        'platform': 'linux|darwin|win32',
        # These tools require Python 3.6+
        # more info: https://github.com/ambv/black/issues/439#issuecomment-411429907
        'basepython': 'python3',
        'skip_install': 'true',
        'deps': '\n'.join(dependencies),
        # Run formatter AFTER sorting imports
        'commands': '\n'.join(
            [
                'isort . --settings-path ../pyproject.toml ',
                'black . --config ../pyproject.toml',
                'python -c "print(\'\\n[NOTE] flake8 may still report style errors for things black cannot fix, '
                'these will need to be fixed manually.\')"',
                'flake8 --config=../.flake8 .',
            ]
        ),
    }

    # Always add the environment configurations
    config.envconfigs[STYLE_FORMATTER_ENV_NAME] = make_envconfig(
        config, STYLE_FORMATTER_ENV_NAME, section, reader._subs, config
    )

    # Intentionally add to envlist when seeing what is available
    if config.option.env is None or config.option.env == STYLE_FORMATTER_ENV_NAME:
        config.envlist_default.append(STYLE_FORMATTER_ENV_NAME)


def get_make_envconfig():
    make_envconfig = tox.config.ParseIni.make_envconfig

    # Make this a non-bound method for Python 2 compatibility
    make_envconfig = getattr(make_envconfig, '__func__', make_envconfig)

    return make_envconfig


def get_reader(config):
    # This is just boilerplate necessary to create a valid reader
    reader = tox.config.SectionReader('tox', config._cfg)
    reader.addsubstitutions(toxinidir=config.toxinidir, homedir=config.homedir)
    reader.addsubstitutions(toxworkdir=config.toxworkdir)
    config.distdir = reader.getpath('distdir', '{toxworkdir}/dist')
    reader.addsubstitutions(distdir=config.distdir)
    config.distshare = reader.getpath('distshare', '{homedir}/.tox/distshare')
    reader.addsubstitutions(distshare=config.distshare)

    return reader
