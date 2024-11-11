import sys
from subprocess import run

if sys.platform == 'darwin':
    run(['brew', 'install', 'rrdtool'])
elif sys.platform == 'linux':
    import platform

    print(platform.freedesktop_os_release())
else:
    raise OSError(f"Cannot install rrdtool on this platform yet: {sys.platform}")
