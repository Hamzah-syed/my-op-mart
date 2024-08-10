#!/bin/bash

# Handle the .env.common file
if [ ! -f ".env.common" ]; then
    if [ "$CI" == "true" ]; then
        echo "Creating temporary .env.common file for CI environment"
        cat <<EOT >> .env.common
# Temporary .env.common for CI
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
EOT
    else
        echo ".env.common file not found! Please create it in the project root."
        exit 1
    fi
fi

# Check if running in CI environment
if [ "$CI" == "true" ]; then
    echo "Running in CI environment"
    export ENV_FILE=.env.example
else
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
fi

# Run docker-compose with the selected environment file
docker-compose up -d --build

# Clean up temporary .env.common if created
if [ "$CI" == "true" ] && [ -f ".env.common" ]; then
    echo "Cleaning up temporary .env.common file"
    rm .env.common
fi
