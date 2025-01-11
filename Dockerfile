# Update Python version
FROM python:3.12-slim

WORKDIR /app

# Set PYTHONPATH to include both /app and /app/src
ENV PYTHONPATH=/app:/app/src

# Install system dependencies including PortAudio and curl
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable to skip AWS SDK version check
ENV IGNORE_AWS_VERSION=1

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install requirements with pip upgrade and additional flags
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p logs data/sample_user_profiles

# Copy the entrypoint script first and set permissions
COPY docker-entrypoint.sh .
RUN chmod +x ./docker-entrypoint.sh

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]