FROM alpine:3.17.0
COPY ca.* /root/ca_cert/
COPY ssl.conf /opt/ssl.conf
RUN apk add --no-cache openssl git build-base

# Build the faketime lib, used to generate expired certificate
RUN git clone https://github.com/wolfcw/libfaketime /libfaketime
WORKDIR /libfaketime
RUN git checkout v0.9.10 \
 && make \
 && make install \
 && cp /usr/local/lib/faketime/libfaketimeMT.so.1 /lib/faketime.so

# Generate certs
WORKDIR /root/certs

## Generate a valid certificate for valid.mock

RUN openssl genrsa -out valid.mock.key 2048 \
 && openssl req -new -sha256 -key valid.mock.key -subj "/C=US/ST=NY/O=foo/CN=valid.mock" -config /opt/ssl.conf -out valid.mock.csr \
 && openssl x509 -req -in valid.mock.csr -CA /root/ca_cert/ca.crt -CAkey /root/ca_cert/ca.key -CAcreateserial -out valid.mock.crt -extensions req_ext -extfile /opt/ssl.conf -days 200 -sha256

## Generate a self-signed non-expired certificate for selfsigned.mock

RUN openssl req -nodes -new -x509 -days 1 -keyout selfsigned.mock.key -out selfsigned.mock.cert -subj "/C=US/ST=NY/O=foo/CN=selfsigned.mock" -addext "subjectAltName = DNS:selfsigned.mock"


## Generate a valid but expired certificate for expired.mock
ENV LD_PRELOAD=/lib/faketime.so
ENV FAKETIME="-15d"
ENV DONT_FAKE_MONOTONIC=1
RUN openssl genrsa -out expired.mock.key 2048 \
 && openssl req -new -sha256 -key expired.mock.key -subj "/C=US/ST=NY/O=foo/CN=expired.mock" -out expired.mock.csr \
 && openssl x509 -req -in expired.mock.csr -CA /root/ca_cert/ca.crt -CAkey /root/ca_cert/ca.key -CAcreateserial -out expired.mock.crt -days 1 -sha256

## Prepare postgresql certificates
ENV PSQL_UID=70
ENV PSQL_GUID=70
RUN for file in valid.mock.key valid.mock.crt; do cp $file postgres.$file; chown $PSQL_UID:$PSQL_GUID postgres.$file; done

## Prepare mysql certificates
ENV MYSQL_UID=999
ENV MYSQL_GUID=999
RUN for file in valid.mock.key valid.mock.crt; do cp $file mysql.$file; chown $MYSQL_UID:$MYSQL_GUID mysql.$file; done
