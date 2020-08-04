# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import io
import json
import os
import re
from ast import literal_eval
from json.decoder import JSONDecodeError

import requests
import semver

from ..utils import dir_exists, file_exists, read_file, read_file_lines, write_file
from .config import load_config
from .constants import NOT_CHECKS, REPO_CHOICES, REPO_OPTIONS_MAP, VERSION_BUMP, get_root, set_root
from .git import get_latest_tag

# match integration's version within the __about__.py module
VERSION = re.compile(r'__version__ *= *(?:[\'"])(.+?)(?:[\'"])')
DOGWEB_JSON_DASHBOARDS = (
    'btrfs',
    'cassandra',
    'couchbase',
    'elastic',
    'fluentd',
    'gearmand',
    'iis',
    'ibm_was',
    'immunio',
    'kong',
    'kyoto_tycoon',
    'marathon',
    'mcached',
    'mysql',
    'nginx',
    'pgbouncer',
    'php_fpm',
    'postfix',
    'postgres',
    'sqlserver',
    'rabbitmq',
    'riak',
    'riakcs',
    'solr',
    'sqlserver',
    'tokumx',
    'tomcat',
    'varnish',
)
DOGWEB_CODE_GENERATED_DASHBOARDS = (
    'activemq',
    'apache',
    'ceph',
    'cisco_aci',
    'consul',
    'couchdb',
    'cri',
    'crio',
    'etcd',
    'gunicorn',
    'haproxy',
    'hdfs_datanode',
    'hdfs_namenode',
    'hyperv',
    'ibm_mq',
    'kafka',
    'kube_controller_manager',
    'kube_scheduler',
    'kubernetes',
    'lighttpd',
    'mapreduce',
    'marathon',
    'mesos',
    'mongo',
    'nginx',
    'nginx_ingress_controller',
    'openstack',
    'powerdns_recursor',
    'rabbitmq',
    'redisdb',
    'sigsci',
    'spark',
    'twistlock',
    'wmi_check',
    'yarn',
    'zk',
)


def format_commit_id(commit_id):
    if commit_id:
        if commit_id.isdigit():
            return f'PR #{commit_id}'
        else:
            return f'commit hash `{commit_id}`'
    return commit_id


def get_current_agent_version():
    release_data = requests.get('https://raw.githubusercontent.com/DataDog/datadog-agent/master/release.json').json()
    versions = set()

    for version in release_data:
        parts = version.split('.')
        if len(parts) > 1:
            versions.add((int(parts[0]), int(parts[1])))

    most_recent = sorted(versions)[-1]

    return f"{most_recent[0]}.{most_recent[1]}"


def is_package(d):
    return file_exists(os.path.join(d, 'setup.py'))


def normalize_package_name(package_name):
    return re.sub(r'[-_. ]+', '_', package_name).lower()


def string_to_toml_type(s):
    if s.isdigit():
        s = int(s)
    elif s == 'true':
        s = True
    elif s == 'false':
        s = False
    elif s.startswith('['):
        s = literal_eval(s)

    return s


def get_check_file(check_name):
    return os.path.join(get_root(), check_name, 'datadog_checks', check_name, check_name + '.py')


def get_readme_file(check_name):
    return os.path.join(get_root(), check_name, 'README.md')


def check_root():
    """Check if root has already been set."""
    existing_root = get_root()
    if existing_root:
        return True

    root = os.getenv('DDEV_ROOT', '')
    if root and os.path.isdir(root):
        set_root(root)
        return True
    return False


def initialize_root(config, agent=False, core=False, extras=False, here=False):
    """Initialize root directory based on config and options"""
    if check_root():
        return

    repo_choice = 'core' if core else 'extras' if extras else 'agent' if agent else config.get('repo', 'core')
    config['repo_choice'] = repo_choice
    config['repo_name'] = REPO_CHOICES.get(repo_choice, repo_choice)

    message = None
    # TODO: remove this legacy fallback lookup in any future major version bump
    legacy_option = None if repo_choice == 'agent' else config.get(repo_choice)
    root = os.path.expanduser(legacy_option or config.get('repos', {}).get(repo_choice, ''))
    if here or not dir_exists(root):
        if not here:
            repo = 'datadog-agent' if repo_choice == 'agent' else f'integrations-{repo_choice}'
            message = f'`{repo}` directory `{root}` does not exist, defaulting to the current location.'

        root = os.getcwd()

    set_root(root)
    return message


def complete_set_root(args):
    """Set the root directory within the context of a cli completion operation."""
    if check_root():
        return

    config = load_config()

    kwargs = {REPO_OPTIONS_MAP[arg]: True for arg in args if arg in REPO_OPTIONS_MAP}
    initialize_root(config, **kwargs)


def complete_testable_checks(ctx, args, incomplete):
    complete_set_root(args)
    return sorted(k for k in get_testable_checks() if k.startswith(incomplete))


def complete_valid_checks(ctx, args, incomplete):
    complete_set_root(args)
    return [k for k in get_valid_checks() if k.startswith(incomplete)]


def get_version_file(check_name):
    if check_name == 'datadog_checks_base':
        return os.path.join(get_root(), check_name, 'datadog_checks', 'base', '__about__.py')
    elif check_name == 'datadog_checks_dev':
        return os.path.join(get_root(), check_name, 'datadog_checks', 'dev', '__about__.py')
    elif check_name == 'datadog_checks_downloader':
        return os.path.join(get_root(), check_name, 'datadog_checks', 'downloader', '__about__.py')
    else:
        return os.path.join(get_root(), check_name, 'datadog_checks', check_name, '__about__.py')


def is_agent_check(check_name):
    package_root = os.path.join(get_root(), check_name, 'datadog_checks', check_name, '__init__.py')
    if not file_exists(package_root):
        return False

    contents = read_file(package_root)

    # Anything more than the version must be a subclass of the base class
    return contents.count('import ') > 1


def code_coverage_enabled(check_name):
    if check_name in ('datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader'):
        return True

    return is_agent_check(check_name)


def get_manifest_file(check_name):
    return os.path.join(get_root(), check_name, 'manifest.json')


def get_tox_file(check_name):
    return os.path.join(get_root(), check_name, 'tox.ini')


def get_metadata_file(check_name):
    return os.path.join(get_root(), check_name, 'metadata.csv')


def get_assets_from_manifest(check_name, asset_type):
    paths = load_manifest(check_name).get('assets', {}).get(asset_type, {})
    assets = []
    nonexistent_assets = []
    for path in paths.values():
        asset = os.path.join(get_root(), check_name, *path.split('/'))

        if not file_exists(asset):
            nonexistent_assets.append(path)
            continue
        else:
            assets.append(asset)
    return sorted(assets), nonexistent_assets


def get_config_file(check_name):
    return os.path.join(get_data_directory(check_name), 'conf.yaml.example')


def get_config_spec(check_name):
    if check_name == 'agent':
        return os.path.join(get_root(), 'pkg', 'config', 'conf_spec.yaml')
    else:
        path = load_manifest(check_name).get('assets', {}).get('configuration', {}).get('spec', '')
        return os.path.join(get_root(), check_name, *path.split('/'))


def get_default_config_spec(check_name):
    return os.path.join(get_root(), check_name, 'assets', 'configuration', 'spec.yaml')


def get_assets_directory(check_name):
    return os.path.join(get_root(), check_name, 'assets')


def get_data_directory(check_name):
    if check_name == 'agent':
        return os.path.join(get_root(), 'pkg', 'config')
    else:
        return os.path.join(get_root(), check_name, 'datadog_checks', check_name, 'data')


def get_check_directory(check_name):
    return os.path.join(get_root(), check_name, 'datadog_checks', check_name)


def get_test_directory(check_name):
    return os.path.join(get_root(), check_name, 'tests')


def get_codeowners():
    codeowners_file = os.path.join(get_root(), '.github', 'CODEOWNERS')
    contents = read_file_lines(codeowners_file)
    return contents


def get_config_files(check_name):
    """TODO: Remove this function when all specs are finished"""
    if check_name == 'agent':
        return [os.path.join(get_root(), 'pkg', 'config', 'config_template.yaml')]

    files = []

    if check_name in NOT_CHECKS:
        return files

    root = get_root()

    auto_conf = os.path.join(root, check_name, 'datadog_checks', check_name, 'data', 'auto_conf.yaml')
    if file_exists(auto_conf):
        files.append(auto_conf)

    default_yaml = os.path.join(root, check_name, 'datadog_checks', check_name, 'data', 'conf.yaml.default')
    if file_exists(default_yaml):
        files.append(default_yaml)

    example_yaml = os.path.join(root, check_name, 'datadog_checks', check_name, 'data', 'conf.yaml.example')
    if file_exists(example_yaml):
        files.append(example_yaml)

    return sorted(files)


def get_check_files(check_name, file_suffix='.py', abs_file_path=True, include_dirs=None):
    """Return generator of filenames from within a given check.

    By default, only includes files within 'datadog_checks' and 'tests' directories, this
    can be expanded by adding to the `include_dirs` arg.
    """
    base_dirs = ['datadog_checks', 'tests']
    if include_dirs is not None:
        base_dirs += include_dirs

    bases = [os.path.join(get_root(), check_name, base) for base in base_dirs]

    for base in bases:
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith(file_suffix):
                    if abs_file_path:
                        yield os.path.join(root, f)
                    else:
                        yield f


def get_valid_checks():
    return {path for path in os.listdir(get_root()) if file_exists(get_version_file(path))}


def get_valid_integrations():
    return {path for path in os.listdir(get_root()) if file_exists(get_manifest_file(path))}


def get_testable_checks():
    return {path for path in os.listdir(get_root()) if file_exists(get_tox_file(path))}


def get_metric_sources():
    return {path for path in os.listdir(get_root()) if file_exists(get_metadata_file(path))}


def read_metric_data_file(check_name):
    return read_file(os.path.join(get_root(), check_name, 'metadata.csv'))


def read_metadata_rows(metadata_file):
    """
    Iterate over the rows of a `metadata.csv` file.
    """
    with io.open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')

        # Read header
        reader._fieldnames = reader.fieldnames

        for line_no, row in enumerate(reader, 2):
            yield line_no, row


def read_readme_file(check_name):
    for line_no, line in enumerate(read_file_lines(get_readme_file(check_name))):
        yield line_no, line


def read_version_file(check_name):
    return read_file(get_version_file(check_name))


def get_version_string(check_name, tag_prefix='v', pattern=None):
    """
    Get the version string for the given check.
    """
    # Check the version file of the integration if available
    # Otherwise, get the latest SemVer git tag for the project
    if check_name:
        version = VERSION.search(read_version_file(check_name))
        if version:
            return version.group(1)
    else:
        return get_latest_tag(pattern=pattern, tag_prefix=tag_prefix)


def load_manifest(check_name):
    """
    Load the manifest file into a dictionary
    """
    manifest_path = get_manifest_file(check_name)
    if file_exists(manifest_path):
        return json.loads(read_file(manifest_path).strip())
    return {}


def load_saved_views(path):
    """
    Load the saved view file into a dictionary
    """
    if file_exists(path):
        return json.loads(read_file(path).strip())
    return {}


def write_manifest(manifest, check_name):
    manifest_path = get_manifest_file(check_name)
    write_file(manifest_path, f'{json.dumps(manifest, indent=2)}\n')


def get_bump_function(changelog_types):
    minor_bump = False

    for changelog_type in changelog_types:
        bump_function = VERSION_BUMP.get(changelog_type)
        if bump_function is semver.bump_major:
            return bump_function
        elif bump_function is semver.bump_minor:
            minor_bump = True

    return semver.bump_minor if minor_bump else semver.bump_patch


def parse_agent_req_file(contents):
    """
    Returns a dictionary mapping {check-package-name --> pinned_version} from the
    given file contents. We can assume lines are in the form:

        datadog-active-directory==1.1.1; sys_platform == 'win32'

    """
    catalog = {}
    for line in contents.splitlines():
        toks = line.split('==', 1)
        if len(toks) != 2 or not toks[0] or not toks[1]:
            # if we get here, the requirements file is garbled but let's stay
            # resilient
            continue

        name, other = toks
        version = other.split(';')
        catalog[name] = version[0]

    return catalog


def parse_version_parts(version):
    if not isinstance(version, str):
        return []
    return [int(v) for v in version.split('.') if v.isdigit()]


def has_e2e(check):
    for path, _, files in os.walk(get_test_directory(check)):
        for fn in files:
            if fn.startswith('test_') and fn.endswith('.py'):
                with open(os.path.join(path, fn)) as test_file:
                    if 'pytest.mark.e2e' in test_file.read():
                        return True
    return False


def has_process_signature(check):
    manifest_file = get_manifest_file(check)
    try:
        with open(manifest_file) as f:
            manifest = json.loads(f.read())
    except JSONDecodeError as e:
        raise Exception("Cannot decode {}: {}".format(manifest_file, e))
    return len(manifest.get('process_signatures', [])) > 0


def is_tile_only(check):
    config_file = get_config_file(check)
    return not os.path.exists(config_file)


def has_dashboard(check):
    if check in DOGWEB_JSON_DASHBOARDS or check in DOGWEB_CODE_GENERATED_DASHBOARDS:
        return True
    dashboards_path = os.path.join(get_assets_directory(check), 'dashboards')
    return os.path.isdir(dashboards_path) and len(os.listdir(dashboards_path)) > 0


def find_legacy_signature(check):
    """
    Validate that the given check does not use the legacy agent signature (contains agentConfig)
    """
    for path, _, files in os.walk(get_check_directory(check)):
        for f in files:
            if f.endswith('.py'):
                with open(os.path.join(path, f)) as test_file:
                    for num, line in enumerate(test_file):
                        if "__init__" in line and "agentConfig" in line:
                            return str(f), num
    return None
