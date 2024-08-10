#!/bin/bash

# # Check if running in CI environment
# if [ "$CI" == "true" ]; then
#     echo "Running in CI environment"
#     export ENV_FILE=".env.example"
# else
#     # Check if ENVIRONMENT variable is set
#     if [ -z "$ENVIRONMENT" ]; then
#         echo "ENVIRONMENT variable not set. Please set it to 'development' or 'production'."
#         exit 1
#     fi

#     # Set the appropriate ENV_FILE based on ENVIRONMENT
#     if [ "$ENVIRONMENT" == "development" ]; then
#         export ENV_FILE=".env.dev"
#         echo "Using Development Environment"
#     elif [ "$ENVIRONMENT" == "production" ]; then
#         export ENV_FILE=".env.prod"
#         echo "Using Production Environment"
#     else
#         echo "Invalid ENVIRONMENT value. Exiting."
#         exit 1
#     fi
# fi

# # Ensure that the ENV_FILE is not pointing to a directory
# if [ -d "$ENV_FILE" ]; then
#     echo "Error: $ENV_FILE is a directory, but it should be a file."
#     exit 1
# fi
 export ENV_FILE=".env.example"
# Run docker-compose with the selected environment file
docker-compose up -d --build
