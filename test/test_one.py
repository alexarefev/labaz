import psycopg2
import time

def create_db_local(*args):
    sql_exc = "SELECT * FROM dbcreation('%s', '%s', '%s', '%s');" % (args[0], args[1], args[2], args[4])
    print(sql_exc)
    db = args[3]
    db.execute(sql_exc)
    rc = db.fetchone()[0].split(',')
    print (args[0] + " has been created: " + str(rc))
    return rc[4]

def recover_db_local(*args):
    sql_exc = "SELECT * FROM dbrecover('%s', '%s', '%s', '%s');" % (args[0], args[1], args[2], args[4])
    print(sql_exc)
    db = args[3]
    db.execute(sql_exc)
    rc = db.fetchone()
    print (args[0] + " has been recovered: " + str(rc))

def delete_db_local(*args):
    sql_exc = "SELECT * FROM dbdeletion('%s', '%s', '%s', '%s');" % (args[0], args[1], args[2], args[4])
    print(sql_exc)
    db = args[3]
    db.execute(sql_exc)
    rc = db.fetchone()
    print (args[0] + " has been deleted: " + str(rc))

conn = psycopg2.connect("dbname=pgmgmt user=postgres")
conn.autocommit = True
dbc = conn.cursor()
print ("PostgreSQL has been connected!")

try: 
    sql_trn = "TRUNCATE databases RESTART IDENTITY;"
    print(sql_trn)
    dbc.execute(sql_trn)
    trn = dbc.fetchone()
    print("Table database has been truncated: " + str(trn))
except:
    pass

t = 0.5
k = 10
n = 'pg3'
tp = 'pg'
pas = []

for i in range(1, k+1):
    dbn = "db" + str(i)
    user = "user_name" + str(i)
    host = n
    p = create_db_local(dbn, user, host, dbc, tp)
    pas.append(p)
    time.sleep(t)

k2 = 20
fl = 'test_dump.gz'

for i in range(k+1, k2+1):
    dbn = "db" + str(i)
    user = "user_name" + str(i)
    host = n
    create_db_local(dbn, user, host, dbc, tp)
    r = k2 - i
    dbr = "db" + str(r)
    recover_db_local(dbr, fl, pas[r-1], dbc, tp)
    time.sleep(t)

input()
for i in range(1, k+1, 2):
    dbn = "db" + str(i)
    delete_db_local(dbn, 'false', pas[i-1], dbc, tp)
    dbn = "db" + str(i+1)
    delete_db_local(dbn, 'true', pas[i], dbc, tp)
    time.sleep(t)

dbc.close()
conn.close()
