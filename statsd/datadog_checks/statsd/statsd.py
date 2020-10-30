# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import socket

from six import BytesIO

from datadog_checks.base import AgentCheck, ensure_bytes, ensure_unicode

SERVICE_CHECK_NAME = "statsd.can_connect"
SERVICE_CHECK_NAME_HEALTH = "statsd.is_up"

ENDER = re.compile(b"^(END|health: up|health: down)\n$", re.MULTILINE)
BAD_ENDER = re.compile(b"^ERROR\n$", re.MULTILINE)


class StatsCheck(AgentCheck):
    def check(self, instance):
        host = instance.get("host", "localhost")
        port = instance.get("port", 8126)
        timeout = float(instance.get('timeout', 10))
        tags = instance.get("tags", [])
        tags = ["host:{0}".format(host), "port:{0}".format(port)] + tags

        # Is it up?
        health = self._send_command(host, port, timeout, "health", tags).getvalue().strip()
        if health == b"health: up":
            self.service_check(SERVICE_CHECK_NAME_HEALTH, AgentCheck.OK, tags)
        else:
            self.service_check(SERVICE_CHECK_NAME_HEALTH, AgentCheck.CRITICAL, tags)

        # Get general stats
        stats = self._send_command(host, port, timeout, "stats", tags)
        stats.seek(0)
        for l in stats.readlines():
            parts = l.strip().split(b":")
            if len(parts) == 2:
                # Uptime isn't a gauge. Since we have only one exception, this
                # seems fine. If we make more a lookup table might be best.
                if parts[0] == b"bad_lines_seen":
                    self.monotonic_count("statsd.{0}".format(ensure_unicode(parts[0])), float(parts[1]), tags=tags)
                else:
                    self.gauge("statsd.{0}".format(ensure_unicode(parts[0])), float(parts[1]), tags=tags)

        counters = len(self._send_command(host, port, timeout, "counters", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.counters.count", counters, tags=tags)

        gauges = len(self._send_command(host, port, timeout, "gauges", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.gauges.count", gauges, tags=tags)

        timers = len(self._send_command(host, port, timeout, "timers", tags).getvalue().splitlines()) - 1
        self.gauge("statsd.timers.count", timers, tags=tags)

        # Send the final service check status
        self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags)

    def _send_command(self, host, port, timeout, command, tags):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))

            s.sendall(ensure_bytes("{0}\n".format(command)))

            buf = BytesIO()

            chunk = s.recv(1024)
            buf.write(ensure_bytes(chunk))
            while chunk:
                if ENDER.search(chunk):
                    break
                if BAD_ENDER.search(chunk):
                    raise Exception("Got an error issuing command: {0}".format(command))
                chunk = s.recv(1024)
                buf.write(chunk)
            return buf
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags)
            raise Exception("Failed connection {0}".format(str(e)))
        finally:
            s.close()
