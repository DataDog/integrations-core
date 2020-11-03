# SNMP Tools

## Using `tcpdump` for troubleshooting

In one shell:
```
tcpdump -vvv -nni lo0 -T snmp host localhost and port 1161
```

In another shell:
```
snmpwalk -O n -v2c -c <COMMUNITY_STRING> localhost:1161 1.3.6.1.2.1.1.2.0
```
