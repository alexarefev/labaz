from bottle import get, post, delete, request, run, Bottle, response, static_file, FileUpload
import psycopg2
import os
import logging
import re
import multiprocessing as mp
import cysystemd.daemon as sysd

def run_api(port_number):

    app = Bottle()
        
    def input_validation(input_str, valid_lenth):
        first_step = input_str.replace(' ','')[:valid_lenth]
        second_step = re.findall('[^\w,^\-]', first_step)
        if second_step:
            return ''
        else:
            return first_step
    
    def input_validation_bool(input_str):
        first_step = input_str.replace(' ','')
        second_step = first_step.lower()
        if second_step == 'true' or second_step == 'yes':
            return 'true'
        else:
            return 'false'
    
    @app.post('/api/v1/<entity_type>')
    def createdb(entity_type):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    data = request.json
                    logger.debug(f"JSON: {data}")
                    host_name = ''
                    db_name = ''
                    user_name = ''
                    if data:
                        if 'host' in data:
                            host_name = input_validation(data['host'], 250)
                        if 'name' in data:
                            db_name = input_validation(data['name'], 50)
                        if 'user' in data:
                            user_name = input_validation(data['user'], 50)
                    sql = f"SELECT * FROM dbcreation('{db_name}', '{user_name}', '{host_name}', '{entity_type}')"
                    logger.debug(sql)
                    result = run_sql(sql)
                    if result[0] == '0':
                        response.status = 201
                        json_data = { "Result": "success", "type": entity_type, "host": result[1], "name": result[2], "user": result[3], "password": result[4] }
                        logger.info(f"JSON: {json_data}")
                        return json_data
                    else:
                        json_data = { "Result": "fail", "message": result[1] }
                        logger.warning(f"JSON: {json_data}")
                        response.status = 404
                        return json_data                    
                else:
                    pass
        
            json_data = { "Result": "fail", "message": "Error in request" }
            logger.warning(f"JSON: {json_data}")
            response.status = 404
            return json_data
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.route('/api/v1/<entity_type>/<entity>', method='PATCH')
    def recoverdb(entity_type, entity):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    data = request.json
                    logger.debug(f"JSON: {data}")
                    backup_file = ''
                    db_secret = ''
                    db_name = input_validation(entity, 50)
                    if data:
                        if ('file' in data) and ('pass' in data):
                            backup_file = input_validation(data['file'], 50)
                            db_secret = input_validation(data['pass'], 50)
                            is_backup = os.path.exists("{BACKUP_DIR}/{entity_type}/{backup_file}")
                            logger.debug(f"Backup_path: {backup_file}, exists: {is_backup}")
                            if is_backup:
                                sql = "SELECT * FROM dbrecover('{db_name}', '{backup_file}', '{db_secret}', '{entity_type}');"
                                logger.debug(sql)
                                result = run_sql(sql)
                                if result[0] == '0':
                                    response.status = 201
                                    json_data = { "Result": "success", "type": entity_type }
                                    logger.info(f"JSON: {json_data}")
                                    return json_data
                                else:
                                    json_data = { "Result": "fail", "message": result[1] }
                                    logger.warning(f"JSON: {json_data}")
                                    response.status = 404
                                    return json_data                    
                else:
                    pass
        
            json_data = { "Result": "fail", "message": "Error in request" }
            logger.warning(f"JSON: {json_data}")
            response.status = 404
            return json_data
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.delete('/api/v1/<entity_type>')
    def deletedb(entity_type):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    data = request.json
                    db_name = ''
                    db_backup = ''
                    if data:
                        if 'name' in data:
                            db_name = input_validation(data['name'], 50)
                        if 'pass' in data:
                            db_secret = input_validation(data['pass'], 50)
                        if 'backup' in data:
                            db_backup = input_validation_bool(data['backup'])
                        else:
                            db_backup = 'false'
                    if db_name:
                        sql = f"SELECT * FROM dbdeletion('{db_name}', '{db_backup}', '{db_secret}', '{entity_type}');"
                        logger.debug(sql)
                        result = run_sql(sql)
                        if result[0] == '0':
                            response.status = 204
                            json_data = { "Result": "success", "type": entity_type }
                            logger.info(f"JSON: {json_data}")
                            return json_data
                        else:
                            json_data = { "Result": "fail", "message": result[1] }
                            logger.warning(f"JSON: {json_data}")
                            response.status = 404
                            return json_data                    
                else:
                    pass
        
            json_data = { "Result": "fail", "message": "Error in request" }
            logger.warning(f"JSON: {json_data}")
            response.status = 404
            return json_data
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.get('/api/v1/<entity_type>')
    def listdb(entity_type):
        try:
            response.add_header("Allow", "GET, POST, DELETE, PATCH")
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    sql = f"SELECT * FROM dblist('{valid_type}');"
                    logger.debug(sql)
                    result = run_sql(sql)
                    if results:
                        json_data = { "Result": "success", "type": entity_type }
                        logger.info(f"JSON: {json_data}")
                        json_list =[]
                        for result in results:
                            json_str = { "host": result[2], "name": result[0], "user": result[1] }
                            logger.debug(json_str)
                            json_list.append(json_str)
                        json_data.update({"data":json_list})
                        response.status = 200
                        return json_data
    
            response.status = 404
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.get('/api/v1/server/<entity_type>') 
    def listhost(entity_type):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    sql = f"SELECT * FROM hostlist('{valid_type}');"
                    logger.debug(sql)
                    result = run_sql(sql)
                    if results:
                        json_data = { "Result": "success", "type": entity_type }
                        logger.info(f"JSON: {json_data}")
                        json_list =[]
                        for result in results:
                            json_str = { "host": result[0], "active": result[1], "last_ack": str(result[2]) }
                            logger.debug(json_str)
                            json_list.append(json_str)
                        json_data.update({"data":json_list})
                        response.status = 200
                        return json_data
    
            response.status = 404
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.get('/api/v1/backup/<entity_type>/<entity>')
    def downloadbackup(entity_type):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    backup_dir = f"{BACKUP_DIR}/{entity_type}"
                    is_backup = os.path.exists(f"{backup_dir}/{entity}")
                    if is_backup:
                        logger.debug(f"Backup {entity} has been sent")
                        response.status = 200
                        return static_file(entity, root=backup_dir, download=entity)
    
            response.status = 404
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.put('/api/v1/backup/<entity_type>/<entity>')
    def uploadbackup(entity_type, entity):
        try:
            for valid_type in ['pg', 'mysql']:
                if entity_type == valid_type:
                    backup_path = f"{BACKUP_DIR}/{entity_type}/{entity}"
                    is_backup = os.path.exists(backup_path)
                    if not is_backup:
                        backup = FileUpload(request.body, None, filename='')
                        backup.save(backup_path)
                        logger.debug(f"Backup {entity} has been recived")
                        response.status = 200
                        return "" 
    
            response.status = 403
    
        except Exception as err:
            logger.critical(str(err))
    
    @app.get('/api/v1/features')
    def listfeatures():
        try:
            logger.debug("Features list has been sent")
            response.status = 200 
            return static_file('api.html', root='./')
    
        except Exception as err:
            logger.critical(str(err))
    
    def run_sql(sql_query, fetch=None):
            local_db.execute(sql_query)
            if fetch:
                record = loca_db.fetchall()
            else:
                record = local_db.fetchone()[0].split(',')
            return record

    try:
        local_connection = psycopg2.connect(dbname=LOCAL_DB_NAME,
                                            user=LOCAL_DB_USER,
                                            password=LOCAL_DB_PASSWORD,
                                            host='127.0.0.1')
        local_db = local_connection.cursor()
        local_connection.autocommit = True

        logger.info(f"API process on port {port_number}: has been connected to PostgreSQL Management")
        run(app, host='127.0.0.1', port=port_number, quiet=True)
        return 0

    except Exception as err:
        logger.critical(str(err))
        local_db.close()
        local_connection.close()

if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = __file__
    
    LOCAL_DB_NAME = os.environ['LOCAL_DB_NAME']
    LOCAL_DB_USER = os.environ['LOCAL_DB_USER']
    LOCAL_DB_PASSWORD = os.environ['LOCAL_DB_PASSWORD']
    
    BACKUP_DIR = os.environ['BACKUP_DIR']
    API_PORTS = os.environ['API_PORTS']
    CONNECTIONS = len(API_PORTS.lstrip().rstrip().split(' '))
    PORTS_LIST = API_PORTS.lstrip().rstrip().split(' ')
    LOG_LEVEL = os.environ['LOG_LEVEL']
    
    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME)
    
    logger.info(f"MY NAME IS {UNAME}")
    logger.info(f"BACKUP_DIR IS {BACKUP_DIR}")
    
    try:

        sysd.notify(sysd.Notification.READY)

        with mp.Pool(5) as proc:
            proc.map(run_api, PORTS_LIST)
    
    except Exception as err:
        logger.critical(str(err))
