#!/bin/bash
cat <<EOF | sudo tee -a /etc/sysctl.conf
fs.aio-max-nr = 1048576
fs.file-max = 6815744
kernel.shmall = 2097152
kernel.shmmax = 1987162112
kernel.shmmni = 4096
kernel.sem = 250 32000 100 128
net.ipv4.ip_local_port_range = 9000 65500
net.core.rmem_default = 262144
net.core.rmem_max = 4194304
net.core.wmem_default = 262144
net.core.wmem_max = 1048586
EOF
sudo sysctl -p
cat <<EOF | sudo tee -a /etc/security/limits.conf
oracle soft nproc 2047
oracle hard nproc 16384
oracle soft nofile 1024
oracle hard nofile 65536
EOF

sudo mkdir -p /mnt/disks/disk1
sudo mount -o discard,defaults /dev/sdb1 /mnt/disks/disk1/
cp /mnt/disks/disk1/linuxamd64_12102_database_1of2.zip /tmp
cp /mnt/disks/disk1/linuxamd64_12102_database_2of2.zip /tmp

sudo mkdir /u01
sudo chown -R oracle:oinstall /u01
chmod -R 775 /u01
chmod g+s /u01
sudo yum install -y binutils.x86_64 compat-libcap1.x86_64 gcc.x86_64 gcc-c++.x86_64 glibc.i686 glibc.x86_64 \
glibc-devel.i686 glibc-devel.x86_64 ksh compat-libstdc++-33 libaio.i686 libaio.x86_64 libaio-devel.i686 libaio-devel.x86_64 \
libgcc.i686 libgcc.x86_64 libstdc++.i686 libstdc++.x86_64 libstdc++-devel.i686 libstdc++-devel.x86_64 libXi.i686 libXi.x86_64 \
libXtst.i686 libXtst.x86_64 make.x86_64 sysstat.x86_64 zip unzip

sudo dd if=/dev/zero of=/swapfile bs=1M count=16384
sudo chmod 600 /swapfile
sudo mkswap /swapfile
echo '/swapfile swap swap 0 0' | sudo tee -a /etc/fstab
sudo swapon -a

cd /tmp/
unzip linuxamd64_12102_database_1of2.zip
unzip linuxamd64_12102_database_2of2.zip

cd database
sh runInstaller -silent -waitforcompletion -responsefile /tmp/db.rsp -showProgress
sudo /u01/app/oraInventory/orainstRoot.sh
sudo /u01/app/oracle/product/12.1.0/dbhome_1/root.sh
/u01/app/oracle/product/12.1.0/dbhome_1/cfgtoollogs/configToolAllCommands RESPONSE_FILE=/tmp/cfgrsp.properties
ORACLE_SID=orcl ORACLE_HOME=/u01/app/oracle/product/12.1.0/dbhome_1/ /u01/app/oracle/product/12.1.0/dbhome_1/bin/sqlplus / AS SYSDBA @/tmp/grant.sql
