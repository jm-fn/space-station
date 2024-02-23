# SPACE STATION

A showcase of fastAPI server working with RabbitMQ queue. The server stores a
database of cosmonauts represented by rows of names and optional ages and uses
RabbitMQ queue to ingest larger numbers of cosmonauts.

## Installation

### Local
The server can be run locally with podman-compose:
```
cd space_station
podman-compose build && docker-compose up -d
```
The docker-compose has been tested with `podman-compose` but it should work with docker-compose as well.


## Usage
To manipulate cosmonauts manually run curl:
```
# add cosmonaut
curl -H "Content-Type: application/json" --data '{"name": "Karel"}' ${server_host}:${server_port}/kosmonauts/
# query cosmonaut details by his ID
curl ${server_host}:${server_port}/kosmonauts/${ID}
# update cosmonaut's age by ID
curl --request POST ${server_host}:${server_port}/kosmonauts/${ID}/${age}
# delete kosmonaut by ID
curl --request POST ${server_host}:${server_port}/kosmonauts/delete/${ID}
```
where `server_host` is the address of the space_station server (e.g. localhost) and `server_port` is the port exposed by space_station (e.g. 8000).

The content of the post should conform to the json schema listed in [this section](#json-schema).
