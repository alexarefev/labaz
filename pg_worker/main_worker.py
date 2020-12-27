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
        local_worker.create_entity(task, local_db, logger)
        remote_worker.creation_acknowledge(remote_db, task[5], logger)
    elif task[4] == 'delete' and UNAME == task[7]:
        if task[8] == 'backup':
            result = local_worker.backup_entity(UNAME, task[5], backup, logger)
        local_worker.drop_entity(task, local_db, logger)
        remote_worker.deletion_acknowledge(remote_db, task[5], logger)
    else:
        logger.warning('Task for other server or unknown operation')

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

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)

    logger.info("MY NAME IS %s" % UNAME)
    logger.info("BACKUP_DIR IS %s" % BACKUP_DIR)

    QUEUE_NAME = "pg"
    PREF = "worker"

    try:
        remote_connection_string = ("host='%s' dbname='%s' user='%s' password='%s' port=5432"
                                    % (REMOTE_DB_HOST, REMOTE_DB_NAME, REMOTE_DB_USER, 
                                       REMOTE_DB_PASSWORD))
        logger.debug(remote_connection_string)
        remote_connection = psycopg2.connect(remote_connection_string)
        remote_db = remote_connection.cursor()
        remote_connection.autocommit = True
        logger.info("PostgreSQL Management has been connected")
        local_connection_string = ("dbname='%s' user='%s'" % (LOCAL_DB_NAME, LOCAL_DB_USER))
        local_connection = psycopg2.connect(local_connection_string)
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info("PostgreSQL local has been connected")

        remote_worker.worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        while True:
            tasks = remote_worker.queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                logger.debug("Task: %s" % str(tasks))
                for task in tasks:
                    task_processing(task, local_db, remote_db, logger, BACKUP_DIR)

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
