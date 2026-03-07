FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    fonts-dejavu \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory and make wait script executable
RUN mkdir -p /app/logs && chmod +x /app/wait-for-db.sh

EXPOSE 8080

# Wait for DB to be ready before starting app
CMD ["/bin/sh", "-c", "/app/wait-for-db.sh && python app.py"]
