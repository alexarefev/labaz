#!/bin/bash
export BACKUP_DIR="/mnt/backups/pg"
export REMOTE_DB_NAME="pgmgmt"
export REMOTE_DB_USER="pgmgmt"
export REMOTE_DB_PASSWORD="paaasssworddd"
export REMOTE_DB_HOST="pg-mgmt"
export LOCAL_DB_NAME="postgres"
export LOCAL_DB_USER="pg"
export LOCAL_DB_PASSWORD="pgpgpgpppp"
export LOG_LEVEL="DEBUG"

python3 remote_worker.py >> /var/log/pgmgmt/worker.log 2>&1 &
python3 local_worker.py >> /var/log/pgmgmt/worker.log 2>&1 &
python3 local_worker_async.py >> /var/log/pgmgmt/worker.log 2>&1 &
