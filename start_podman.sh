#!/bin/bash

#==============================================================================
# Script Name: start_podman.sh.
# Description: Build and run a podman container. If the container is already
#              running, the running container is stopped and deleted prior.
#      Author: Rafael Müller
#       Email: rafa.molitoris@gmail.com
#  Created on: 17 Feb, 2020
#==============================================================================


IMG_NAME="meta_registration_api"
CONT_NAME="meta_registration_api_cont"
PORT=5001

if [ ! "$(sudo podman ps -q -f name='$CONT_NAME')" ]; then
  echo "Found container with same name"

  if [ ! "$(sudo podman ps -aq -f status=exited -f name='$CONT_NAME')" ]; then
    echo "Container is still running. Stop container \"$CONT_NAME now\""
    sudo podman stop "$CONT_NAME"
  fi

  echo "Remove container $CONT_NAME"
  sudo podman rm "$CONT_NAME"

fi

echo "Build container"
sudo podman build -t "$IMG_NAME" .
echo "Run container"
sudo podman run -d -p "$PORT":8000 --name "$CONT_NAME" "$IMG_NAME"
