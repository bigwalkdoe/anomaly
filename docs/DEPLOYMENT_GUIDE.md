# Anomaly Deployment Guide

This guide covers deploying Anomaly in various environments.

## Prerequisites

- Docker and Docker Compose
- Kubernetes (for Helm deployment)
- Python 3.12+ (for development)

## Deployment Options

### Option 1: Docker Compose (Development/Production)

#### Using docker-compose.yml (Development)

```bash
cd anomaly
docker compose up -d
```

This starts:
- Postgres 16 (port 5432)
- Redis 7 (port 6379)
- MinIO (port 9000)
- Anomaly API (port 8000)
- Anomaly Worker

Access the API at http://localhost:8000/docs

#### Using docker-compose.prod.yml (Production)

```bash
cd anomaly

# Create secrets
echo -n "your-secure-***REMOVED***" > infra/secrets/postgres_password
echo -n "your-secure-minio-password" > infra/secrets/minio_root_password
echo -n "your-secure-jwt-secret" > infra/secrets/jwt_secret

docker compose -f docker-compose.prod.yml up -d
```

Production compose uses Docker secrets and binds to:
- API: port 8000
- Postgres: port 5432
- Redis: port 6379
- MinIO: port 9000

### Option 2: Kubernetes (Helm)

```bash
cd anomaly/deploy/helm/anomaly

# Install
helm install anomaly ./anomaly

# With custom values
helm install anomaly ./anomaly -f my-values.yaml
```

#### Helm Values

Key configuration values in `values.yaml`:

```yaml
replicaCount: 2

image:
  repository: anomaly/api
  tag: "0.1.0"

env:
  DATABASE_URL: "postgresql+asyncpg://anomaly:anomaly@postgres:5432/anomaly"
  REDIS_URL: "redis://redis:6379/0"
  JWT_SECRET: "***REMOVED***"
  MINIO_ENDPOINT: "minio:9000"
  MINIO_ACCESS_KEY: "minioadmin"
  MINIO_SECRET_KEY: "minioadmin"
  MINIO_BUCKET: "anomaly-evidence"

ingress:
  enabled: true
  hosts:
    - host: anomaly.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: anomaly-tls
      hosts:
        - anomaly.example.com
```

### Option 3: Manual Installation

```bash
# Install dependencies
pip install -e packages/core -e packages/tools -e packages/ai -e packages/reporting -e packages/integrations -e packages/common -e apps/api -e apps/worker

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:5432/anomaly"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="***REMOVED***"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export MINIO_BUCKET="anomaly-evidence"

# Run database migrations
cd packages/core
alembic upgrade head

# Start API
cd ../apps/api
uvicorn anomaly_api.main:app --host 0.0.0.0 --port 8000

# Start worker
cd ../apps/worker
arq anomaly_worker.main:WorkerSettings
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | - |
| REDIS_URL | Redis connection string | - |
| JWT_SECRET | Secret for JWT signing | - |
| JWT_ACCESS_TTL_MIN | Access token TTL in minutes | 15 |
| JWT_REFRESH_TTL_DAYS | Refresh token TTL in days | 7 |
| MINIO_ENDPOINT | MinIO host:port | localhost:9000 |
| MINIO_ACCESS_KEY | MinIO access key | minioadmin |
| MINIO_SECRET_KEY | MinIO secret key | minioadmin |
| MINIO_BUCKET | Evidence bucket name | anomaly-evidence |
| RUNNER_IMAGE | Container runner image | anomaly-runner:dev |
| RUNNER_NETWORK | Docker network name | anomaly-net |

## Security Considerations

1. **Change all default passwords/secrets** in production
2. **Use HTTPS** in production (configure TLS termination at ingress/load balancer)
3. **Restrict CORS** origins to trusted domains
4. **Enable rate limiting** (configured at 100 requests/minute per IP)
5. **Use strong JWT secrets** (minimum 256 bits)
6. **Regularly rotate API keys and secrets**
7. **Enable MFA** for all administrative accounts

## Backup and Recovery

### Database Backup

```bash
docker exec anomaly-postgres-1 pg_dumpall -U anomaly > backup.sql
docker exec -i anomaly-postgres-1 psql -U anomaly < backup.sql
```

### MinIO Backup

```bash
docker cp anomaly-minio-1:/data ./minio-backup
```

## Monitoring

- API health: `GET /api/health`
- API version: `GET /api/version`
- Prometheus metrics: `GET /api/metrics`
- Docker healthchecks are configured for all services

## Troubleshooting

### Services won't start

1. Check Docker logs: `docker compose logs`
2. Verify environment variables are set correctly
3. Ensure ports are not already in use

### Database connection fails

1. Verify Postgres is running: `docker compose ps postgres`
2. Check DATABASE_URL format
3. Wait for Postgres healthcheck to pass

### API returns 500 errors

1. Check API logs: `docker compose logs anomaly-api`
2. Verify database migrations are applied: `alembic upgrade head`
3. Check Redis connectivity
