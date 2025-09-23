FROM centos:7

ENV container docker

# 1. Installing Kerberos server, admin and client
# mirrorlist.contos.org does not exits anymore, the below stack exchange post suggests a workaround
# https://serverfault.com/questions/1161816/mirrorlist-centos-org-no-longer-resolve

RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && \
    sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && \
    sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
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
