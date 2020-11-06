# Tools

## Using `tcpdump` with SNMP

`tcpdump` shows the exact request and response content of SNMP `GET`, `GETNEXT` and other SNMP calls.

In a shell run `tcpdump`:

```
tcpdump -vv -nni lo0 -T snmp host localhost and port 161
```

- `-nn`:  turn off host and protocol name resolution (to avoid generating DNS packets)
- `-i INTERFACE`: listen on INTERFACE (default: lowest numbered interface)
- `-T snmp`: type/protocol, snmp in our case


In another separate shell run `snmpwalk` or `snmpget`:

```
snmpwalk -O n -v2c -c <COMMUNITY_STRING> localhost:1161 1.3.6
```

After you've run `snmpwalk`, you'll see results like this from `tcpdump`:

```
tcpdump -vv -nni lo0 -T snmp host localhost and port 161
tcpdump: listening on lo0, link-type NULL (BSD loopback), capture size 262144 bytes
17:25:43.639639 IP (tos 0x0, ttl 64, id 29570, offset 0, flags [none], proto UDP (17), length 76, bad cksum 0 (->91d)!)
    127.0.0.1.59540 > 127.0.0.1.1161:  { SNMPv2c C="cisco-nexus" { GetRequest(28) R=1921760388  .1.3.6.1.2.1.1.2.0 } }
17:25:43.645088 IP (tos 0x0, ttl 64, id 26543, offset 0, flags [none], proto UDP (17), length 88, bad cksum 0 (->14e4)!)
    127.0.0.1.1161 > 127.0.0.1.59540:  { SNMPv2c C="cisco-nexus" { GetResponse(40) R=1921760388  .1.3.6.1.2.1.1.2.0=.1.3.6.1.4.1.9.12.3.1.3.1.2 } }
```

### From the Docker Agent container

If you want to run `snmpget`, `snmpwalk`, and `tcpdump` from the Docker Agent container you can install them by running the following commands (in the container):

```
apt update
apt install -y snmp tcpdump
```
