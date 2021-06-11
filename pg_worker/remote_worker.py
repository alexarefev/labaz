import os
import logging
import psycopg2
'''
Management server interaction
'''

def worker_registration(remote_db, logger, *args):
    '''
    Register the worker as a consumer in the particular queue
    '''
    try:
        consumer_name = "{}_{}".format(args[1], args[2])
        sql = "SELECT * FROM pgq.register_consumer('{}', '{}');".format(args[0], consumer_name)
        logger.debug("Customer registration string: {}".format(sql))
        remote_db.execute(sql)
        result = remote_db.fetchone()
        logger.debug("{} consumer has been registred with code: {}".format(args[1], result))
    except Exception as err:
        logger.critical(str(err))

def queue_reading(remote_db, logger, *args):
    '''
    Get batch of messages from the queue
    '''
    result_list = []
    try:
        consumer_name = "{}_{}".format(args[1], args[2])
        while len(result_list) == 0:
            sql = "SELECT * FROM pgq.next_batch('{}', '{}');".format(args[0], consumer_name)
            remote_db.execute(sql)
            result = remote_db.fetchall()
            batch_set = result[0]
            if batch_set[0] is not None:
                sql = "SELECT * FROM pgq.get_batch_events({});".format(batch_set[0])
                remote_db.execute(sql)
                batch = remote_db.fetchall()
                for i in range(0, len(batch)):
                    logger.debug("server: {}, database: {}, user: {}, action: {}, addition: {}".format(
                                  batch[i][8], batch[i][5], batch[i][6], batch[i][4],
                                  batch[i][7]))
                sql = "SELECT * FROM pgq.finish_batch({});".format(batch_set[0])
                remote_db.execute(sql)
                result = remote_db.fetchall()
            else:
                batch = 0
            return batch
    except Exception as err:
        logger.critical(str(err))

<<<<<<< HEAD
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
    PID_DIR = os.environ['PID_DIR']
    LOG_LEVEL = os.environ['LOG_LEVEL']

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)

    logger.info("Host name is {}".format(UNAME))
    logger.info("Backup directory is {}".format(BACKUP_DIR))

    QUEUE_NAME = "pg"
    PREF = "worker"

    pid_path = "{}/{}".format(PID_DIR, WORKER_NAME)
    pid = os.getpid()
    if os.path.isfile(pid_path) is False:
        pid_file = open(pid_path, 'w')
        pid_file.write("{}\n".format(pid))
        pid_file.close()
        logger.info("PID {} saved to {}".format(pid, pid_path))
    else:
        logger.error("PID file exists {}, terminating".format(pid_path))
        exit()

=======
async def db_acknowledge(remote_db, entity_name, ack_type, db_type, logger):
    '''
    Set database status or delete record with particular database from databases list
    '''
>>>>>>> async
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

        worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        while True:
            tasks = queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                for task in tasks:
                    if task[4] == 'create' and UNAME == task[8]:
                        sql = "INSERT INTO mgmt_task (db_name, db_task, db_user, db_secret) VALUES('{}', '{}', '{}', '{}');".format(task[5], '1', task[6], task[7])
                        local_db.execute(sql)
                        logger.debug("Creation task for database {} has been inserted".format(task[5]))
                    elif task[4] == 'delete' and UNAME == task[7]:
                        if task[8] == 'backup':
                            sql = "INSERT INTO mgmt_task(db_name, db_task, db_user) VALUES('{}', '{}', '{}');".format(task[5], '3', task[6])
                            local_db.execute(sql)
                            logger.debug("Delete with backup task for database {} has been inserted".format(task[5]))
                        else:
                            sql = "INSERT INTO mgmt_task(db_name, db_task, db_user) VALUES('{}', '{}', '{}');".format(task[5], '2', task[6])
                            local_db.execute(sql)
                            logger.debug("Delete task for database {} has been inserted".format(task[5]))
                    elif task[4] == 'recover' and UNAME == task[7]:
                        sql = "INSERT INTO mgmt_task(db_name, db_task, db_file, db_user) VALUES('{}', '{}', '{}', '{}');".format(task[5], '4', task[8], task[6])
                        local_db.execute(sql)
                        logger.debug("Recover task for database {} has been inserted".format(task[5]))
                    else:
                        logger.warning('Task for other server or unknown operation')

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
