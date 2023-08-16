#!/bin/sh

# Install NFS client
apt update && apt install -y nfs-common=1:1.3.4-6

# Make the directory to mount
mkdir /test1

# Mount it
mount -v -t nfs -o port=2049 $NFS_SERVER:/ /test1

echo "NFS Client ready."
