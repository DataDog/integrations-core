#Copyright (c) 2014, 2020, Oracle and/or its affiliates.
#
#Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# ADAPTED FROM THE ORACLE DOCKERFILES PROJECT
# -------------------------------------------
# https://github.com/oracle/docker-images/tree/main/OracleWebLogic/samples

# This Dockerfile extends the Oracle WebLogic image by creating a sample domain and deploys a sample application.
#
# Pull base image
# ---------------
ARG WEBLOGIC_VERSION

FROM container-registry.oracle.com/middleware/weblogic:${WEBLOGIC_VERSION} as wls_base

ARG APPLICATION_NAME="${APPLICATION_NAME:-sample}"
ARG APPLICATION_PKG="${APPLICATION_PKG:-archive.zip}"
ARG CUSTOM_DOMAIN_NAME="${CUSTOM_DOMAIN_NAME:-domain1}"
ARG CUSTOM_ADMIN_PORT="${CUSTOM_ADMIN_PORT:-7001}"
ARG CUSTOM_ADMIN_SERVER_SSL_PORT="${CUSTOM_ADMIN_SERVER_SSL_PORT:-7002}"
ARG CUSTOM_MANAGED_SERVER_PORT="${CUSTOM_MANAGED_SERVER_PORT:-8001}"
ARG CUSTOM_MANAGED_SERVER_SSL_PORT="${CUSTOM_MANAGED_SERVER_SSL_PORT:-8002}"
ARG CUSTOM_DEBUG_PORT="${CUSTOM_DEBUG_PORT:-8453}"
ARG CUSTOM_ADMIN_NAME="${CUSTOM_ADMIN_NAME:-admin-server}"
ARG CUSTOM_ADMIN_HOST="${CUSTOM_ADMIN_HOST:-wlsadmin}"
ARG CUSTOM_CLUSTER_NAME="${CUSTOM_CLUSTER_NAME:-cluster-1}"
ARG CUSTOM_CLUSTER_TYPE="${CUSTOM_CLUSTER_TYPE:-DYNAMIC}"
ARG CUSTOM_SSL_ENABLED="${CUSTOM_SSL_ENABLED:-false}"



# WLS Configuration
# ---------------------------
ENV APP_NAME="${APPLICATION_NAME}" \
    APP_FILE="${APPLICATION_NAME}.war" \
    APP_PKG_FILE="${APPLICATION_PKG}" \
    ORACLE_HOME=/u01/oracle \
    PROPERTIES_FILE_DIR="/u01/oracle/properties" \
    SSL_ENABLED="${CUSTOM_SSL_ENABLED}" \
    DOMAIN_NAME="${CUSTOM_DOMAIN_NAME}" \
    DOMAIN_HOME="/u01/oracle/user_projects/domains/${CUSTOM_DOMAIN_NAME}" \
    ADMIN_PORT="${CUSTOM_ADMIN_PORT}" \
    ADMIN_SERVER_SSL_PORT="${CUSTOM_ADMIN_SERVER_SSL_PORT}" \
    ADMIN_NAME="${CUSTOM_ADMIN_NAME}" \
    ADMIN_HOST="${CUSTOM_ADMIN_HOST}" \
    CLUSTER_NAME="${CUSTOM_CLUSTER_NAME}" \
    MANAGED_SERVER_PORT="${CUSTOM_MANAGED_SERVER_PORT}" \
    MANAGED_SERVER_SSL_PORT="${CUSTOM_MANAGED_SERVER_SSL_PORT}" \
#    MANAGED_SERV_NAME="${CUSTOM_MANAGED_SERV_NAME}" \
    DEBUG_PORT="8453" \
    PATH=$PATH:/u01/oracle/oracle_common/common/bin:/u01/oracle/wlserver/common/bin:${DOMAIN_HOME}:${DOMAIN_HOME}/bin:/u01/oracle

# Retrieve the files required to build this image

# https://github.com/oracle/docker-images/tree/d64e2b42e81ef036057de0d03f7561e1fb5192bb/OracleWebLogic/samples/12213-deploy-application
RUN cd /u01/oracle & curl -L https://github.com/oracle/docker-images/archive/refs/heads/main.tar.gz | tar xz --strip=4 "docker-images-main/OracleWebLogic/samples/12213-deploy-application/sample" "docker-images-main/OracleWebLogic/samples/12213-deploy-application/build-archive.sh"

# https://github.com/oracle/docker-images/tree/1e26820b44c393944b20f0ae069670538a2e37ef/OracleWebLogic/samples/12213-domain-home-in-image/container-scripts

RUN curl -L https://github.com/oracle/docker-images/archive/refs/heads/main.tar.gz | tar xz --strip=5 "docker-images-main/OracleWebLogic/samples/12213-domain-home-in-image/container-scripts" "docker-images-main/OracleWebLogic/samples/12213-deploy-application/container-scripts"


COPY --chown=oracle:root setup_scripts/* /u01/oracle/

#Create directory where domain will be written to
USER root
RUN chmod +xw /u01/oracle/*.sh && \
    chmod +xw /u01/oracle/*.py && \
    mkdir -p ${PROPERTIES_FILE_DIR} && \
    mkdir -p $DOMAIN_HOME && \
    chown -R oracle:root $DOMAIN_HOME/.. && \
    chown -R oracle:root ${PROPERTIES_FILE_DIR}


COPY --chown=oracle:root properties/docker-build/domain*.properties ${PROPERTIES_FILE_DIR}/

# Configuration of WLS Domain
USER oracle
RUN /u01/oracle/createWLSDomain.sh && \
    chmod -R g+w $DOMAIN_HOME && \
    echo ". $DOMAIN_HOME/bin/setDomainEnv.sh" >> /u01/oracle/.bashrc


RUN /u01/oracle/build-archive.sh
RUN /u01/oracle/setEnv.sh ${PROPERTIES_FILE_DIR}/docker-build/domain.properties

# Expose ports for admin, managed server, and debug
EXPOSE $ADMIN_PORT $ADMIN_SERVER_SSL_PORT $MANAGED_SERVER_PORT $MANAGED_SERVER_SSL_PORT $DEBUG_PORT


# Build from WebLogic Server Base Image
FROM wls_base

WORKDIR $DOMAIN_HOME

# Deploy sample application in WLST Offline mode

RUN cd /u01/oracle & $JAVA_HOME/bin/jar xf /u01/oracle/$APP_PKG_FILE && \
    /u01/oracle/deployAppToDomain.sh

# Define default command to start bash.
CMD ["startAdminServer.sh"]
