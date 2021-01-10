'''
Locale server interaction
'''
import os

def create_entity(task_property, local_db, logger):
    '''
    Create database and user
    '''
    try:
        sql = "CREATE DATABASE {};".format(task_property[5])
        local_db.execute(sql)
        logger.debug("{} database has been created".format(task_property[5]))
        sql = "CREATE USER '{}'@'%' IDENTIFIED BY '{}';".format(
               task_property[6], task_property[7])
        local_db.execute(sql)
        logger.debug("{} user has been created".format(task_property[6]))
        sql = "GRANT ALL ON {}.* TO '{}'@'%';".format(task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to {} database has been granted".format(task_property[5]))
        return 0
    except Exception as err:
        logger.critical(str(err))

def drop_entity(task_property, local_db, logger):
    '''
    Drop database and user
    '''
    try:
        sql = "DROP USER '{}'@'%';".format(task_property[6])
        local_db.execute(sql)
        logger.debug("{} user has been dropped".format(task_property[6]))
        sql = "DROP DATABASE {};".format(task_property[5])
        local_db.execute(sql)
        logger.debug("{} database has been dropped".format(task_property[5]))
        return 0
    except Exception as err:
        logger.critical(str(err))

def backup_entity(uname, entity_name, entity_user, entity_password, backup_dir, logger):
    '''
    Perform a backup
    '''
    try:
        backup_command = "mysqldump -u{} -p'{}' {} | gzip -c -q > {}/{}_{}".format(
                           entity_user, entity_password, entity_name, backup_dir, uname, entity_name)
        logger.debug(backup_command)
        result = os.system(backup_command)
        logger.debug("{} has been backuped into {} with result {}".format(entity_name, backup_dir, result))
        return result
    except Exception as err:
        logger.critical(str(err))
        
def recover_entity(task_property, local_db, entity_user, entity_password, backup_dir, logger):
    '''
    Recover from a backup
    '''
    try:
        recovery_command = "gunzip < {}/{} | mysql {} -u{} -p'{}'".format(
                             backup_dir, task_property[8], task_property[5], entity_user, entity_password)
        result = os.system(recovery_command)
        logger.debug("{} has been recovered with result {}".format(task_property[5], result))
        sql = "GRANT ALL ON {}.* TO '{}'@'%';".format(task_property[5], task_property[6])
        local_db.execute(sql)
        logger.debug("Access to {} database has been granted".format(task_property[5]))
        return 0
    except Exception as err:
        logger.critical(str(err))
