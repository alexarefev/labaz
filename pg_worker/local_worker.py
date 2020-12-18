'''
Locale server interaction
'''
import os

def create_entity(task_property, local_db, logger):
    '''
    Create database and role
    '''
    try:
        sql = 'CREATE DATABASE "%s";' % task_property[5]
        local_db.execute(sql)
        logger.debug("%s database has been created" % task_property[5])
        sql = ('''CREATE ROLE "%s" WITH LOGIN PASSWORD '%s';'''
               % (task_property[6], task_property[7]))
        local_db.execute(sql)
        logger.debug("%s role has been created" % task_property[6])
        sql = 'GRANT ALL ON DATABASE "%s" TO "%s"' % (task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to %s database has been granted" % task_property[5])
        return 0
    except Exception as err:
        logger.critical(str(err))

def drop_entity(task_property, local_db, logger):
    '''
    Drop database and role
    '''
    try:
        sql = 'ALTER DATABASE "%s" ALLOW_CONNECTIONS=false;' % task_property[5]
        local_db.execute(sql)
        logger.debug("Connections to %s database have been forbidden"
                     % task_property[5])
        sql = ("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='%s';"
               % task_property[5])
        local_db.execute(sql)
        logger.debug("Connections to %s have been dropped"
                     % task_property[5])
        sql = "DROP DATABASE %s;" % task_property[5]
        local_db.execute(sql)
        logger.debug("%s database has been dropped" % task_property[5])
        sql = 'DROP ROLE "%s";' % task_property[6]
        local_db.execute(sql)
        logger.debug("%s role has been dropped" % task_property[6])
        return 0
    except Exception as err:
        logger.critical(str(err))

def backup_entity(entity_name, backup_dir, logger):
    '''
    Perform a backup
    '''
    try:
        backup_command = ("pg_dump -Z 5 -s -d %s -f %s/%s"
                          % (entity_name, backup_dir, entity_name))
        result = os.system(backup_command)
        logger.debug("%s has been backuped into %s with result %s"
                     % (entity_name, backup_dir, result))
        return result
    except Exception as err:
        logger.critical(str(err))
