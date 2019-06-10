How to install pymqi in MacOs
=============================
To be able to install pymqi in Mac you need to first set up the [IBM MQ toolkit for Mac OS][1].

1. Download an extract the [toolkit][2].
2. Set up the following environment variables:
    ```
    export MQ_INSTALLATION_PATH=~/IBM-MQ-Toolkit-Mac-x64-9.1.2.0
    export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$MQ_INSTALLATION_PATH/lib64
    export PATH="${PATH}:~/IBM-MQ-Toolkit-Mac-x64-9.1.2.0/bin"
    ```
3. Create a softlink from MQ_INSTALLATION_PATH to /opt/mqm
4. `pip install pymqi`


How to run tests from PyCharm
=============================
Set up following env vars in your test run configuration:

* PYTHONPATH=$PYTHONPATH:$PATH_TO_YOUR_PYTHON_INSTALL/site-packages/pymqi  # Otherwise pycharm refuses to find pymqe.so
* DYLD_LIBRARY_PATH=~/IBM-MQ-Toolkit-Mac-x64-9.1.2.0/lib64
* IBM_MQ_VERSION= 8 or 9


[1]: https://developer.ibm.com/messaging/2019/02/05/ibm-mq-macos-toolkit-for-developers/
[2]: https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/mactoolkit/