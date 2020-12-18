import psycopg2
import random
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

k = 60
n = 6

for i in range(1, k+1):
    dbn = "db" + str(i)
    user = "user_name" + str(i)
    j = random.randint(1,n)
    host = "pg" + str(j)
    s = "create_db_local(" + dbn + ", " + user + ", " + host + ", dbc )"
    print(s)
    create_db_local(dbn, user, host, dbc, 'pg')
    time.sleep(1)

for i in range(1, k+1):
    dbn = "db" + str(i)
    b = 'true'
    z = "delete_db_local(" + dbn + ", " + b + ", ''" + ", dbc)" 
    print(z)
    delete_db_local(dbn, b, '', dbc)
    time.sleep(1)

dbc.close()
conn.close()
