# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import tox
import tox.config

STYLE_CHECK_ENV_NAME = 'style'
STYLE_FORMATTER_ENV_NAME = 'format_style'
STYLE_FLAG = 'dd_check_style'


@tox.hookimpl
def tox_configure(config):
    """
    For more info, see: https://tox.readthedocs.io/en/latest/plugins.html
    For an example, see: https://github.com/tox-dev/tox-travis
    """
    sections = config._cfg.sections

    # Cache these
    make_envconfig = None
    reader = None

    # Default to false so:
    # 1. we don't affect other projects using tox
    # 2. check migrations can happen gradually
    if str(sections.get('testenv', {}).get(STYLE_FLAG, 'false')).lower() == 'true':
        # Disable flake8 since we already include that
        config.envlist[:] = [env for env in config.envlist if not env.endswith('flake8')]

        make_envconfig = get_make_envconfig(make_envconfig)
        reader = get_reader(reader, config)

        add_style_checker(config, sections, make_envconfig, reader)
        add_style_formatter(config, sections, make_envconfig, reader)


def add_style_checker(config, sections, make_envconfig, reader):
    # testenv:style
    section = '{}{}'.format(tox.config.testenvprefix, STYLE_CHECK_ENV_NAME)
    sections[section] = {
        'platform': 'linux|darwin|win32',
        # These tools require Python 3.6+
        # more info: https://github.com/ambv/black/issues/439#issuecomment-411429907
        'basepython': 'python3',
        'skip_install': 'true',
        'deps': 'flake8\nflake8-bugbear\nblack\nisort[pyproject]>=4.3.15',
        'commands': 'flake8 --config=../.flake8 .\nblack --check --diff .\nisort --check-only --diff --recursive .',
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
    sections[section] = {
        'platform': 'linux|darwin|win32',
        # These tools require Python 3.6+
        # more info: https://github.com/ambv/black/issues/439#issuecomment-411429907
        'basepython': 'python3',
        'skip_install': 'true',
        'deps': 'black\nisort[pyproject]>=4.3.15',
        # Run formatter AFTER sorting imports
        'commands': 'isort --recursive .\nblack .',
    }

    # Always add the environment configurations
    config.envconfigs[STYLE_FORMATTER_ENV_NAME] = make_envconfig(
        config, STYLE_FORMATTER_ENV_NAME, section, reader._subs, config
    )

    # Intentionally add to envlist when seeing what is available
    if config.option.env is None or config.option.env == STYLE_FORMATTER_ENV_NAME:
        config.envlist_default.append(STYLE_FORMATTER_ENV_NAME)


def get_make_envconfig(make_envconfig):
    if make_envconfig is None:
        make_envconfig = tox.config.ParseIni.make_envconfig

        # Make this a non-bound method for Python 2 compatibility
        make_envconfig = getattr(make_envconfig, '__func__', make_envconfig)

    return make_envconfig


def get_reader(reader, config):
    if reader is None:
        # This is just boilerplate necessary to create a valid reader
        reader = tox.config.SectionReader('tox', config._cfg)
        reader.addsubstitutions(toxinidir=config.toxinidir, homedir=config.homedir)
        reader.addsubstitutions(toxworkdir=config.toxworkdir)
        config.distdir = reader.getpath('distdir', '{toxworkdir}/dist')
        reader.addsubstitutions(distdir=config.distdir)
        config.distshare = reader.getpath('distshare', '{homedir}/.tox/distshare')
        reader.addsubstitutions(distshare=config.distshare)

    return reader
