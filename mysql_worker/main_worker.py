'''
Main module
'''
import os
import logging
import psycopg2
import pymysql
import local_worker
import remote_worker

if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = __file__

    REMOTE_DB_NAME = os.environ['REMOTE_DB_NAME']
    REMOTE_DB_USER = os.environ['REMOTE_DB_USER']
    REMOTE_DB_PASSWORD = os.environ['REMOTE_DB_PASSWORD']
    REMOTE_DB_HOST = os.environ['REMOTE_DB_HOST']

    LOCAL_DB_USER = os.environ['LOCAL_DB_USER']
    LOCAL_DB_PASSWORD = os.environ['LOCAL_DB_PASSWORD']
    BACKUP_DIR = os.environ['BACKUP_DIR']

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)

    QUEUE_NAME = "mysql"
    PREF = "worker"

    try:
        remote_connection = psycopg2.connect(host=REMOTE_DB_HOST, 
                                             dbname=REMOTE_DB_NAME, 
                                             user=REMOTE_DB_USER, 
                                             password=REMOTE_DB_PASSWORD,
                                             port=5432)
        remote_db = remote_connection.cursor()
        remote_connection.autocommit = True
        logger.info("PostgreSQL Management has been connected")
        local_connection = pymysql.connect(user=LOCAL_DB_USER,
                                           password=LOCAL_DB_PASSWORD)
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info("MySQL local has been connected")

        remote_worker.worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        while True:
            tasks = remote_worker.queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                logger.debug("Task: %s" % str(tasks))
                for i in range(0, len(tasks)):
                    if tasks[i][4] == 'create' and UNAME == tasks[i][8]:
                        local_worker.create_entity(tasks[i], local_db, logger)
                        remote_worker.creation_acknowledge(remote_db, tasks[i][5], logger)
                    elif tasks[i][4] == 'delete' and UNAME == tasks[i][7]:
                        if tasks[i][8] == 'backup':
                            result = local_worker.backup_entity(tasks[i][5], LOCAL_DB_USER, LOCAL_DB_PASSWORD, BACKUP_DIR, logger)
                        local_worker.drop_entity(tasks[i], local_db, logger)
                        remote_worker.deletion_acknowledge(remote_db, tasks[i][5], logger)
                    else:
                        logger.warning('Task for other server or unknown operation')

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
