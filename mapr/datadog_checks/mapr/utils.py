# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket


def get_stream_id_for_topic(topic_name, rng=1):
    """To distribute load, all the topics are not in the same stream. Each topic named is hashed
    to obtain an id which is in turn the name of the stream.
    This uses the djb2 algorithm, as described here
    https://mapr.com/docs/60/AdministratorGuide/spyglass-on-streams.html"""
    if rng == 1:
        return 0

    h = 5381
    for c in topic_name:
        h = ((h << 5) + h) + ord(c)
    return abs(h % rng)


def get_fqdn():
    """Returns the fully qualified domain name similarly to how `hostname -f` does it.
    The fqdn is used to find the correct mapr topic to read metrics from."""
    # Not portable but Mapr only runs on Linux
    # https://mapr.com/docs/61/InteropMatrix/r_os_matrix_6.x.html
    return socket.getfqdn()
