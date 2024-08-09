FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configuration to avoid creating virtual environments inside the Docker container
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install 

# Copy the rest of the application code
COPY . .

# Expose the application port
EXPOSE 8002

# for absolute path
ENV PYTHONPATH=/app 
# for showing script logs
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["sh", "-c", "poetry run uvicorn notification_service.main:app --host 0.0.0.0 --reload --port 8000"]
