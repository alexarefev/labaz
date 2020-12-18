#!/bin/bash
export BACKUP_DIR="/mnt/backups/mysql"
export REMOTE_DB_NAME="pgmgmt"
export REMOTE_DB_USER="pgmgmt"
export REMOTE_DB_PASSWORD="paaasssworddd"
export REMOTE_DB_HOST="pg-mgmt"
export LOCAL_DB_USER="mysql"
export LOCAL_DB_PASSWORD="mmmyyy"

python3 main_worker.py > /var/log/pgmgmt/worker.log 2>&1 &
