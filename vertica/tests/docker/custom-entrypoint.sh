#!/usr/bin/env bash

# NOTICE: This is a slightly modified version of the file found at
# https://github.com/vertica/vertica-containers/blob/0d200b500c3c47b4d6dc10c8f170210301b0ffe5/one-node-ce/docker-entrypoint.sh

# (c) Copyright [2021] Micro Focus or one of its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DEBUG_FAILING_STARTUP=y
if [ "${DEBUG_FAILING_STARTUP}" != "y" ]; then
  # Stop container, if any error occurs during startup
  # Can be overriden by setting DEBUG_FAILING_STARTUP to "y"
  set -e
fi

# We have to export it here, vertica_env.sh is not propagated into entrypoint script
export VERTICA_DB_USER="`whoami`"
echo VERTICA_DB_USER is \"$VERTICA_DB_USER\"
STOP_LOOP="false"
VSQL="${VERTICA_OPT_DIR}/bin/vsql -U ${VERTICA_DB_USER}"
ADMINTOOLS="${VERTICA_OPT_DIR}/bin/admintools"

function start_agent() {
    echo "Starting MC agent"
    # suppress errors about lack of systemd
    sudo ${VERTICA_OPT_DIR}/sbin/vertica_agent start \
         2> ${VERTICA_DATA_DIR}/${VERTICA_DB_NAME}/agent_start.err \
         1> ${VERTICA_DATA_DIR}/${VERTICA_DB_NAME}/agent_start.out
}

function stop_agent() {
    echo "Shutting down MC agent"
    # suppress errors about lack of systemd
    sudo ${VERTICA_OPT_DIR}/sbin/vertica_agent stop \
         2> ${VERTICA_DATA_DIR}/${VERTICA_DB_NAME}/agent_stop.err \
         1> ${VERTICA_DATA_DIR}/${VERTICA_DB_NAME}/agent_stop.out
}

# Vertica should be shut down properly
function shut_down() {
    echo "Shutting Down"
    vertica_proper_shutdown
    echo 'Stopping loop'
    STOP_LOOP="true"
}

function vertica_proper_shutdown() {
    db=$(${ADMINTOOLS} -t show_active_db)
    case "$db"x in
        x) 
            echo "Database not running --- shutting down"
            ;;
        *)
            stop_agent
            echo 'Vertica: Closing active sessions'
            ${VSQL} -c 'SELECT CLOSE_ALL_SESSIONS();'
            echo 'Vertica: Flushing everything on disk'
            ${VSQL} -c 'SELECT MAKE_AHM_NOW();'
            echo 'Vertica: Stopping database'
            ${ADMINTOOLS} -t stop_db -d $VERTICA_DB_NAME -i
            ;;
    esac
}

function create_app_db_user() {
    echo ''
    echo "Creating APP DB user ${APP_DB_USER} ... "
    CHECK_STRING="ALREADY_EXISTS"
    CHECK_QUERY="select case when count(*) > 0 then '${CHECK_STRING}' end from users where user_name = '${APP_DB_USER}'"
    ALREADY_EXISTS=$($VSQL -c "${CHECK_QUERY}" | grep ${CHECK_STRING} | sed 's/ //g' || true)
    if [ "${ALREADY_EXISTS}" != "${CHECK_STRING}" ]; then
        ${VSQL} -c "create user ${APP_DB_USER}"
        ${VSQL} -c "grant pseudosuperuser to ${APP_DB_USER}"
        ${VSQL} -c "alter user ${APP_DB_USER} default role all"
    fi
    # Alter the user password everytime to support change of the password
    # We must prevent error "ROLLBACK 2301:  Can not reuse current password" with " || true"
    ${VSQL} -c "alter user ${APP_DB_USER} identified by '${APP_DB_PASSWORD}'" || true
}

function preserve_config() {
    # unfortunately, admintools doesn't (always) obey symlinks when
    # manipulating its admintools.conf file, so we have to move the
    # entire config directory  
    if [ -f ${VERTICA_DATA_DIR}/config/admintools.conf ]; then
        # second and subsequent times starting the container
        # we have an admintools.conf in ${VERTICA_DATA_DIR}
        echo "config has already been preserved"
    else
        # first time through docker-entrypoint.sh we need to move
        # the config directory to persistent store
        echo "Moving config directory tree to persistent store"
        sudo cp --archive ${VERTICA_OPT_DIR}/config ${VERTICA_DATA_DIR}
        sudo chown -R ${VERTICA_DB_USER} ${VERTICA_DATA_DIR}/config
    fi
    # unfortunately, the symlink is in the container image
    # so we have to renew it each time
    if [ ! -L ${VERTICA_OPT_DIR}/config ]; then
        echo "symlink ${VERTICA_OPT_DIR}/config -> ${VERTICA_DATA_DIR}/config"
        rm -rf ${VERTICA_OPT_DIR}/config
        ln -s  ${VERTICA_DATA_DIR}/config  ${VERTICA_OPT_DIR}/config
    fi
}       


trap "shut_down" SIGKILL SIGTERM SIGHUP SIGINT
if [ -n "${TZ}" ]; then
  echo "Custom time zone required - ${TZ}"
  if [ ! -f "${VERTICA_OPT_DIR}/share/timezone/${TZ}" ]; then
    echo "ERROR: timezone file ${VERTICA_OPT_DIR}/${TZ} does not exist"
    echo "Check Dockerfile and uncomment a workaround solution linking system time zones"
    exit 1
  fi
fi

echo 'Starting up'
if [ ! -d ${VERTICA_DATA_DIR}/${VERTICA_DB_NAME} ]; then
    # first time through --- create db, etc.
    mkdir -p ${VERTICA_DATA_DIR}/config
    preserve_config
    echo 'Creating database'

    ${ADMINTOOLS} -t create_db \
                  --skip-fs-checks \
                  -s localhost \
                  --database=$VERTICA_DB_NAME \
                  --catalog_path=${VERTICA_DATA_DIR} \
                  --data_path=${VERTICA_DATA_DIR}

    # These are the lines that we remove from the original script
    # echo 'Loading VMart schema ...'
    # ${VMART_DIR}/${VMART_ETL_SCRIPT}

    if [ -n "${APP_DB_USER}" ]; then
        create_app_db_user
    fi
else
    # ${VERTICA_OPT_DIR}/config/admintools.conf is the unmodified container
    # copy, but we symlinked it the first time through, and have to
    # recreate that symlink
    preserve_config
    echo 'Starting Database'
    ${ADMINTOOLS} -t start_db \
                  --database=$VERTICA_DB_NAME \
                  --noprompts
fi

echo
if [ -d /docker-entrypoint-initdb.d/ ]; then
    echo "Running entrypoint scripts ..."
    for f in $(ls /docker-entrypoint-initdb.d/* | sort); do
        case "$f" in
            *.sh)     echo "$0: running $f"; . "$f" ;;
            *.sql)    echo "$0: running $f"; ${VSQL} -f $f; echo ;;
            *)        echo "$0: ignoring $f" ;;
        esac
        echo
    done
fi

# cron(d) daemonizes, so no need for launching as background process
if grep -q -i debian /etc/os-release; then
    sudo /usr/sbin/cron
else
    sudo /usr/sbin/crond
fi
start_agent

echo
echo "Vertica is now running"

while [ "${STOP_LOOP}" == "false" ]; do
    # We could use admintools -t show_active_db to see if the
    # db is still running, and restart it if it isn't
    sleep 1
done

