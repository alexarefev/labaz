#!/bin/bash
export BACKUP_DIR="/mnt/backups/mysql"
export REMOTE_DB_NAME="pgmgmt"
export REMOTE_DB_USER="pgmgmt"
export REMOTE_DB_PASSWORD="paaasssworddd"
export REMOTE_DB_HOST="pg-mgmt"
export LOCAL_DB_USER="mysql"
export LOCAL_DB_PASSWORD="mmmyyy"
export LOCAL_DB_NAME="mysql"
export LOG_LEVEL="DEBUG"
export PID_DIR="/run/pgmgmt"

python3 remote_worker.py >> /var/log/pgmgmt/worker.log 2>&1 &
python3 local_worker.py >> /var/log/pgmgmt/worker.log 2>&1 &
python3 local_worker_async.py >> /var/log/pgmgmt/worker.log 2>&1 &
