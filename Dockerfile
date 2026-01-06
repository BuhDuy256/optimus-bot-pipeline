# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY src/ ./src/

# Create necessary directories
RUN mkdir -p /app/data/markdown /app/data/raw

# Initialize hash_store.json if it doesn't exist
RUN echo '{"articles": {}, "last_fetching_time": 0}' > /app/data/hash_store.json

# Run the application
CMD ["python", "main.py"]
