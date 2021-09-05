'''
Locale server interaction
'''
import os
import asyncio
import logging
import psycopg2
import pymysql
from systemd.daemon import notify, Notification


async def proc_entity(tsk, local_db, remote_db, logger):
    try:
        if tsk[1] == 3:
            '''
            Perform a backup
            '''
            logger.debug("Backup DB: {}".format(tsk[0]))
            sql = "UPDATE mysql.mgmt_task SET db_task=5 WHERE db_name='{}' AND db_task=3".format(tsk[0])
            local_db.execute(sql)
            backup_command = "mysqldump -u{} -p'{}' {} | gzip -c -q > {}/{}_{}".format(
                           entity_user, entity_password, entity_name, backup_dir, uname, entity_name)
            proc = await asyncio.create_subprocess_shell(backup_command)
            await proc.wait()
            result = proc.returncode
            logger.debug("{} has been backuped into {} with result {}".format(tsk[0], BACKUP_DIR, result))
            if result == 0:
                sql = "DROP USER '{}'@'%';".format(tsk[6])
                local_db.execute(sql)
                logger.debug("{} user has been dropped".format(tsk[6]))
                sql = "DROP DATABASE {};".format(tsk[5])
                local_db.execute(sql)
                logger.debug("{} database has been dropped".format(tsk[5]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(tsk[0], 'delete', QUEUE_NAME)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(tsk[0], result[1]))
                sql = "DELETE FROM mysql.mgmt_task WHERE db_name='{}' AND db_task=5".format(tsk[0])
                local_db.execute(sql)
        elif tsk[1] == 4:
            '''
            Recover from a backup
            '''
            logger.debug("Recovery DB: {}".format(tsk[0]))
            sql = "UPDATE mysql.mgmt_task SET db_task=6 WHERE db_name='{}' AND db_task=4".format(tsk[0])
            local_db.execute(sql)
            recovery_command = ("gunzip < {}/{} | psql {}".format(BACKUP_DIR, tsk[3], tsk[0]))
            proc = await asyncio.create_subprocess_shell(recovery_command)
            await proc.wait()
            result = proc.returncode
            logger.debug("{} has been recovered with result {}".format(tsk[0], result))
            if result == 0:
                sql = "GRANT ALL ON {}.* TO '{}'@'%';".format(tsk[5], tsk[6])
                local_db.execute(sql)
                logger.debug("Access to {} database has been granted".format(tsk[5]))
                sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(tsk[0], 'create', QUEUE_NAME)
                remote_db.execute(sql)
                result = remote_db.fetchone()[0].split(',')
                logger.debug("{} {}".format(tsk[0], result[1]))
                sql = "DELETE FROM mysql.mgmt_task WHERE db_name='{}' AND db_task=6".format(tsk[0])
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

        notify(Notification.READY)

        while True:
            sql = 'SELECT * FROM mysql.mgmt_task WHERE db_task=3 OR db_task=4;'
            local_db.execute(sql)
            tasks = local_db.fetchall()
            if tasks:
                logger.debug("Task: {}".format(tasks))
                coroutines = asyncio.gather(*[proc_entity(task, local_db, remote_db, logger) for task in tasks])
                loop = asyncio.get_event_loop()
                loop.run_until_complete(coroutines)

    except Exception as err:
        logger.critical(str(err))
        remote_db.close()
        remote_connection.close()
        local_db.close()
        local_connection.close()

