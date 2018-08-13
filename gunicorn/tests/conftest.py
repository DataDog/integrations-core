# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import subprocess
import pytest
import os
import tempfile
import requests
import shutil
import logging
import time

from common import FIXTURES, PROC_NAME

log = logging.getLogger('test_gunicorn')


@pytest.fixture(scope="session")
def setup_gunicorn(request):
    gunicorn_tmpdir = tempfile.mkdtemp()
    log.warning(gunicorn_tmpdir)
    app_dir = os.path.join(gunicorn_tmpdir, 'app')
    venv_dir = os.path.join(gunicorn_tmpdir, 'venv')
    os.mkdir(app_dir)
    os.mkdir(venv_dir)

    venv_file_path = os.path.join(venv_dir, 'virtualenv.py')

    with open(venv_file_path, 'w+') as f:
        r = requests.get('https://raw.github.com/pypa/virtualenv/1.11.6/virtualenv.py')
        f.write(r.text)

    subprocess.check_call(['python', venv_file_path, '--no-site-packages', '--no-pip', '--no-setuptools', venv_dir])

    venv_python_path = os.path.join(venv_dir, 'bin', 'python')

    ez_setup_file_path = os.path.join(venv_dir, 'ez_setup.py')
    get_pip_file_path = os.path.join(venv_dir, 'get-pip.py')

    with open(ez_setup_file_path, 'w+') as f:
        r = requests.get('https://bootstrap.pypa.io/ez_setup.py')
        f.write(r.text)

    subprocess.check_call([venv_python_path, ez_setup_file_path])

    with open(get_pip_file_path, 'w+') as f:
        r = requests.get('https://bootstrap.pypa.io/get-pip.py')
        f.write(r.text)

    subprocess.check_call([venv_python_path, get_pip_file_path])

    venv_pip_path = os.path.join(venv_dir, 'bin', 'pip')

    gunicorn_version = os.environ.get('GUNICORN_VERSION')

    if gunicorn_version:
        gunicorn_install = 'gunicorn=={}'.format(gunicorn_version)

    else:
        gunicorn_install = 'gunicorn'

    subprocess.check_call([venv_pip_path,
                           'install',
                           gunicorn_install,
                           'gevent',
                           'setproctitle'])

    conf_file = os.path.join(gunicorn_tmpdir, 'conf.py')
    shutil.copyfile(os.path.join(FIXTURES, 'conf.py'), conf_file)

    with open(conf_file, 'a') as f:
        f.write('chdir = "{}"'.format(app_dir))

    app_file = os.path.join(app_dir, 'app.py')

    shutil.copyfile(os.path.join(FIXTURES, 'app.py'), app_file)

    gunicorn_file_path = os.path.join(venv_dir, 'bin', 'gunicorn')
    args = [gunicorn_file_path,
            '--config={}'.format(conf_file),
            '--name={}'.format(PROC_NAME),
            'app:app']

    proc = subprocess.Popen(args)

    time.sleep(15)

    def fin():
        proc.terminate()
        shutil.rmtree(gunicorn_tmpdir)
    request.addfinalizer(fin)

    yield
