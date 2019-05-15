To run integration tests you need to install python-rrdtool

Install python-rrdtool on MAC
=============================
```
brew install rrdtool
pip install rrdtool
```

To run integration tests
========================
* `ddev env start cacti py27-integration`
* `docker ps`
*  Install required dependencies in agent image:
    ```
    $ docker exec -it <agent_image> /bin/bash
    # apt-get update && apt-get install rrdtool librrd-dev libpython-dev build-essential -y && pip install rrdtool
    # exit
    ```
* `ddev env check cacti py27-integration`
* `ddev env stop cacti py27-integration`
