FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY packages/ ./packages/
COPY apps/ ./apps/

# Install Python dependencies
RUN pip install --no-cache-dir -e packages/core -e packages/tools -e packages/ai -e packages/reporting -e packages/integrations -e packages/common -e apps/api -e apps/worker

# Create non-root user
RUN useradd -m -r -s /bin/bash anomaly
USER anomaly

# Run the arq worker
CMD ["arq", "anomaly_worker.main:WorkerSettings"]
