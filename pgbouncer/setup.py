from setuptools import setup
from codecs import open
from os import path

HERE = path.abspath(path.dirname(__file__))

# Get version info
ABOUT = {}
with open(path.join(HERE, "datadog_checks", "pgbouncer", "__about__.py")) as f:
    exec(f.read(), ABOUT)


# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# Parse requirements
def get_requirements(fpath):
    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        return f.readlines()


setup(
    name='datadog-pgbouncer',
    version=ABOUT["__version__"],
    description='The PGbouncer check',
    long_description=long_description,
    keywords='datadog agent pgbouncer check',
    url='https://github.com/DataDog/integrations-core',
    author='Datadog',
    author_email='packages@datadoghq.com',
    license='BSD',
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
    packages=['datadog_checks.pgbouncer'],
    install_requires=get_requirements("requirements.in") + ["datadog_checks_base"],
    tests_require=get_requirements("requirements-dev.txt"),
    # Extra files to ship with the wheel package
    package_data={b'datadog_checks.pgbouncer': ['conf.yaml.example']},
    include_package_data=True,
)
