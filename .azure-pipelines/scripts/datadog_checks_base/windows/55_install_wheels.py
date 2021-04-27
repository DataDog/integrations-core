import glob
import os
import subprocess

PACKAGES = [
    # https://github.com/joerick/cibuildwheel/pull/649#issuecomment-825721286
    'mmh3==2.5.1',
]


def main():
    # Rely on glob patterns to locate Python in case there are new patch releases
    executable = glob.glob(r'C:\hostedtoolcache\windows\Python\2.7.*\x64\python.exe')[0]

    subprocess.check_call(
        [executable, '-m', 'pip', 'install', '--cache-dir', os.environ['PIP_CACHE_DIR'], '--extra-index-url', 'https://datadoghq.dev/ci-wheels/bin', *PACKAGES]
    )


if __name__ == '__main__':
    main()
