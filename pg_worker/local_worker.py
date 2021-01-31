'''
Locale server interaction
'''
import os
import asyncio

def create_entity(task_property, local_db, logger):
    '''
    Create database and role
    '''
    try:
        sql = 'CREATE DATABASE "{}";'.format(task_property[5])
        local_db.execute(sql)
        logger.debug("{} database has been created".format(task_property[5]))
        sql = ('''CREATE ROLE "{}" WITH LOGIN PASSWORD '{}';'''.format(task_property[6], task_property[7]))
        local_db.execute(sql)
        logger.debug("{} role has been created".format(task_property[6]))
        sql = 'GRANT ALL ON DATABASE "{}" TO "{}"'.format(task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to {} database has been granted".format(task_property[5]))
        return 0
    except Exception as err:
        logger.critical(str(err))

def drop_entity(task_property, local_db, logger):
    '''
    Drop database and role
    '''
    try:
        sql = 'ALTER DATABASE "{}" ALLOW_CONNECTIONS=false;'.format(task_property[5])
        local_db.execute(sql)
        logger.debug("Connections to {} database have been forbidden".format(task_property[5]))
        sql = ("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{}';".format(task_property[5]))
        local_db.execute(sql)
        logger.debug("Connections to {} have been dropped".format(task_property[5]))
        sql = "DROP DATABASE {};".format(task_property[5])
        local_db.execute(sql)
        logger.debug("{} database has been dropped".format(task_property[5]))
        sql = 'DROP ROLE "{}";'.format(task_property[6])
        local_db.execute(sql)
        logger.debug("{} role has been dropped".format(task_property[6]))
        return 0
    except Exception as err:
        logger.critical(str(err))

async def backup_entity(uname, entity_name, backup_dir, logger):
    '''
    Perform a backup
    '''
    try:
        backup_command = ("pg_dump -d {} | gzip -c > {}/{}_{}".format(
                           entity_name, backup_dir, uname, entity_name))
        proc = await asyncio.create_subprocess_shell(backup_command)
        result = proc.returncode
        logger.debug("{} has been backuped into {} with result {}".format(entity_name, backup_dir, result))
        return proc
    except Exception as err:
        logger.critical(str(err))

async def recover_entity(task_property, local_db, backup_dir, logger):
    '''
    Recover from a backup
    '''
    try:
        recovery_command = ("gunzip < {}/{} | psql {}".format(backup_dir, task_property[8], task_property[5]))
        proc = await asyncio.create_subprocess_shell(recovery_command)
        result = proc.returncode
        logger.debug("{} has been recovered with result {}".format(task_property[5], result))
        sql = 'GRANT ALL ON DATABASE "{}" TO "{}"'.format(task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to {} database has been granted".format(task_property[5]))
        return proc
    except Exception as err:
        logger.critical(str(err))
