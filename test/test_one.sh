#!/bin/bash

psql -d pgmgmt -U postgres -c "TRUNCATE databases RESTART IDENTITY;"

HS=${2:-pg4}
TP=${1:-pg}
RESP=./response


echo "TP=${TP}; HS=${HS}"

i=1
while [ $i -le 10 ]
do
	DB_NAME='db'$i
	USER_NAME='user_'$i
	let i++
#	echo "DB=${DB_NAME}; USER=${USER_NAME}"
	curl -XPOST -H "Authorization: Basic bGFiYXo6cnR5ZGZnNDU2" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"host\":\"$HS\", \"name\":\"$DB_NAME\", \"user\":\"$USER_NAME\"}" http://localhost:8080/apiv1/$TP >> $RESP
done

read

let i=1
while [ $i -le 5 ]
do
	DB_NAME='db'$i
	PASS=$(grep $DB_NAME $RESP | sed 's/.\+"password":\ "\(.\+\)"}/\1/')
	let i++
#	echo "DB=${DB_NAME}"
	curl -XDELETE -H "Authorization: Basic bGFiYXo6cnR5ZGZnNDU2" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"name\":\"$DB_NAME\", \"backup\":\"true\", \"pass\":\"$PASS\"}" http://localhost:8080/apiv1/$TP
done

let i=6
while [ $i -le 10 ]
do
	DB_NAME='db'$i
	PASS=$(grep $DB_NAME $RESP | sed 's/.\+"password":\ "\(.\+\)"}/\1/')
	let i++
#	echo "DB=${DB_NAME}"
	curl -XDELETE -H "Authorization: Basic bGFiYXo6cnR5ZGZnNDU2" -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"name\":\"$DB_NAME\", \"backup\":\"false\", \"pass\":\"$PASS\"}" http://localhost:8080/apiv1/$TP
done


curl -v -XPUT -H "Authorization: Basic bGFiYXo6cnR5ZGZnNDU2" -d @test_dump_pg http://localhost:8080/apiv1/backup/pg/pg1

