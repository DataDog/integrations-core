set -e

mkdir -p /etc/mqm/pki/keys
cd /etc/mqm/pki
runmqakm -keydb -create -db ./keys/qm1.kdb -pw Secret13 -stash
runmqakm -cert -create -db ./keys/qm1.kdb -type kdb -pw Secret13 \
-label qm1 -dn CN=qm1 -size 2048 -x509version 3 -expire 365 -fips -sig_alg SHA256WithRSA
runmqakm -keydb -create -db ./keys/client.kdb -pw Secret13 -stash
runmqakm -cert -create -db ./keys/client.kdb -type kdb -pw Secret13 \
-label client -dn CN=client -size 2048 -x509version 3 -expire 365 -fips -sig_alg SHA256WithRSA
runmqakm -cert -extract -db ./keys/qm1.kdb -pw Secret13 \
-label qm1 -target ./keys/qm1.pem
runmqakm -cert -add -db ./keys/client.kdb -pw Secret13 \
-label qm1 -file ./keys/qm1.pem
runmqakm -cert -extract -db ./keys/client.kdb -pw Secret13 \
-label client -target ./keys/client.pem
runmqakm -cert -add -db ./keys/qm1.kdb -pw Secret13 \
-label client -file ./keys/client.pem

cp -r /etc/mqm/pki/keys/* /var/mqm/qmgrs/QM1/ssl/
chown -R mqm /var/mqm/qmgrs/QM1/ssl/
