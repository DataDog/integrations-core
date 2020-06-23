How to install pymqi in MacOs
=============================
To install pymqi on Mac, first set up the [IBM MQ toolkit for Mac OS][1].

1. Download and extract the [toolkit][2].
2. Create a softlink from MQ_INSTALLATION_PATH to /opt/mqm
3. Set up the following environment variables:
    ```
    export MQ_INSTALLATION_PATH=~/IBM-MQ-Toolkit-Mac-x64-9.1.2.0
    export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$MQ_INSTALLATION_PATH/lib64
    export C_INCLUDE_PATH=/opt/mqm/inc
    export PATH="${PATH}:$MQ_INSTALLATION_PATH/bin"
    ```
4. `pip install pymqi==1.10.1`
5. Edit `requirements.in` and remove `and sys_platform != 'darwin'` so `pymqi` gets autoinstalled on tox environments.
Do not commit this change as it would break the mac agent build.


How to run tests from PyCharm
=============================
Set up the following env vars in your test run configuration:

* PYTHONPATH=$PYTHONPATH:$PATH_TO_YOUR_PYTHON_INSTALL/site-packages/pymqi  # Otherwise pycharm refuses to find pymqe.so
* DYLD_LIBRARY_PATH=~/IBM-MQ-Toolkit-Mac-x64-9.1.2.0/lib64
* IBM_MQ_VERSION= 8 or 9

Caveat about DYLD_LIBRARY_PATH on MacOS
=======================================

You might not be able to set `DYLD_LIBRARY_PATH` environment variable due to MacOS ["Runtime Protections"](https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html#//apple_ref/doc/uid/TP40016462-CH3-SW1) purging the variable.

This example won't work on MacOS:

```bash
$ DYLD_LIBRARY_PATH=/opt/mqm/lib64 python -c 'import pymqi'
...
ModuleNotFoundError: No module named 'pymqe'
```

The workaround is to use a virtualenv, then set `DYLD_LIBRARY_PATH`, then import `pymqi`.

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


[1]: https://developer.ibm.com/messaging/2019/02/05/ibm-mq-macos-toolkit-for-developers
[2]: https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/mactoolkit
