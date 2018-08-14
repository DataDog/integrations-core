# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import os
import pytest
import shutil
import subprocess
import sys
import time

from datadog_checks.dev import temp_dir

from common import FIXTURES, PROC_NAME

log = logging.getLogger('test_gunicorn')


@pytest.fixture(scope="session")
def setup_gunicorn(request):
    with temp_dir() as tmpdir:
        app_dir, venv_dir = create_dirs(tmpdir)

        create_venv(venv_dir)

        venv_bin_path = get_venv_bin_path(venv_dir)

        install_pip_packages(venv_bin_path)

        conf_file = os.path.join(tmpdir, 'conf.py')
        copy_config_files(conf_file, app_dir)

        proc = start_gunicorn(venv_bin_path, conf_file)

        def fin():
            proc.terminate()
        request.addfinalizer(fin)

        time.sleep(15)

        yield


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
    gunicorn_version = os.environ.get('GUNICORN_VERSION')

    venv_pip_path = os.path.join(venv_bin_path, 'pip')

    if gunicorn_version:
        gunicorn_install = 'gunicorn=={}'.format(gunicorn_version)
    else:
        gunicorn_install = 'gunicorn'

    install_cmd = [venv_pip_path, 'install', gunicorn_install, 'gevent', 'setproctitle']
    subprocess.check_call(install_cmd)


def copy_config_files(conf_file, app_dir):
    shutil.copyfile(os.path.join(FIXTURES, 'conf.py'), conf_file)

    with open(conf_file, 'a') as f:
        f.write('chdir = "{}"'.format(app_dir))

    app_file = os.path.join(app_dir, 'app.py')

    shutil.copyfile(os.path.join(FIXTURES, 'app.py'), app_file)


def start_gunicorn(venv_bin_path, conf_file):
    gunicorn_file_path = os.path.join(venv_bin_path, 'gunicorn')
    args = [gunicorn_file_path,
            '--config={}'.format(conf_file),
            '--name={}'.format(PROC_NAME),
            'app:app']

    return subprocess.Popen(args)
