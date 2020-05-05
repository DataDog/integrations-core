These fixtures were generated from a Windows server running many services like IIS, Active Directory, etc.

`counter_indexes_<lang>-<locale>` is essentially the contents of the registry entry that lists all the strings, enumerated in the file.
`allcounters_<lang>-<locale>` is the output of `typeperf -qx`, with a bit of parsing to make it easier to parse back in for the tests.

You take `typeperf -qx` and redirect to a file, that gets you a huge file in the format:

```
\Storage QoS Filter - Volume(D:)\Avg. Normalized I/O Cost
\Storage QoS Filter - Volume(D:)\Avg. I/O Cost
\Network Virtualization(Provider Routing Domain)\Unicast Replicated Packets out
\Network Virtualization(Provider Routing Domain)\Inbound Packets dropped
```

Then you use a giant regex to format it so that `!` is the separator, to make it easier to parse.

This is the lasting remnant of the old script:

```python
import re
import string
from collections import defaultdict

teststrings = [
 '\ASP.NET\Requests Disconnected',
 '\ASP.NET Applications(_LM_W3SVC_2_ROOT_EWS)\Anonymous Requests/Sec',
 '\MSMQ Queue(win-k2olfvr52p5\private$\order_queue$)\Bytes in Queue',
 '\SMB Client Shares(\localhost\IPC$)\Current Data Queue Length',
]


def parse_counter(counter):
    classname = None
    instance = None
    cname = None
    # remove the leading slash, don't need it
    c = string.lstrip(counter, '\\')

    firstslash = c.find('\\')

    # now, check to see if there's a (.  Open paren indicates an instance
    # name (and there could be a "\" in the instance name)
    cname_start = 0
    open_paren = c[:firstslash].find('(')
    if open_paren != -1:
        close_paren = c[open_paren:].find(')')
        instance = c[open_paren+1:open_paren + close_paren]
        cname_start = open_paren + close_paren + 2
        classname = c[:open_paren]
    else:
        cname_start = firstslash+1
        classname = c[:firstslash]

    cname = c[cname_start:]
    return classname, instance, cname


#cl, inst, co = parse_counter(str1)
#print("%s - %s - %s\n" % (cl, inst, co))

#cl, inst, co = parse_counter(str2)
#print("%s - %s - %s\n" % (cl, inst, co))

allcounters = defaultdict(list)
regex = r'(\\[^(]+)(?:\(([^)]+)\))?(\\[^(]+)'
compiled_regex = re.compile(regex)
for s in teststrings:
    res = compiled_regex.search(s).groups()
    a,b,c = [ x if not x else x.lstrip('\\') for x in res ]
    #if b:
    #    b = b.lstrip("(").rstrip(")")
    allcounters[a][0].append(c) if c not in allcounters[a][0]

print allcounters
```
