#!/bin/sh

set -e

# Install NFS client
apt-get update
apt-get install -y nfs-common

# Make the directory to mount
mkdir /test1

# Mount it
mount -v -t nfs -o port=2049 $NFS_SERVER:/ /test1

echo "NFS Client ready."
