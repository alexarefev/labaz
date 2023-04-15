'''
Local server interaction
'''
import os
import logging
import psycopg2
import pymysql
import cysystemd.daemon as sysd

def create_entity(local_db, remote_db, logger):
    '''
    Create database and user
    '''
    try:
        sql = 'SELECT * FROM mysql.mgmt_task WHERE db_task=1;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        local_connection.commit()
        if tasks:
            for task in tasks:
                sql = f"CREATE DATABASE {task[0]};"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
                logger.debug(f"{task[0]} database has been created")
                sql = f"CREATE USER '{task[2]}'@'%' IDENTIFIED BY '{task[3]}';"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
                logger.debug(f"{task[2]} user has been created")
                sql = f"GRANT ALL ON {task[0]}.* TO '{task[2]}'@'%';"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
                logger.debug(f"Access to {task[0]} database has been granted")
                sql = f"SELECT * FROM public.dback('{task[0]}', 'create', '{QUEUE_NAME}');"
                logger.debug(sql)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{task[0]} {result[1]}")
                sql = f"DELETE FROM mysql.mgmt_task WHERE db_name='{task[0]}' AND db_task=1;"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
    except Exception as err:
        logger.critical(str(err))

def drop_entity(local_db, remote_db, logger):
    '''
    Drop database and user
    '''
    try:
        sql = 'SELECT * FROM mysql.mgmt_task WHERE db_task=2;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        local_connection.commit()
        if tasks:
            for task in tasks:
                sql = f"DROP USER '{task[2]}'@'%';"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
                logger.debug(f"{task[2]} user has been dropped")
                sql = f"DROP DATABASE {task[0]};"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
                logger.debug(f"{task[0]} database has been dropped")
                sql = f"SELECT * FROM public.dback('{task[0]}', 'delete', '{QUEUE_NAME}');"
                logger.debug(sql)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{task[0]} {result[1]}")
                sql = f"DELETE FROM mysql.mgmt_task WHERE db_name='{task[0]}' AND db_task=2;"
                logger.debug(sql)
                local_db.execute(sql)
                local_connection.commit()
    except Exception as err:
        logger.critical(str(err))


if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = os.path.basename(__file__)

    REMOTE_DB_NAME = os.environ['REMOTE_DB_NAME']
    REMOTE_DB_USER = os.environ['REMOTE_DB_USER']
    REMOTE_DB_PASSWORD = os.environ['REMOTE_DB_PASSWORD']
    REMOTE_DB_HOST = os.environ['REMOTE_DB_HOST']

    LOCAL_DB_USER = os.environ['LOCAL_DB_USER']
    LOCAL_DB_PASSWORD = os.environ['LOCAL_DB_PASSWORD']
    LOCAL_DB_NAME = os.environ['LOCAL_DB_NAME']
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
                                           password=LOCAL_DB_PASSWORD,
                                           database=LOCAL_DB_NAME)
        local_db = local_connection.cursor()
        logger.info("MySQL local has been connected")

        sysd.notify(sysd.Notification.READY)

        while True:
            create_entity(local_db, remote_db, logger)
            drop_entity(local_db, remote_db, logger)

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()
