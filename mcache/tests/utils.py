# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess


def count_connections(port):
    """
    Count how many connections to memcached there are in the current process
    """
    pid = os.getpid()
    p1 = subprocess.Popen(['lsof', '-a', '-p%s' % pid, '-i4'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", ":%s" % port], stdin=p1.stdout, stdout=subprocess.PIPE)
    p3 = subprocess.Popen(["wc", "-l"], stdin=p2.stdout, stdout=subprocess.PIPE)
    output = p3.communicate()[0]
    return int(output.strip())


def get_host_socket_path():
    return os.getenv('HOST_SOCKET_PATH')
