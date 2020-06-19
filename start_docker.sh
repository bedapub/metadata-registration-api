#!/bin/bash
# =============================================================================
# Script Name: start_docker.sh.
# Description: Build and run a docker container. If the container is already
#              running, the running container is stopped and deleted prior.
#      Author: Rafael Müller
#       Email: rafa.molitoris@gmail.com
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
sudo docker run -d -e DEBUG=false \
-e APP_SECRET=TO_FILL \
-e CHECK_ACCESS_TOKEN=true \
-e PORT=8000 \
-e API_HOST=TO_FILL \
-e API_EP_CTRL_VOC=/ctrl_voc \
-e API_EP_PROPERTY=/properties \
-e API_EP_FORM=/forms \
-e API_EP_STUDY=/studies \
-e API_EP_USER=/users \
-e MONGODB_DB=TO_FILL \
-e MONGODB_HOST=TO_FILL \
-e MONGODB_PORT=TO_FILL \
-e MONGODB_USERNAME=TO_FILL \
-e MONGODB_PASSWORD=TO_FILL \
-e MONGODB_COL_PROPERTY=TO_FILL \
-e MONGODB_COL_CTRL_VOC=TO_FILL \
-e MONGODB_COL_FORM=TO_FILL \
-e MONGODB_COL_USER=TO_FILL \
-e MONGODB_COL_STUDY=TO_FILL \
-p "$PORT":8000 --name "$CONT_NAME" "$IMG_NAME"