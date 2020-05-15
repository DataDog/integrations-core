#!/bin/sh

# Install NFS client
apt update && apt install -y nfs-common

# Make the directory to mount
mkdir /test1

# Mount it
mount -v -t nfs -o port=2049 $NFS_SERVER:/ /test1

# Wait for it to be ready
sleep 1

echo "NFS Client ready."
