# IBM MQ integration Dev Setup for MacOS

## Download the IBM MQ Client

You can find it here: 
https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/mactoolkit/9.2.5.0-IBM-MQ-DevToolkit-MacX64.pkg

Follow the instructions in the installation guide to update your PATH.

## Verify it works

```bash
virtualenv /tmp/venv
source /tmp/venv/bin/activate
pip install pymqi

LD_LIBRARY_PATH=/opt/mqm/lib64 python -c 'import pymqi'  # If this line does not fail. We are good.

rm -rf /tmp/venv
```

More info why we need virtualenv in section "Caveat about DYLD_LIBRARY_PATH on MacOS".


How to run tests from your IDE
=============================
Set up the following env vars in your test run configuration:

* PYTHONPATH=$PYTHONPATH:$PATH_TO_YOUR_PYTHON_INSTALL/site-packages/pymqi  # Otherwise pycharm refuses to find pymqe.so
* DYLD_LIBRARY_PATH=/opt/mqm/lib64
* IBM_MQ_VERSION=8 or 9

Caveat about DYLD_LIBRARY_PATH on MacOS
=======================================

You might not be able to set `DYLD_LIBRARY_PATH` environment variable due to MacOS ["Runtime Protections"](https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html#//apple_ref/doc/uid/TP40016462-CH3-SW1) purging the variable.

This example won't work on MacOS:

```bash
$ DYLD_LIBRARY_PATH=/opt/mqm/lib64 python -c 'import pymqi'
...
ModuleNotFoundError: No module named 'pymqe'
```

The workaround is to use a virtualenv:
1. Create a virtualenv.
2. Set `DYLD_LIBRARY_PATH`.
3. Install `pymqi` using `pip install pymqi`.
4. Re-install ddev in the virtual environment using `python -m pip install -e "path/to/datadog_checks_dev[cli]"`.

You can start the ddev environment in your virtual environment.

This does not affect tox tests since virtualenv is used.

Development Tips
================

### How to connect to IBM MQ console

```
$ ddev env start ibm_mq py27-8
$ docker exec -it ibm_mq runmqsc datadog
```

# IBM MQ Console example commands

```
# Display all channels
$ DIS CHANNEL(*)

# Display one channels properties
DIS CHANNEL(DEV.APP.SVRCONN)
``` 


### How to create a channel with permissions

```
DEFINE CHANNEL('DEV.APP.SVRCONN') CHLTYPE(SVRCONN) MCAUSER('app') REPLACE
SET CHLAUTH('DEV.ADMIN.SVRCONN') TYPE(BLOCKUSER) USERLIST('nobody') DESCR('Allows admins on ADMIN channel') ACTION(REPLACE)
SET CHLAUTH('DEV.ADMIN.SVRCONN') TYPE(USERMAP) CLNTUSER('admin') USERSRC(CHANNEL) DESCR('Allows admin user to connect via ADMIN channel') ACTION(REPLACE)
```
[source](https://github.com/ibm-messaging/mq-docker/blob/a1df5ac6c5f39c375bdbdc0ec812c00aa54accc3/mq-dev-config#L35-L43)
