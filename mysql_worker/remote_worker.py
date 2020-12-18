'''
Management server interaction
'''

def worker_registration(remote_db, logger, *args):
    '''
    Register the worker as a consumer in the particular queue
    '''
    try:
        consumer_name = "%s_%s" % (args[1], args[2])
        sql = "SELECT * FROM pgq.register_consumer('%s', '%s');" % (args[0], consumer_name)
        logger.debug("Customer registration string: %s" % sql)
        remote_db.execute(sql)
        result = remote_db.fetchone()
        logger.debug("%s consumer has been registred with code: %s" % (args[1], result))
    except Exception as err:
        logger.critical(str(err))

def queue_reading(remote_db, logger, *args):
    '''
    Get batch of messages from the queue
    '''
    result_list = []
    try:
        consumer_name = "%s_%s" % (args[1], args[2])
        while len(result_list) == 0:
            sql = "SELECT * FROM pgq.next_batch('%s', '%s');" % (args[0], consumer_name)
            remote_db.execute(sql)
            result = remote_db.fetchall()
            batch_set = result[0]
            if batch_set[0] is not None:
                sql = "SELECT * FROM pgq.get_batch_events(%s);" % str(batch_set[0])
                remote_db.execute(sql)
                batch = remote_db.fetchall()
                for i in range(0, len(batch)):
                    logger.debug("server: %s, database: %s, user: %s, action: %s, backup: %s"
                                 % (batch[i][8], batch[i][5], batch[i][6], batch[i][4],
                                    batch[i][7]))
                sql = "SELECT * FROM pgq.finish_batch(%s);" % str(batch_set[0])
                remote_db.execute(sql)
                result = remote_db.fetchall()
            else:
                batch = 0
            return batch
    except Exception as err:
        logger.critical(str(err))

def creation_acknowledge(remote_db, entity_name, logger):
    '''
    Set database status
    '''
    try:
        sql = "UPDATE databases SET db_state=1 WHERE db_name='%s';" % entity_name
        remote_db.execute(sql)
        logger.debug("%s status has been updated in management database"
                     % entity_name)
        return 0
    except Exception as err:
        logger.critical(str(err))

def deletion_acknowledge(remote_db, entity_name, logger):
    '''
    Delete record with particular database from databases list
    '''
    try:
        sql = "DELETE FROM databases WHERE db_name='%s';" % entity_name
        remote_db.execute(sql)
        logger.debug("%s has been deleted from management database"
                     % entity_name)
        return 0
    except Exception as err:
        logger.critical(str(err))
