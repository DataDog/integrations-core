import argparse
import json
import os
import subprocess
import sys
import tomllib
from fnmatch import fnmatch
from functools import cache
from pathlib import Path

# https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idoutputs
OUTPUT_LIMIT = 1024 * 1024

# https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-strategy
JOB_LIMIT = 256

TESTABLE_FILE_PATTERNS = (
    'assets/configuration/**/*',
    'tests/**/*',
    '*.py',
    'hatch.toml',
    'pyproject.toml',
)
NON_TESTABLE_FILES = {'auto_conf.yaml', 'agent_requirements.in'}
DISPLAY_ORDER_OVERRIDE = {
    _d: _i for _i, _d in enumerate(
        (
            'ddev',
            'datadog_checks_base',
            'datadog_checks_dev',
            'datadog_checks_downloader',
        )
    )
}
PLATFORM_NAMES = {'linux': 'Linux', 'windows': 'Windows', 'macos': 'macOS'}
PLATFORM_TO_OS = {
    # https://github.com/actions/runner-images/blob/main/images/linux/Ubuntu2204-Readme.md
    'linux': 'ubuntu-22.04',
    # https://github.com/actions/runner-images/blob/main/images/win/Windows2022-Readme.md
    'windows': 'windows-2022',
    # https://github.com/actions/runner-images/blob/main/images/macos/macos-12-Readme.md
    'macos': 'macos-12',
}


@cache
def read_manifest(root: Path, directory_name: str) -> dict:
    manifest_path = root / directory_name / 'manifest.json'
    if not manifest_path.is_file():
        return {}

    return json.loads(manifest_path.read_text(encoding='utf-8'))


def is_git_warning_line(line: str) -> bool:
    return line.startswith('warning: ') or 'original line endings' in line


def git(*args) -> str:
    try:
        process = subprocess.run(
            ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True
        )
    except subprocess.CalledProcessError as e:
        raise OSError(f'{str(e)[:-1]}:\n{e.output}') from None

    return process.stdout


def get_changed_files(*, ref: str, local: bool) -> list[str]:
    changed_files = set()

    # Committed e.g.:
    # A   relative/path/to/file.added
    # M   relative/path/to/file.modified
    for line in git('diff', '--name-status', f'{ref}...').splitlines():
        if not is_git_warning_line(line):
            changed_files.add(line.split(maxsplit=1)[1])

    if local:
        # Tracked
        for line in git('diff', '--name-only', 'HEAD').splitlines():
            if not is_git_warning_line(line):
                changed_files.add(line)

        # Untracked
        changed_files.update(git('ls-files', '--others', '--exclude-standard').splitlines())

    return sorted(changed_files, key=lambda relative_path: (relative_path, -relative_path.count('/')))


def main():
    root = Path.cwd()
    os.chdir(root)

    parser = argparse.ArgumentParser(prog='devenv', allow_abbrev=False)
    parser.add_argument('--ref', default='origin/master')
    parser.add_argument('-p', '--pretty', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    matrices = []
    for i in range(2):
        matrices.append({'os': 'ubuntu-22.04', 'target': 'disk', 'name': f'Disk {i}'})
    output = json.dumps(matrices, separators=(',', ':'))
    print(output)
    print(f'Output size: {len(output)} / {OUTPUT_LIMIT}', file=sys.stderr)
    return

    changed_files = get_changed_files(ref=args.ref, local=args.pretty)
    if args.verbose:
        print('\n'.join(changed_files), file=sys.stderr)

    changed_directories = {}
    for changed_file in changed_files:
        directory_name, _, relative_path = changed_file.partition('/')
        if relative_path:
            changed_directories.setdefault(directory_name, []).append(relative_path)

    testable_directories = []
    for directory_name, files in changed_directories.items():
        directory = root / directory_name
        if not ((directory / 'hatch.toml').is_file() and (directory / 'tests').is_dir()):
            continue

        for relative_path in files:
            possible_file = directory / relative_path
            if possible_file.name in NON_TESTABLE_FILES:
                continue
            elif any(fnmatch(str(possible_file), str(directory / pattern)) for pattern in TESTABLE_FILE_PATTERNS):
                testable_directories.append(directory_name)
                break

    testable_directories.sort(key=lambda d: (DISPLAY_ORDER_OVERRIDE.get(d, len(DISPLAY_ORDER_OVERRIDE)), d))

    overrides = {}
    if (config_file := root / '.ddev' / 'config.toml').is_file():
        overrides.update(tomllib.loads(config_file.read_text(encoding='utf-8')).get('overrides', {}))

    display_overrides = overrides.get('display-name', {})
    ci_overrides = overrides.get('ci', {})

    matrices = []
    for directory_name in testable_directories:
        manifest = read_manifest(root, directory_name)

        matrix_overrides = ci_overrides.get(directory_name, {})
        platforms = matrix_overrides.get('platforms', [])
        if not platforms:
            if manifest:
                platforms = []
                for classifier_tag in manifest['tile']['classifier_tags']:
                    key, _, value = classifier_tag.partition('::')
                    if key == 'Supported OS':
                        platforms.append(value.lower())

                # Run only on Linux if not exclusive to Windows
                if platforms != ['windows']:
                    platforms = ['linux']
            else:
                platforms = ['linux']

        for platform in platforms:
            if platform not in PLATFORM_NAMES:
                raise ValueError(f'Unsupported platform for `{directory_name}`: {platform}')

            config = {'os': PLATFORM_TO_OS[platform], 'target': directory_name}

            if directory_name in display_overrides:
                config['name'] = display_overrides[directory_name]
            elif manifest:
                config['name'] = manifest['assets']['integration']['source_type_name']
            else:
                config['name'] = directory_name

            if len(platforms) > 1:
                config['name'] += f' on {PLATFORM_NAMES[platform]}'

            if matrix_overrides.get('test-py2', False):
                config['py2'] = True

            matrices.append(config)

    total_matrices = len(matrices)
    matrices[:] = matrices[:JOB_LIMIT]

    output = json.dumps(matrices, indent=2) if args.pretty else json.dumps(matrices, separators=(',', ':'))
    print(output)

    print(f'Output size: {len(output)} / {OUTPUT_LIMIT}', file=sys.stderr)
    print(f'Number of jobs: {total_matrices}', file=sys.stderr)
    if total_matrices > JOB_LIMIT:
        print(f'Jobs ignored to satisfy limit: {total_matrices - JOB_LIMIT}', file=sys.stderr)


if __name__ == '__main__':
    main()
