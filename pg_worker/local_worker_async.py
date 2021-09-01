'''
Locale server interaction
'''
import os
import psycopg2
import asyncio
import logging
import systemd.daemon


async def proc_entity(tsk, local_db, remote_db, logger):
    try:
        if tsk[1] == 3:
            '''
            Perform a backup
            '''
            logger.debug("Backup DB: {}".format(tsk[0]))
            sql = "UPDATE mgmt_task SET db_task=5 WHERE db_name='{}' AND db_task=3".format(tsk[0])
            local_db.execute(sql)
            backup_command = ("pg_dump -d {} | gzip -c > {}/{}_{}".format(
                               tsk[0], BACKUP_DIR, UNAME, tsk[0]))
            proc = await asyncio.create_subprocess_shell(backup_command)
            await proc.wait()
            result = proc.returncode
            logger.debug("{} has been backuped into {} with result {}".format(tsk[0], BACKUP_DIR, result))
            if result == 0:
                sql = 'ALTER DATABASE "{}" ALLOW_CONNECTIONS=false;'.format(tsk[0])
                local_db.execute(sql)
                logger.debug("Connections to {} database have been forbidden".format(tsk[0]))
                sql = ("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{}';".format(tsk[0]))
                local_db.execute(sql)
                logger.debug("Connections to {} have been dropped".format(tsk[0]))
                sql = "DROP DATABASE {};".format(tsk[0])
                local_db.execute(sql)
                logger.debug("{} database has been dropped".format(tsk[0]))
                sql = 'DROP ROLE "{}";'.format(tsk[2])
                local_db.execute(sql)
                logger.debug("{} role has been dropped".format(tsk[2]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(tsk[0], 'delete', QUEUE_NAME)
                remote_db.execute(sql)                
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(tsk[0], result[1]))
                sql = "DELETE FROM mgmt_task WHERE db_name='{}' AND db_task=5".format(tsk[0])
                local_db.execute(sql)
        elif tsk[1] == 4:
            '''
            Recover from a backup
            '''
            logger.debug("Recovery DB: {}".format(tsk[0])) 
            sql = "UPDATE mgmt_task SET db_task=6 WHERE db_name='{}' AND db_task=4".format(tsk[0])
            local_db.execute(sql)
            recovery_command = ("gunzip < {}/{} | psql {}".format(BACKUP_DIR, tsk[3], tsk[0]))
            proc = await asyncio.create_subprocess_shell(recovery_command)
            await proc.wait()
            result = proc.returncode
            logger.debug("{} has been recovered with result {}".format(tsk[0], result))
            if result == 0:
                sql = 'GRANT ALL ON DATABASE "{}" TO "{}"'.format(tsk[0], tsk[2])
                local_db.execute(sql)
                logger.debug("Access to {} database has been granted".format(tsk[0]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(tsk[0], 'create', QUEUE_NAME)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(tsk[0], result[1]))
                sql = "DELETE FROM mgmt_task WHERE db_name='{}' AND db_task=6".format(tsk[0])
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

        systemd.daemon.notify('READY=1')

        while True:
            sql = 'SELECT * FROM mgmt_task WHERE db_task=3 OR db_task=4;'
            local_db.execute(sql)
            tasks = local_db.fetchall()
            if tasks:
                logger.debug("Task: {}".format(tasks))
                coroutines = asyncio.gather(*[proc_entity(task, local_db, remote_db, logger) for task in tasks])
                loop = asyncio.get_event_loop()
                loop.run_until_complete(coroutines)

    except Exception as err:
        logger.critical(str(err))
    finally:
        if os.path.isfile(pid_path) is True:
            os.remove(pid_path)
        if remote_connection:
            remote_db.close()
            remote_connection.close()
        if local_connection:
            local_db.close()
            local_connection.close()
