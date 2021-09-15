'''
Management server interaction
'''
import os
import logging
import psycopg2
import pymysql
from cysystemd.daemon import notify, Notification

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
                    logger.debug("server: {}, database: {}, user: {}, action: {}, backup: {}".format(
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
    LOG_LEVEL = os.environ['LOG_LEVEL']

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
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

        worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        notify(Notification.READY)

        while True:
            tasks = queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                for task in tasks:
                    if task[4] == 'create' and UNAME == task[8]:
                        sql = "INSERT INTO mysql.mgmt_task(db_name, db_task, db_user, db_secret) VALUES('{}', {}, '{}', '{}');".format(task[5], '1', task[6], task[7])
                        logger.debug(sql)
                        local_db.execute(sql)
                        res = local_db.fetchone()
                        logger.debug("Creation task database {} has been inserted with result: {}".format(task[5], res))
                    elif task[4] == 'delete' and UNAME == task[7]:
                        if task[8] == 'backup':
                            sql = "INSERT INTO mysql.mgmt_task(db_name, db_task, db_user) VALUES('{}', {}, '{}');".format(task[5], '3', task[6])
                            logger.debug(sql)
                            local_db.execute(sql)
                            res = local_db.fetchone()
                            logger.debug("Backup task database {} has been inserted with result: {}".format(task[5], res))
                    elif task[4] == 'recover' and UNAME == task[7]:
                        sql = "INSERT INTO mysql.mgmt_task(db_name, db_task, db_file, db_user) VALUES('{}', {}, '{}', '{}');".format(task[5], '4', task[8], task[6])
                        logger.debug(sql)
                        local_db.execute(sql)
                        res = local_db.fetchone()
                        logger.debug("Recover task database {} has been inserted with result {}:".format(task[5], res))
                    else:
                        logger.warning('Task for other server or unknown operation')

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()

