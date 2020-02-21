#!/bin/bash
# =============================================================================
# Script Name: start_docker.sh.
# Description: Build and run a docker container. If the container is already
#              running, the running container is stopped and deleted prior.
#      Author: Rafael Müller
#       Email: rafael.mueller1@gmail.com
#  Created on: 20 Feb, 2020
# =============================================================================

IMG_NAME="api"
CONT_NAME="api_cont"
PORT=5001

if [ ! "$(docker ps -q -f name='$CONT_NAME')" ]; then
  echo "Found container with same name"

  if [ ! "$(docker ps -aq -f status=exited -f name='$CONT_NAME')" ]; then
    echo "Container is still running. Stop container \"$CONT_NAME now\""
    sudo docker stop "$CONT_NAME"
  fi

  echo "Remove container $CONT_NAME"
  sudo docker rm "$CONT_NAME"

fi

echo "Build container"
sudo docker build -t "$IMG_NAME" .
echo "Run container"
sudo docker run -d -p "$PORT":8000 --name "$CONT_NAME" "$IMG_NAME"