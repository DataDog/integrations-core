To run this on MacOS follow instructions on https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db#issues-with-mac-os-x
You would need to set DYLD_LIBRARY_PATH to point to lib folder as per the installation location of clidriver in your environment. Assuming the driver is installed at /usr/local/lib/python3.5/site-packages/clidriver, you can set the path as:

```
export DYLD_LIBRARY_PATH=<PYTHON_PATH>/lib/python3.8/site-packages/clidriver/lib:$DYLD_LIBRARY_PATH
```

## Query metrics seed

Run the query metrics integration test on an amd64 Linux host with Docker:

```shell
ddev --no-interactive test ibm_db2:py3.13-12.1.5.0 -- -k test_query_metrics
```

The existing test fixture starts Db2 12.1. The test enables `dbm`, establishes a
counter baseline, closes the collector's connection, and verifies that collection
resumes and submits the next three executions in a `dbm-metrics` payload. It uses
synchronous collection with a short interval; database initialization accounts for
most of the runtime.

This verifies a real database through the Agent test aggregator. It does not verify
the Agent's native SQL obfuscator, backend ingestion, or UI behavior. Collection is
limited to the configured database and current member. New cache entries establish
a baseline before subsequent counter increases are reported.
