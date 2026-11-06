FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml packages/core/pyproject.toml packages/tools/pyproject.toml packages/ai/pyproject.toml packages/reporting/pyproject.toml packages/integrations/pyproject.toml packages/common/pyproject.toml apps/api/pyproject.toml ./
RUN pip install --no-cache-dir -e packages/core -e packages/tools -e packages/ai -e packages/reporting -e packages/integrations -e packages/common -e apps/api

# Copy source code
COPY packages/ ./packages/
COPY apps/ ./apps/

# Create non-root user
RUN useradd --create-user --shell /bin/bash anomaly
USER anomaly

# Expose API port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "anomaly_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
