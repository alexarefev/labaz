'''
Local server interaction
'''
import os
import psycopg2
import asyncio
import logging
import cysystemd.daemon as sysd

async def proc_entity(tsk, local_db, remote_db, logger):
    try:
        if tsk[1] == 3:
            '''
            Perform a backup
            '''
            logger.debug(f"Backup DB: {tsk[0]}")
            sql = f"UPDATE mgmt_task SET db_task=5 WHERE db_name='{tsk[0]}' AND db_task=3"
            local_db.execute(sql)
            backup_command = f"pg_dump -d {tsk[0]} | gzip -c > {BACKUP_DIR}/{UNAME}_{tsk[0]}.gz"
            proc = await asyncio.create_subprocess_shell(backup_command)
            await proc.wait()
            result = proc.returncode
            logger.debug(f"{tsk[0]} has been backuped into {BACKUP_DIR} with result {result}")
            if result == 0:
                sql = f'ALTER DATABASE "{tsk[0]}" ALLOW_CONNECTIONS=false;'
                local_db.execute(sql)
                logger.debug(f"Connections to {tsk[0]} database have been forbidden")
                sql = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{tsk[0]}';"
                local_db.execute(sql)
                logger.debug(f"Connections to {tsk[0]} have been dropped")
                sql = f"DROP DATABASE {tsk[0]};"
                local_db.execute(sql)
                logger.debug(f"{tsk[0]} database has been dropped")
                sql = f'DROP ROLE "{tsk[2]}";'
                local_db.execute(sql)
                logger.debug(f"{tsk[2]} role has been dropped")
                sql = f"SELECT * FROM public.dback('{tsk[0]}', 'delete', '{QUEUE_NAME}');"
                remote_db.execute(sql)                
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{tsk[0]} {result[1]}")
                sql = f"DELETE FROM mgmt_task WHERE db_name='{tsk[0]}' AND db_task=5"
                local_db.execute(sql)
        elif tsk[1] == 4:
            '''
            Recover from a backup
            '''
            logger.debug(f"Recovery DB: {tsk[0]}") 
            sql = f"UPDATE mgmt_task SET db_task=6 WHERE db_name='{tsk[0]}' AND db_task=4"
            local_db.execute(sql)
            recovery_command = (f"gunzip < {BACKUP_DIR}/{tsk[3]} | psql {tsk[0]}")
            proc = await asyncio.create_subprocess_shell(recovery_command)
            await proc.wait()
            result = proc.returncode
            logger.debug(f"{tsk[0]} has been recovered with result {result}")
            if result == 0:
                sql = f'GRANT ALL ON DATABASE "{tsk[0]}" TO "{tsk[2]}"'
                local_db.execute(sql)
                logger.debug(f"Access to {tsk[0]} database has been granted")
                sql = f"SELECT * FROM public.dback('{tsk[0]}', 'create', '{QUEUE_NAME}');"
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug(f"{tsk[0]} {result[1]}")
                sql = f"DELETE FROM mgmt_task WHERE db_name='{tsk[0]}' AND db_task=6"
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
            sql = f'SELECT * FROM mgmt_task WHERE db_task=3 OR db_task=4;'
            local_db.execute(sql)
            tasks = local_db.fetchall()
            if tasks:
                logger.debug(f"Task: {tasks}")
                coroutines = asyncio.gather(*[proc_entity(task, local_db, remote_db, logger) for task in tasks])
                loop = asyncio.get_event_loop()
                loop.run_until_complete(coroutines)

    except Exception as err:
        logger.critical(str(err))
    finally:
        if remote_connection:
            remote_db.close()
            remote_connection.close()
        if local_connection:
            local_db.close()
            local_connection.close()
