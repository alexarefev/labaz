#!/bin/bash
export BACKUP_DIR="/mnt/backups"
export LOCAL_DB_NAME="pgmgmt"
export LOCAL_DB_USER="pgmgmt"
export LOCAL_DB_PASSWORD="paaasssworddd"
export LOG_LEVEL="DEBUG"

export API_PORT="8081"
python3 api.py  >> /var/log/pgmgmt/api.log 2>&1 &
export API_PORT="8082"
python3 api.py  >> /var/log/pgmgmt/api.log 2>&1 &
export API_PORT="8083"
python3 api.py  >> /var/log/pgmgmt/api.log 2>&1 &
export API_PORT="8084"
python3 api.py  >> /var/log/pgmgmt/api.log 2>&1 &
