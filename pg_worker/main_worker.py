'''
Main module
'''
import os
import logging
import psycopg2
import local_worker
import remote_worker

def task_processing(task, local_db, remote_db, logger, backup):
    if task[4] == 'create' and UNAME == task[8]:
        result = local_worker.create_entity(task, local_db, logger)
        if result == 0:
            remote_worker.db_acknowledge(remote_db, task[5], 'create', QUEUE_NAME, logger)
    elif task[4] == 'delete' and UNAME == task[7]:
        if task[8] == 'backup':
            result = local_worker.backup_entity(UNAME, task[5], backup, logger)
            if result == 0:
                pass
            else:
                logger.error("Backup error {}".format(result))
                return 1
        local_worker.drop_entity(task, local_db, logger)
        remote_worker.db_acknowledge(remote_db, task[5], 'delete', QUEUE_NAME, logger)
    elif task[4] == 'recover' and UNAME == task[7]:
        result = local_worker.recover_entity(task, local_db, BACKUP_DIR, logger)
        if result == 0:
            remote_worker.db_acknowledge(remote_db, task[5], 'create', QUEUE_NAME, logger)
    else:
        logger.warning('Task for other server or unknown operation')
    return 0

if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = __file__

    REMOTE_DB_NAME = os.environ['REMOTE_DB_NAME']
    REMOTE_DB_USER = os.environ['REMOTE_DB_USER']
    REMOTE_DB_PASSWORD = os.environ['REMOTE_DB_PASSWORD']
    REMOTE_DB_HOST = os.environ['REMOTE_DB_HOST']

    LOCAL_DB_NAME = os.environ['LOCAL_DB_NAME']
    LOCAL_DB_USER = os.environ['LOCAL_DB_USER']
    BACKUP_DIR = os.environ['BACKUP_DIR']
    LOG_LEVEL = os.environ['LOG_LEVEL']

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)

    logger.info("Host name is {}".format(UNAME))
    logger.info("Backup directory is {}".format(BACKUP_DIR))

    QUEUE_NAME = "pg"
    PREF = "worker"

    try:
        remote_connection_string = ("host='{}' dbname='{}' user='{}' password='{}' port=5432".format(
                                     REMOTE_DB_HOST, REMOTE_DB_NAME, REMOTE_DB_USER, REMOTE_DB_PASSWORD))
        logger.debug(remote_connection_string)
        remote_connection = psycopg2.connect(remote_connection_string)
        remote_db = remote_connection.cursor()
        remote_connection.autocommit = True
        logger.info("PostgreSQL Management has been connected")
        local_connection_string = ("dbname='{}' user='{}'".format(LOCAL_DB_NAME, LOCAL_DB_USER))
        local_connection = psycopg2.connect(local_connection_string)
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info("PostgreSQL local has been connected")

        remote_worker.worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        while True:
            tasks = remote_worker.queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                logger.debug("Task: {}".format(tasks))
                for task in tasks:
                    task_processing(task, local_db, remote_db, logger, BACKUP_DIR)

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
