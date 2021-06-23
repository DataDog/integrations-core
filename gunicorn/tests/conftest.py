# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import os
import shutil
import subprocess
import sys
import time

import pytest

from datadog_checks.dev import docker_run, temp_dir

from .common import COMPOSE, GUNICORN_VERSION, INSTANCE, PROC_NAME

log = logging.getLogger('test_gunicorn')


@pytest.fixture(scope='session')
def dd_environment():
    os.environ['PROC_NAME'] = PROC_NAME
    os.environ['GUNICORN_VERSION'] = GUNICORN_VERSION
    compose_file = os.path.join(COMPOSE, 'docker-compose.yaml')
    with docker_run(compose_file, log_patterns=['Booting worker with pid'], build=True):
        yield INSTANCE


@pytest.fixture(scope="session")
def setup_gunicorn(request):
    with temp_dir() as tmpdir:
        app_dir, venv_dir = create_dirs(tmpdir)

        create_venv(venv_dir)

        venv_bin_path = get_venv_bin_path(venv_dir)

        install_pip_packages(venv_bin_path)

        conf_file = os.path.join(tmpdir, 'conf.py')
        copy_config_files(conf_file, app_dir)

        gunicorn_bin_path = os.path.join(venv_bin_path, 'gunicorn')

        proc = start_gunicorn(gunicorn_bin_path, conf_file)

        def fin():
            proc.kill()
            time.sleep(5)

        request.addfinalizer(fin)

        time.sleep(5)

        yield {'gunicorn_bin_path': gunicorn_bin_path}


def create_dirs(tmpdir):
    app_dir = os.path.join(tmpdir, 'app')
    venv_dir = os.path.join(tmpdir, 'venv')
    os.mkdir(app_dir)
    os.mkdir(venv_dir)

    return (app_dir, venv_dir)


def create_venv(venv_dir):
    cmd = [sys.executable, '-m', 'virtualenv', venv_dir]
    subprocess.check_call(cmd)


def get_venv_bin_path(venv_dir):
    return os.path.join(venv_dir, 'bin')


def install_pip_packages(venv_bin_path):
    venv_pip_path = os.path.join(venv_bin_path, 'pip')

    if GUNICORN_VERSION:
        gunicorn_install = 'gunicorn=={}'.format(GUNICORN_VERSION)
    else:
        gunicorn_install = 'gunicorn'

    install_cmd = [venv_pip_path, 'install', gunicorn_install, 'gevent', 'setproctitle']
    subprocess.check_call(install_cmd)


def copy_config_files(conf_file, app_dir):
    shutil.copyfile(os.path.join(COMPOSE, 'conf.py'), conf_file)

    with open(conf_file, 'a') as f:
        f.write('chdir = "{}"'.format(app_dir))

    app_file = os.path.join(app_dir, 'app.py')

    shutil.copyfile(os.path.join(COMPOSE, 'app.py'), app_file)


def start_gunicorn(gunicorn_bin_path, conf_file):
    args = [gunicorn_bin_path, '--config={}'.format(conf_file), '--name={}'.format(PROC_NAME), 'app:app']

    return subprocess.Popen(args)
