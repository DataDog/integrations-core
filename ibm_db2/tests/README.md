To run this on MacOS follow instructions on https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db#issues-with-mac-os-x
You would need to set DYLD_LIBRARY_PATH to point to lib folder as per the installation location of clidriver in your environment. Assuming the driver is installed at /usr/local/lib/python3.5/site-packages/clidriver, you can set the path as:

```
export DYLD_LIBRARY_PATH=<PYTHON_PATH>/lib/python3.8/site-packages/clidriver/lib:$DYLD_LIBRARY_PATH
```
