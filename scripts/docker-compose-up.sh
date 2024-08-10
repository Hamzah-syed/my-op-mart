#!/bin/bash

# Check if ENVIRONMENT variable is set
if [ -z "$ENVIRONMENT" ]; then
    echo "ENVIRONMENT variable not set. Please set it to 'development' or 'production'."
    exit 1
fi

# Set the appropriate ENV_FILE based on ENVIRONMENT
if [ "$ENVIRONMENT" == "development" ]; then
    export ENV_FILE=.env.dev
    echo "Using Development Environment"
elif [ "$ENVIRONMENT" == "production" ]; then
    export ENV_FILE=.env.prod
    echo "Using Production Environment"
else
    echo "Invalid ENVIRONMENT value. Exiting."
    exit 1
fi

# Run docker-compose with the selected environment file
docker-compose up -d --build
