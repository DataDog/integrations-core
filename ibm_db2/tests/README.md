To run this on MacOS follow instructions on https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db#issues-with-mac-os-x
You would need to set DYLD_LIBRARY_PATH to point to lib folder as per the installation location of clidriver in your environment.
Assuming the driver is installed at /opt/ibm_db/clidriver, you can set the path as:

```
IBM_DB_HOME=/opt/ibm_db/clidriver
export DYLD_LIBRARY_PATH=/opt/ibm_db/clidriver/lib:$DYLD_LIBRARY_PATH
```
