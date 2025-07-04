FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --upgrade pip && \
    pip install wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create volume for persistent data
VOLUME ["/app/data"]

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TRADING_MODE=live
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT}", "main:app"] 