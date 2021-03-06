from bottle import get, post, delete, request, run, Bottle, response, static_file, FileUpload
import psycopg2
import os
import logging
import re

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
                logger.debug("JSON: {}".format(data))
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
                sql = "SELECT * FROM dbcreation('{}', '{}', '{}', '{}');".format(db_name, user_name, host_name, entity_type)
                logger.debug(sql)
                local_db.execute(sql)
                result = local_db.fetchone()[0].split(',')
                if result[0] == '0':
                    response.status = 201
                    json_data = { "Result": "success", "type": entity_type, "host": result[1], "name": result[2], "user": result[3], "password": result[4] }
                    logger.info("JSON: {}".format(json_data))
                    return json_data
                else:
                    json_data = { "Result": "fail", "message": result[1] }
                    logger.warning("JSON: {}".format(json_data))
                    response.status = 404
                    return json_data                    
            else:
                pass
    
        json_data = { "Result": "fail", "message": "Error in request" }
        logger.warning("JSON: {}".format(json_data))
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
                logger.debug("JSON: {}".format(data))
                backup_file = ''
                db_secret = ''
                db_name = input_validation(entity, 50)
                if data:
                    if ('file' in data) and ('pass' in data):
                        backup_file = input_validation(data['file'], 50)
                        db_secret = input_validation(data['pass'], 50)
                        is_backup = os.path.exists("{}/{}/{}".format(BACKUP_DIR, entity_type, backup_file))
                        logger.debug("Backup_path: {}, exists: {}".format(backup_file, is_backup))
                        if is_backup:
                            sql = "SELECT * FROM dbrecover('{}', '{}', '{}', '{}');".format(db_name, backup_file, db_secret, entity_type)
                            logger.debug(sql)
                            local_db.execute(sql)
                            result = local_db.fetchone()[0].split(',')
                            if result[0] == '0':
                                response.status = 201
                                json_data = { "Result": "success", "type": entity_type }
                                logger.info("JSON: {}".format(json_data))
                                return json_data
                            else:
                                json_data = { "Result": "fail", "message": result[1] }
                                logger.warning("JSON: {}".format(json_data))
                                response.status = 404
                                return json_data                    
            else:
                pass
    
        json_data = { "Result": "fail", "message": "Error in request" }
        logger.warning("JSON: {}".format(json_data))
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
                    sql = "SELECT * FROM dbdeletion('{}', '{}', '{}', '{}');".format(db_name, db_backup, db_secret, entity_type)
                    logger.debug(sql)
                    local_db.execute(sql)
                    result = local_db.fetchone()[0].split(',')
                    if result[0] == '0':
                        response.status = 204
                        json_data = { "Result": "success", "type": entity_type }
                        logger.info("JSON: {}".format(json_data))
                        return json_data
                    else:
                        json_data = { "Result": "fail", "message": result[1] }
                        logger.warning("JSON: {}".format(json_data))
                        response.status = 404
                        return json_data                    
            else:
                pass
    
        json_data = { "Result": "fail", "message": "Error in request" }
        logger.warning("JSON: {}".format(json_data))
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
                sql = "SELECT * FROM dblist('{}');".format(valid_type)
                logger.debug(sql)
                local_db.execute(sql)
                results = local_db.fetchall()
                if results:
                    json_data = { "Result": "success", "type": entity_type }
                    logger.info("JSON: {}".format(json_data))
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
                sql = "SELECT * FROM hostlist('{}');".format(valid_type)
                logger.debug(sql)
                local_db.execute(sql)
                results = local_db.fetchall()
                if results:
                    json_data = { "Result": "success", "type": entity_type }
                    logger.info("JSON: {}".format(json_data))
                    json_list =[]
                    for result in results:
                        json_str = { "host": result[0], "active": result[1] }
                        logger.debug(json_str)
                        json_list.append(json_str)
                    json_data.update({"data":json_list})
                    response.status = 200
                    return json_data

        response.status = 404

    except Exception as err:
        logger.critical(str(err))

@app.get('/api/v1/backup/<entity_type>/<entity>')
def downloadbackup(entity_type, entity):
    try:
        for valid_type in ['pg', 'mysql']:
            if entity_type == valid_type:
                backup_dir = "{}/{}".format(BACKUP_DIR, entity_type)
                is_backup = os.path.exists("{}/{}".format(backup_dir, entity))
                if is_backup:
                    logger.debug("Backup {} has been sent".format(entity))
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
                backup_path = "{}/{}/{}".format(BACKUP_DIR, entity_type, entity)
                is_backup = os.path.exists(backup_path)
                if not is_backup:
                    backup = FileUpload(request.body, None, filename='')
                    backup.save(backup_path)
                    logger.debug("Backup {} has been recived".format(entity))
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

if __name__ == "__main__":

    UNAME = os.uname()[1]
    WORKER_NAME = __file__
    
    LOCAL_DB_NAME = os.environ['LOCAL_DB_NAME']
    LOCAL_DB_USER = os.environ['LOCAL_DB_USER']
    LOCAL_DB_PASSWORD = os.environ['LOCAL_DB_PASSWORD']
    
    BACKUP_DIR = os.environ['BACKUP_DIR']
    API_PORT = os.environ['API_PORT']
    LOG_LEVEL = os.environ['LOG_LEVEL']
    
    LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(lineno)s %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOGGER_FORMAT)
    logger = logging.getLogger(WORKER_NAME + API_PORT)
    
    logger.info("MY NAME IS {}".format(UNAME))
    logger.info("BACKUP_DIR IS {}".format(BACKUP_DIR))
    
    try:
        local_connection = psycopg2.connect(dbname=LOCAL_DB_NAME,
                                            user=LOCAL_DB_USER,
                                            password=LOCAL_DB_PASSWORD,
                                            host='127.0.0.1')
        local_db = local_connection.cursor()
        local_connection.autocommit = True
        logger.info("PostgreSQL Management has been connected")

        run(app, host='127.0.0.1', port=API_PORT)
    
    except Exception as err:
        logger.critical(str(err))
        local_db.close()
        local_connection.close()
