#!/bin/bash

DOCKER_HUB_USERNAME="hamzahrpc"
DOCKER_HUB_PASSWORD="hamzah1435"

# Build the Docker images using docker-compose
docker-compose build
if [ $? -ne 0 ]; then
    echo "Docker build failed."
    exit 1
fi

# Tag the images
docker tag my_mart-inventory-service:latest $DOCKER_HUB_USERNAME/inventory-service:latest
docker tag my_mart-user-service:latest $DOCKER_HUB_USERNAME/user-service:latest
docker tag my_mart-notification-service:latest $DOCKER_HUB_USERNAME/notification-service:latest
if [ $? -ne 0 ]; then
    echo "Docker tag failed."
    exit 1
fi

# Log in to Docker Hub
echo $DOCKER_HUB_PASSWORD | docker login --username $DOCKER_HUB_USERNAME --password-stdin
if [ $? -ne 0 ]; then
    echo "Docker login failed."
    exit 1
fi

# Push the images to Docker Hub
docker push $DOCKER_HUB_USERNAME/inventory-service:latest
if [ $? -ne 0 ]; then
    echo "Failed to push inventory-service image."
    exit 1
fi

docker push $DOCKER_HUB_USERNAME/user-service:latest
if [ $? -ne 0 ]; then
    echo "Failed to push user-service image."
    exit 1
fi

docker push $DOCKER_HUB_USERNAME/notification-service:latest
if [ $? -ne 0 ]; then
    echo "Failed to push notification-service image."
    exit 1
fi

echo "Docker images built, tagged, and pushed successfully."
