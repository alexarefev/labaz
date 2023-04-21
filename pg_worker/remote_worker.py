import os
import logging
import psycopg2
import cysystemd.daemon as sysd

'''
Management server interaction
'''

def worker_registration(remote_db, logger, *args):
    '''
    Register the worker as a consumer in the particular queue
    '''
    try:
        consumer_name = "{args[1]}_{args[2]}"
        sql = f"SELECT * FROM pgq.register_consumer('{args[0]}', '{consumer_name}');"
        logger.debug(f"Customer registration string: {sql}")
        remote_db.execute(sql)
        result = remote_db.fetchone()
        logger.debug(f"{args[1]} consumer has been registred with code: {result}")
    except Exception as err:
        logger.critical(str(err))

def queue_reading(remote_db, logger, *args):
    '''
    Get batch of messages from the queue
    '''
    result_list = []
    try:
        consumer_name = "{args[1]}_{args[2]}"
        while len(result_list) == 0:
            sql = f"SELECT * FROM pgq.next_batch('{args[0]}', '{consumer_name}');"
            remote_db.execute(sql)
            result = remote_db.fetchall()
            batch_set = result[0]
            if batch_set[0] is not None:
                sql = f"SELECT * FROM pgq.get_batch_events({batch_set[0]});"
                remote_db.execute(sql)
                batch = remote_db.fetchall()
                for i in range(0, len(batch)):
                    logger.debug(f"server: {batch[i][8]}, database: {batch[i][5]}, user: {batch[i][6]}, action: {batch[i][4]}, addition: {batch[i][7]}"
                sql = f"SELECT * FROM pgq.finish_batch({batch_set[0]});"
                remote_db.execute(sql)
                result = remote_db.fetchall()
            else:
                batch = 0
            return batch
    except Exception as err:
        logger.critical(str(err))

if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = os.path.basename(__file__)

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

    logger.info("Host name is {UNAME}")
    logger.info("Backup directory is {BACKUP_DIR}")

    QUEUE_NAME = "pg"
    PREF = "worker"


    try:
        remote_connection_string = ("host='{REMOTE_DB_HOST}' dbname='{REMOTE_DB_NAME}' user='{REMOTE_DB_USER}' password='{REMOTE_DB_PASSWORD port=5432")
        logger.debug(remote_connection_string)
        remote_connection = psycopg2.connect(remote_connection_string)
        remote_db = remote_connection.cursor()
        remote_connection.autocommit = True
        logger.info("PostgreSQL Management has been connected")
        local_connection_string = ("dbname='{LOCAL_DB_NAME}' user='{LOCAL_DB_USER}'")
        local_connection = psycopg2.connect(local_connection_string)
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info("PostgreSQL local has been connected")

        worker_registration(remote_db, logger, QUEUE_NAME, PREF, UNAME)

        sysd.notify(sysd.Notification.READY)

        while True:
            tasks = queue_reading(remote_db, logger, QUEUE_NAME, PREF, UNAME)
            if tasks:
                for task in tasks:
                    if task[4] == 'create' and UNAME == task[8]:
                        sql = f"INSERT INTO mgmt_task (db_name, db_task, db_user, db_secret) VALUES('{task[5]}, '1', '{task[6]}', '{task[7]}')"
                        local_db.execute(sql)
                        logger.debug(f"Creation task for database {task[5]} has been inserted")
                    elif task[4] == 'delete' and UNAME == task[7]:
                        if task[8] == 'backup':
                            sql = f"INSERT INTO mgmt_task(db_name, db_task, db_user) VALUES('{task[5]}', '3', '{task[6]}'")
                            local_db.execute(sql)
                            logger.debug(f"Delete with backup task for database {task[5]} has been inserted")
                        else:
                            sql = f"INSERT INTO mgmt_task(db_name, db_task, db_user) VALUES('{task[5]}', '2', '{task[6]}'")
                            local_db.execute(sql)
                            logger.debug(f"Delete task for database {task[5]} has been inserted")
                    elif task[4] == 'recover' and UNAME == task[7]:
                        sql = f"INSERT INTO mgmt_task(db_name, db_task, db_file, db_user) VALUES('{task[5]}', '4', '{task[8]}', '{task[6]}'")
                        local_db.execute(sql)
                        logger.debug(f"Recover task for database {task[5]} has been inserted")
                    else:
                        logger.warning('Task for other server or unknown operation')

    except Exception as err:
        logger.critical(str(err))
    finally:
        if remote_connection:
            remote_db.close()
            remote_connection.close()
        if local_connection:
            local_db.close()
            local_connection.close()

