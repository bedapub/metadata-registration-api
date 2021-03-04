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

if [ ! "$(podman ps -q -f name='$CONT_NAME')" ]; then
  echo "Found container with same name"

  if [ ! "$(podman ps -aq -f status=exited -f name='$CONT_NAME')" ]; then
    echo "Container is still running. Stop container \"$CONT_NAME now\""
    podman stop "$CONT_NAME"
  fi

  echo "Remove container $CONT_NAME"
  podman rm "$CONT_NAME"

fi

if [ "$(podman images -q $IMG_NAME)" ]; then
  echo "Found image with same name"
  echo "Remove image $IMG_NAME"
  podman rmi "$IMG_NAME"
fi

echo "Build container"
podman build -t "$IMG_NAME" .
echo "Run container"
podman run -d -e DEBUG=false \
-e APP_SECRET=uktvlyih84KHNI54jbL64 \
-e CHECK_ACCESS_TOKEN=true \
-e PORT=8000 \
-e API_HOST=127.0.0.1 \
-e API_EP_CTRL_VOC=/ctrl_voc \
-e API_EP_PROPERTY=/properties \
-e API_EP_FORM=/forms \
-e API_EP_STUDY=/studies \
-e API_EP_USER=/users \
-e MONGODB_DB=metadata_api_dev \
-e MONGODB_HOST=192.168.2.52 \
-e MONGODB_PORT=27017 \
-e MONGODB_USERNAME="" \
-e MONGODB_PASSWORD="" \
-e MONGODB_COL_PROPERTY=metadata_api_properties \
-e MONGODB_COL_CTRL_VOC=metadata_api_ctrl_voc \
-e MONGODB_COL_FORM=metadata_api_form \
-e MONGODB_COL_USER=metadata_api_user \
-e MONGODB_COL_STUDY=metadata_api_study \
-p "$PORT":8000 --name "$CONT_NAME" "$IMG_NAME"
