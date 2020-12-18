import psycopg2
import time

def create_db_local(*args):
    sql_exc = "SELECT * FROM dbcreation('%s', '%s', '%s', '%s');" % (args[0], args[1], args[2], args[4])
    print(sql_exc)
    db = args[3]
    db.execute(sql_exc)
    rc = db.fetchone()
    conn.commit()
    print (args[0] + " has been created: " + str(rc))

def delete_db_local(*args):
    sql_exc = "SELECT * FROM dbdeletion('%s', '%s');" % (args[0], args[1])
    print(sql_exc)
    db = args[2]
    db.execute(sql_exc)
    rc = db.fetchone()
    conn.commit()
    print (args[0] + " has been deleted: " + str(rc))

conn = psycopg2.connect("dbname=pgmgmt user=postgres")
dbc = conn.cursor()

print ("PostgreSQL has been connected!")

try: 
    sql_trn = "TRUNCATE databases RESTART IDENTITY;"
    print(sql_trn)
    dbc.execute(sql_trn)
    trn = dbc.fetchone()
    conn.commit()
    print("Table database has been truncated: " + str(trn))
except:
    pass

t = 0.5
k = 10
n = 'db1'
tp = 'mysql'

for i in range(1, k+1):
    dbn = "db" + str(i)
    user = "user_name" + str(i)
    host = n
    print("create_db_local(%s, %s, %s, dbc)" % (dbn, user, host))
    create_db_local(dbn, user, host, dbc, tp)
    #input()
    time.sleep(t)

input()
for i in range(1, k+1, 2):
    dbn = "db" + str(i)
    print("delete_db_local(%s, false, dbc)" % dbn) 
    delete_db_local(dbn, 'false', dbc)
    dbn = "db" + str(i+1)
    print("delete_db_local(%s, 'true', dbc)" % dbn) 
    delete_db_local(dbn, 'true', dbc)
    time.sleep(t)
    #input()

dbc.close()
conn.close()
