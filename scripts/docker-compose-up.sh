#!/bin/bash

echo "Select the environment:"
echo "1) Development"
echo "2) Production"

read -p "Enter your choice (1 or 2): " env_choice

if [ "$env_choice" == "1" ]; then
    export ENV_FILE=.env.dev
    echo "Using Development Environment"
elif [ "$env_choice" == "2" ]; then
    export ENV_FILE=.env.prod
    echo "Using Production Environment"
else
    echo "Invalid choice. Exiting."
    exit 1
fi

docker-compose up -d --build
