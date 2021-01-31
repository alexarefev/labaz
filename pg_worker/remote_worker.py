'''
Management server interaction
'''

def worker_registration(remote_db, logger, *args):
    '''
    Register the worker as a consumer in the particular queue
    '''
    try:
        consumer_name = "{}_{}".format(args[1], args[2])
        sql = "SELECT * FROM pgq.register_consumer('{}', '{}');".format(args[0], consumer_name)
        logger.debug("Customer registration string: {}".format(sql))
        remote_db.execute(sql)
        result = remote_db.fetchone()
        logger.debug("{} consumer has been registred with code: {}".format(args[1], result))
    except Exception as err:
        logger.critical(str(err))

def queue_reading(remote_db, logger, *args):
    '''
    Get batch of messages from the queue
    '''
    result_list = []
    try:
        consumer_name = "{}_{}".format(args[1], args[2])
        while len(result_list) == 0:
            sql = "SELECT * FROM pgq.next_batch('{}', '{}');".format(args[0], consumer_name)
            remote_db.execute(sql)
            result = remote_db.fetchall()
            batch_set = result[0]
            if batch_set[0] is not None:
                sql = "SELECT * FROM pgq.get_batch_events({});".format(batch_set[0])
                remote_db.execute(sql)
                batch = remote_db.fetchall()
                for i in range(0, len(batch)):
                    logger.debug("server: {}, database: {}, user: {}, action: {}, backup: {}".format(
                                  batch[i][8], batch[i][5], batch[i][6], batch[i][4],
                                  batch[i][7]))
                sql = "SELECT * FROM pgq.finish_batch({});".format(batch_set[0])
                remote_db.execute(sql)
                result = remote_db.fetchall()
            else:
                batch = 0
            return batch
    except Exception as err:
        logger.critical(str(err))

async def db_acknowledge(remote_db, entity_name, ack_type, db_type, logger):
    '''
    Set database status or delete record with particular database from databases list
    '''
    try:
        sql = "SELECT * FROM public.dback('{}', '{}', '{}');".format(entity_name, ack_type, db_type)
        remote_db.execute(sql)
        result = remote_db.fetchone()[0].split(',')
        logger.debug("{} {}".format(entity_name, result[1]))
        return 0
    except Exception as err:
        logger.critical(str(err))
