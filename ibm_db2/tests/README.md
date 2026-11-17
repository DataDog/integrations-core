To run this on MacOS follow instructions on https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db#issues-with-mac-os-x
You would need to set DYLD_LIBRARY_PATH to point to lib folder as per the installation location of clidriver in your environment. Assuming the driver is installed at /usr/local/lib/python3.5/site-packages/clidriver, you can set the path as:

```
export DYLD_LIBRARY_PATH=<PYTHON_PATH>/lib/python3.8/site-packages/clidriver/lib:$DYLD_LIBRARY_PATH
```

## Read Agent DBM output without a backend

On a native x86_64 workspace, install the `zstd` CLI and start the recorder:

```shell
python ibm_db2/scripts/capture_agent.py /tmp/db2-agent.jsonl
```

Run a disposable Agent on the workspace with Docker's `--network host`, mounting
`ibm_db2/scripts/capture_agent.yaml` as its `datadog.yaml` and the check configuration
as usual. This configuration uses a dummy API key and directs DBM traffic to the
loopback recorder. Read the decompressed, submitted events with:

```shell
python ibm_db2/scripts/capture_agent.py /tmp/db2-agent.jsonl --read --stream dbm-activity
```

The same reader supports metrics, FQT, metadata, and health streams. Captures omit
request headers and URL queries, but preserve submitted event bodies so literal
leaks can be detected with controlled workloads. A recorded request proves Agent
submission; the recorder does not validate backend ingestion or persistence.
