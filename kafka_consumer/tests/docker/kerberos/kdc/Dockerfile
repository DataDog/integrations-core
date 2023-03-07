FROM centos:7

ENV container docker

# 1. Installing Kerberos server, admin and client
RUN yum install -y krb5-server krb5-libs krb5-auth-dialog
RUN yum install -y krb5-workstation krb5-libs

# 2. Configuring Kerberos and KDC
COPY krb5.conf /etc/krb5.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh
RUN mkdir /var/log/kerberos
RUN mkdir /etc/kdc
RUN mkdir -p /var/kerberos/krb5kdc/
RUN ln -s /etc/krb5.conf /etc/kdc/krb5.conf

EXPOSE 88

RUN kdb5_util -P confluent -r TEST.CONFLUENT.IO create -s

ENTRYPOINT ["/start.sh"]
