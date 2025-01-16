#!/bin/bash

set -e

rest=$@

IMAGE=chromakey_service_izhan:latest

CONTAINER_ID=$(docker inspect --format="{{.Id}}" ${IMAGE} 2> /dev/null)
if [[ "${CONTAINER_ID}" ]]; then
    docker run --shm-size=4g --gpus all --rm \
      -p 9022:9022 \
      -v `pwd`:/scratch \
      --user $(id -u):$(id -g) --workdir=/scratch -e HOME=/scratch $IMAGE $@
else
    echo "Unknown container image: ${IMAGE}"
    exit 1
fi