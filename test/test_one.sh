#!/bin/bash

psql -d pgmgmt -U postgres -c "TRUNCATE databases RESTART IDENTITY;"

HS=${2:-pg4}
TP=${1:-pg}

echo "TP=${TP}; HS=${HS}"

i=1
while [ $i -le 10 ]
do
	DB_NAME='db'$i
	USER_NAME='user'$i
	let i++
	echo "DB=${DB_NAME}; USER=${USER_NAME}"
	curl -XPOST -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"host\":\"$HS\", \"name\":\"$DB_NAME\", \"user\":\"$USER_NAME\"}" http://localhost:8080/apiv1/$TP
done

read

let i=1
while [ $i -le 5 ]
do
	DB_NAME='db'$i
	let i++
	echo "DB=${DB_NAME}"
	curl -XDELETE -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"name\":\"$DB_NAME\", \"backup\":\"true\"}" http://localhost:8080/apiv1/pg
done

let i=6
while [ $i -le 10 ]
do
	DB_NAME='db'$i
	let i++
	echo "DB=${DB_NAME}"
	curl -XDELETE -H "Content-Type: application/json" -H "Accept: application/json" -d "{\"name\":\"$DB_NAME\", \"backup\":\"false\"}" http://localhost:8080/apiv1/pg
done
