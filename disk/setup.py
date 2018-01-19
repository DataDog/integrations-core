# Always prefer setuptools over distutils
from setuptools import setup
from codecs import open  # To use a consistent encoding
from os import path

HERE = path.abspath(path.dirname(__file__))

def parse_req_line(line):
    line = line.strip()
    if not line or line.startswith('--hash') or line[0] == '#':
        return None
    req = line.rpartition('#')
    if len(req[1]) == 0:
        line = req[2].strip()
    else:
        line = req[1].strip()

    if '--hash=' in line:
        line = line[:line.find('--hash=')].strip()
    if ';' in line:
        line = line[:line.find(';')].strip()
    if '\\' in line:
        line = line[:line.find('\\')].strip()

    return line


ABOUT = {}
with open(path.join(HERE, "datadog_checks", "disk", "__about__.py")) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Parse requirements
def get_requirements(fpath):
    requirements_txt = set()
    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        for line in f.readlines():
            req = parse_req_line(line)
            if req:
                requirements_txt.add(req)
    return list(requirements_txt)


setup(
    name='datadog-disk',
    version=ABOUT["__version__"],
    description='The Disk check',
    long_description=long_description,
    keywords='datadog agent disk check',

    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',

    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',

    # License
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    # The package we're going to ship
    packages=['datadog_checks.disk'],

    # Run-time dependencies
    install_requires=get_requirements('requirements.txt')+[
        'datadog-checks-base',
    ],

    # Development dependencies, run with:
    # $ pip install -e .[dev]
    extras_require={
        'dev': [
            'check-manifest',
        ],
    },

    # Testing setup and dependencies
    setup_requires=['pytest-runner',],
    tests_require=get_requirements(path.join('tests', 'requirements.txt')),

    # Extra files to ship with the wheel package
    package_data={'datadog_checks.disk': ['conf.yaml.default']},
    include_package_data=True,
)
