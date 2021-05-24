'''
Locale server interaction
'''
import os
import logging
import psycopg2
import pymysql

def create_entity(local_db, remote_db, logger):
    '''
    Create database and user
    '''
    try:
        sql = 'SELECT * FROM mgmt_task WHERE db_task=1;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        if tasks:
            for task in tasks:
                logger.debug("Task: {}".format(task))
                sql = "CREATE DATABASE {};".format(task[0])
                local_db.execute(sql)
                local_connection.commit()
                logger.debug("{} database has been created".format(task[0]))
                sql = "CREATE USER '{}'@'%' IDENTIFIED BY '{}';".format(task[2], task[3])
                local_db.execute(sql)
                local_connection.commit()
                logger.debug("{} user has been created".format(task[2]))
                sql = "GRANT ALL ON {}.* TO '{}'@'%';".format(task[0], task[2])
                local_db.execute(sql)
                local_connection.commit()
                logger.debug("Access to {} database has been granted".format(task[0]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(task[0], 'create', QUEUE_NAME)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(task[0], result[1]))
                sql = "DELETE FROM mgmt_task WHERE db_name='{}' AND db_task=1".format(task[0])
                local_db.execute(sql)
                local_connection.commit()
        else:
            local_connection.commit()
        return 0
    except Exception as err:
        logger.critical(str(err))

def drop_entity(local_db, remote_db, logger):
    '''
    Drop database and user
    '''
    try:
        sql = 'SELECT * FROM mgmt_task WHERE db_task=2;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        if tasks:
            for task in tasks:
                sql = "DROP USER '{}'@'%';".format(task[2])
                local_db.execute(sql)
                local_connection.commit()
                logger.debug("{} user has been dropped".format(task[2]))
                sql = "DROP DATABASE {};".format(task[0])
                local_db.execute(sql)
                local_connection.commit()
                logger.debug("{} database has been dropped".format(task[0]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(task[0], 'delete', QUEUE_NAME)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(task[0], result[1]))
                sql = "DELETE FROM mysql.mgmt_task WHERE db_name='{}' AND db_task=2".format(task[0])
                local_db.execute(sql)
                local_connection.commit()
        else:
            local_connection.commit()
        return 0
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
    LOCAL_DB_NAME = os.environ['LOCAL_DB_NAME']
    BACKUP_DIR = os.environ['BACKUP_DIR']
    PID_DIR = os.environ['PID_DIR']
    LOG_LEVEL = os.environ['LOG_LEVEL']

    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)

    QUEUE_NAME = "mysql"
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
                                           password=LOCAL_DB_PASSWORD,
                                           database=LOCAL_DB_NAME)
        local_db = local_connection.cursor()
        logger.info("MySQL local has been connected")

        while True:
            create_entity(local_db, remote_db, logger)
            drop_entity(local_db, remote_db, logger)

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
