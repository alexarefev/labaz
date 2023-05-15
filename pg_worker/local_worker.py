'''
Local server interaction
'''
import os
import psycopg2
import logging
import cysystemd.daemon as sysd 

def create_entity(local_db, remote_db, logger):
    '''
    Create database and role
    '''
    try:
        sql = 'SELECT * FROM mgmt_task WHERE db_task=1;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        if tasks:
            for task in tasks:
                logger.debug(task)
                sql = f'CREATE DATABASE "{task[0]}";'
                local_db.execute(sql)
                logger.debug(f"{task[0]} database has been created")
                sql = f'''CREATE ROLE "{task[2]}" WITH LOGIN PASSWORD '{task[4]}';'''
                local_db.execute(sql)
                logger.debug(f"{task[2]} role has been created")
                sql = f'GRANT ALL ON DATABASE "{task[0]}" TO "{task[2]}"'
                local_db.execute(sql)
                logger.debug(f"Access to {task[0]} database has been granted")
                sql = f"SELECT * FROM public.dback('{task[0]}', 'create', '{QUEUE_NAME}');"
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{task[0]} {result[1]}")
                sql = f"DELETE FROM mgmt_task WHERE db_name='{task[0]}' AND db_task=1"
                local_db.execute(sql)
    except Exception as err:
        logger.critical(str(err))

def drop_entity(local_db, remote_db, logger):
    '''
    Drop database and role
    '''
    try:
        sql = f'SELECT * FROM mgmt_task WHERE db_task=2;'
        local_db.execute(sql)
        tasks = local_db.fetchall()
        if tasks:
            for task in tasks:
                logger.debug(task)
                sql = f'ALTER DATABASE "{task[0]}" ALLOW_CONNECTIONS=false;'
                local_db.execute(sql)
                logger.debug(f"Connections to {task[0]} database have been forbidden")
                sql = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{task[0]}';"
                local_db.execute(sql)
                logger.debug(f"Connections to {task[0]} have been dropped")
                sql = f"DROP DATABASE {task[0]};"
                local_db.execute(sql)
                logger.debug(f"{task[0]} database has been dropped")
                sql = f'DROP ROLE "{task[2]}";'
                local_db.execute(sql)
                logger.debug(f"{task[2]} role has been dropped")
                sql = f"SELECT * FROM public.dback('{task[0]}', 'delete', '{QUEUE_NAME}');"
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{task[0]} {result[1]}")
                sql = f"DELETE FROM mgmt_task WHERE db_name='{task[0]}' AND db_task=2"
                local_db.execute(sql)
    except Exception as err:
        logger.critical(str(err))

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

    logger.info(f"Host name is {UNAME}")
    logger.info(f"Backup directory is {BACKUP_DIR}")

    QUEUE_NAME = "pg"
    PREF = "worker"


    try:
        remote_connection_string = (f"host='{REMOTE_DB_HOST}' dbname='{REMOTE_DB_NAME}' user='{REMOTE_DB_USER}' password='{REMOTE_DB_PASSWORD}' port=5432")
        logger.debug(remote_connection_string)
        remote_connection = psycopg2.connect(remote_connection_string)
        remote_db = remote_connection.cursor()
        remote_connection.autocommit = True
        logger.info(f"PostgreSQL Management has been connected")
        local_connection_string = (f"dbname='{LOCAL_DB_NAME}' user='{LOCAL_DB_USER}'")
        local_connection = psycopg2.connect(local_connection_string)
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info(f"PostgreSQL local has been connected")
        
        sysd.notify(sysd.Notification.READY)

        while True:
            create_entity(local_db, remote_db, logger)
            drop_entity(local_db, remote_db, logger)

    except Exception as err:
        logger.critical(str(err))
    finally:
        if remote_connection:
            remote_db.close()
            remote_connection.close()
        if local_connection:
            local_db.close()
            local_connection.close()
