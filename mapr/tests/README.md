# How to run the test locally on MacOS

You need to install librdkafka to be able to compile `mapr-streams-python`

```
brew install librdkafka
pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib" --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python
```

# How to setup a test environment for MapR

Create multiple VMs (on gcp in an instance group for example) running CentOS 7.
Note: You'll need at least 32GB of memory per VM, yes 32GB.
Run this script on all the VMs:
```
sudo yum -y install java-1.8.0-openjdk-devel
curl https://package.mapr.com/releases/installer/mapr-setup.sh -o /tmp/mapr-setup.sh
```

You can then ssh into one node and follow the process described [here](https://mapr.com/docs/61/MapRInstaller.html) to
start the installer, it starts a web interface from which you can start to actually install MapR on every node
in the cluster.
