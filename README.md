# Labaz

## Description
Python scripts kit for PostgreSQL and MySQL servers in a development environment.

![Scheme][scheme.jpg]

## How it works
`API` is REST API. Available operations:
* creation
* deletion
* backup
* restoring
a database in PostgreSQL or MySQL.

`API` changes data in `pg-mgmt` database and creates a task in the PGQ queue.

`Remote worker` reads the PGQ queue and inserts tasks into the `mgmt` table.

`Local worker` chooses tasks for creation and deletion databases and implements those tasks.

`Local asynchronous worker` chooses tasks for backup and restore and implements those tasks.

`NFS folder` stores SQL dumps. Downloading and uploading SQL dump files goes through the API.

All API features: /api/v1/features
