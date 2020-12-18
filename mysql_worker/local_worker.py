'''
Locale server interaction
'''
import os

def create_entity(task_property, local_db, logger):
    '''
    Create database and user
    '''
    try:
        sql = "CREATE DATABASE %s;" % task_property[5]
        local_db.execute(sql)
        logger.debug("%s database has been created" % task_property[5])
        sql = ("CREATE USER '%s'@'%%' IDENTIFIED BY '%s';"
               % (task_property[6], task_property[7]))
        local_db.execute(sql)
        logger.debug("%s user has been created" % task_property[6])
        sql = "GRANT ALL ON %s.* TO '%s'@'%%';" % (task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to %s database has been granted" % task_property[5])
        return 0
    except Exception as err:
        logger.critical(str(err))

def drop_entity(task_property, local_db, logger):
    '''
    Drop database and user
    '''
    try:
        sql = "DROP USER '%s'@'%%';" % task_property[6]
        local_db.execute(sql)
        logger.debug("%s user has been dropped" % task_property[6])
        sql = "DROP DATABASE %s;" % task_property[5]
        local_db.execute(sql)
        logger.debug("%s database has been dropped" % task_property[5])
        return 0
    except Exception as err:
        logger.critical(str(err))

def backup_entity(entity_name, entity_user, entity_password, backup_dir, logger):
    '''
    Perform a backup
    '''
    try:
        backup_command = ("mysqldump -u%s -p'%s' %s > %s/%s"
                          % (entity_user, entity_password, entity_name, backup_dir, entity_name))
        logger.debug(backup_command)
        result = os.system(backup_command)
        logger.debug("%s has been backuped into %s with result %s"
                     % (entity_name, backup_dir, result))
        return result
    except Exception as err:
        logger.critical(str(err))
