import os
import subprocess
import sys
from contextlib import contextmanager
from io import open

HERE = os.path.dirname(os.path.abspath(__file__))


@contextmanager
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


def ensure_deps_declared(reqs_txt, reqs_in):
    if os.path.isfile(reqs_txt) and not os.path.isfile(reqs_in):
        declacred_lines = []

        with open(reqs_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.split('--hash')[0].strip('\r\n \\')
            if line and not line.startswith('#'):
                declacred_lines.append(line + '\n')

        with open(reqs_in, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(declacred_lines)


def compile_check_deps(check_dir):
    with chdir(check_dir):
        return subprocess.check_output([
            'pip-compile',
            '--generate-hashes',
            '--output-file', 'requirements.txt',
            'requirements.in'
        ], stderr=subprocess.STDOUT)


def main():
    args = sys.argv[1:]
    if '--help' in args:
        print('You must specify deps like `upgrade-dep.py requests 2.18.4`.')
        sys.exit()

    verbose = '-v' in args
    if verbose:
        args.remove('-v')

    if len(args) < 2:
        print('You must specify deps like `upgrade-dep.py requests 2.18.4`.')
        sys.exit(1)

    package, version = args[:2]

    for check_name in sorted(os.listdir(HERE)):
        check_dir = os.path.join(HERE, check_name)
        reqs_in = os.path.join(check_dir, 'requirements.in')
        reqs_txt = os.path.join(check_dir, 'requirements.txt')

        ensure_deps_declared(reqs_txt, reqs_in)

        if os.path.isfile(reqs_in):
            with open(reqs_in, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                try:
                    pkg = line.split('=')[0].strip()
                    if pkg == package:
                        break
                except IndexError:
                    continue
            else:
                continue

            if verbose:
                print('Check `{}`:'.format(check_name))
                print('    Old: `{}`'.format(lines[i].strip()))

            lines[i] = '{}=={}\n'.format(package, version)

            with open(reqs_in, 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(lines)

            if verbose:
                print('    New: `{}`'.format(lines[i].strip()))
                print('    Locking dependencies...')

            compile_check_deps(check_dir)


if __name__ == '__main__':
    main()
