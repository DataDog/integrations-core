# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from six import PY3, iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output

from . import Network
from .const import BSD_TCP_METRICS

if PY3:
    long = int


class BSDNetwork(Network):
    def __init__(self, name, init_config, instances):
        super(BSDNetwork, self).__init__(name, init_config, instances)
        self._collect_cx_queues = self.instance.get('collect_connection_queues', False)

    def check(self, _):
        netstat_flags = ['-i', '-b']

        custom_tags = self.instance.get('tags', [])

        # FreeBSD's netstat truncates device names unless you pass '-W'
        if Platform.is_freebsd():
            netstat_flags.append('-W')

        try:
            output, _, _ = get_subprocess_output(["netstat"] + netstat_flags, self.log)
            lines = output.splitlines()
            # Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll
            # lo0   16384 <Link#1>                        318258     0  428252203   318258     0  428252203     0
            # lo0   16384 localhost   fe80:1::1           318258     -  428252203   318258     -  428252203     -
            # lo0   16384 127           localhost         318258     -  428252203   318258     -  428252203     -
            # lo0   16384 localhost   ::1                 318258     -  428252203   318258     -  428252203     -
            # gif0* 1280  <Link#2>                             0     0          0        0     0          0     0
            # stf0* 1280  <Link#3>                             0     0          0        0     0          0     0
            # en0   1500  <Link#4>    04:0c:ce:db:4e:fa 20801309     0 13835457425 15149389     0 11508790198     0
            # en0   1500  seneca.loca fe80:4::60c:ceff: 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  192.168.1     192.168.1.63    20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # p2p0  2304  <Link#5>    06:0c:ce:db:4e:fa        0     0          0        0     0          0     0
            # ham0  1404  <Link#6>    7a:79:05:4d:bf:f5    30100     0    6815204    18742     0    8494811     0
            # ham0  1404  5             5.77.191.245       30100     -    6815204    18742     -    8494811     -
            # ham0  1404  seneca.loca fe80:6::7879:5ff:    30100     -    6815204    18742     -    8494811     -
            # ham0  1404  2620:9b::54 2620:9b::54d:bff5    30100     -    6815204    18742     -    8494811     -

            headers = lines[0].split()

            # Given the irregular structure of the table above, better to parse from the end of each line
            # Verify headers first
            #          -7       -6       -5        -4       -3       -2        -1
            for h in ("Ipkts", "Ierrs", "Ibytes", "Opkts", "Oerrs", "Obytes", "Coll"):
                if h not in headers:
                    self.log.error("%s not found in %s; cannot parse", h, headers)
                    return False

            current = None
            for l in lines[1:]:
                # Another header row, abort now, this is IPv6 land
                if "Name" in l:
                    break

                x = l.split()
                if len(x) == 0:
                    break

                iface = x[0]
                if iface.endswith("*"):
                    iface = iface[:-1]
                if iface == current:
                    # skip multiple lines of same interface
                    continue
                else:
                    current = iface

                # Filter inactive interfaces
                if self.parse_long(x[-5]) or self.parse_long(x[-2]):
                    iface = current
                    metrics = {
                        'bytes_rcvd': self.parse_long(x[-5]),
                        'bytes_sent': self.parse_long(x[-2]),
                        'packets_in.count': self.parse_long(x[-7]),
                        'packets_in.error': self.parse_long(x[-6]),
                        'packets_out.count': self.parse_long(x[-4]),
                        'packets_out.error': self.parse_long(x[-3]),
                    }
                    self.submit_devicemetrics(iface, metrics, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting connection stats.")

        try:
            netstat, _, _ = get_subprocess_output(["netstat", "-s", "-p" "tcp"], self.log)
            # 3651535 packets sent
            #         972097 data packets (615753248 bytes)
            #         5009 data packets (2832232 bytes) retransmitted
            #         0 resends initiated by MTU discovery
            #         2086952 ack-only packets (471 delayed)
            #         0 URG only packets
            #         0 window probe packets
            #         310851 window update packets
            #         336829 control packets
            #         0 data packets sent after flow control
            #         3058232 checksummed in software
            #         3058232 segments (571218834 bytes) over IPv4
            #         0 segments (0 bytes) over IPv6
            # 4807551 packets received
            #         1143534 acks (for 616095538 bytes)
            #         165400 duplicate acks
            #         ...

            self._submit_regexed_values(netstat, BSD_TCP_METRICS, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting TCP stats.")

        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')

        net_proc_base_location = self.get_net_proc_base_location(proc_location)

        if self.is_collect_cx_state_runnable(net_proc_base_location):
            try:
                self.log.debug("Using `netstat` to collect connection state")
                output_tcp, _, _ = get_subprocess_output(["netstat", "-n", "-a", "-p", "tcp"], self.log)
                output_udp, _, _ = get_subprocess_output(["netstat", "-n", "-a", "-p", "udp"], self.log)
                lines = output_tcp.splitlines() + output_udp.splitlines()
                # Active Internet connections (w/o servers)
                # Proto Recv-Q Send-Q Local Address           Foreign Address         State
                # tcp        0      0 46.105.75.4:80          79.220.227.193:2032     SYN_RECV
                # tcp        0      0 46.105.75.4:143         90.56.111.177:56867     ESTABLISHED
                # tcp        0      0 46.105.75.4:50468       107.20.207.175:443      TIME_WAIT
                # tcp6       0      0 46.105.75.4:80          93.15.237.188:58038     FIN_WAIT2
                # tcp6       0      0 46.105.75.4:80          79.220.227.193:2029     ESTABLISHED
                # udp        0      0 0.0.0.0:123             0.0.0.0:*
                # udp6       0      0 :::41458                :::*

                metrics = self.parse_cx_state(lines[2:], self.tcp_states['netstat'], 5)
                for metric, value in iteritems(metrics):
                    self.gauge(metric, value, tags=custom_tags)
            except SubprocessOutputEmptyError:
                self.log.exception("Error collecting connection states.")
