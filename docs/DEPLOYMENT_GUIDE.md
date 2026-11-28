# Anomaly Deployment Guide

This guide covers deploying Anomaly in various environments.

Before deploying beyond local development, complete the [Production Readiness Checklist](PRODUCTION_READINESS.md) and record evidence for every gate.

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
- Postgres 16 (host port 20102)
- Redis 7 (host port 20103)
- MinIO (host ports 20104/20105)
- Anomaly API (host port 20101)
- Anomaly Worker

Access the API at http://localhost:20101/docs

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
- API: host port 20101
- Postgres: internal only (no host publish)
- Redis: internal only (no host publish)
- MinIO: internal only (no host publish)

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

# Set environment variables (host-access examples for local dev)
export DATABASE_URL="postgresql+asyncpg://anomaly:anomaly@localhost:20102/anomaly"
export REDIS_URL="redis://localhost:20103/0"
export JWT_SECRET="***REMOVED***"
export MINIO_ENDPOINT="localhost:20104"
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

## Security Hardening (Deployment)

### Reverse Proxy / Ingress

When running behind a reverse proxy (nginx, Traefik, Cloudflare, etc.):

- **Forward security headers**: Ensure the proxy does not strip or override the API's
  security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Content-Security-Policy`). Verify with `curl -I` against the proxied endpoint.
- **CORS origins**: Set `ANOMALY_CORS_ORIGINS` (or `CORS_ALLOW_ORIGINS`) to specific
  trusted domains in production. Never use `*` with credentials enabled.
- **Rate limiting**: The API includes `RateLimitMiddleware` (default 100 req/60s per IP).
  Consider additional proxy-level rate limiting for DDoS protection.
- **TLS termination**: Terminate TLS at the proxy/load balancer. The API itself does not
  handle TLS. Enable HSTS at the proxy level (`Strict-Transport-Security`).

### Token-in-Query Log Redaction (WebSocket)

WebSocket endpoints accept tokens via query parameter (`?token=...`) for browser
compatibility, and optionally via `Authorization: Bearer` header. To prevent token
leakage in proxy/access logs:

- **nginx**: Use a custom log format that redacts query parameters:
  ```nginx
  log_format redacted '$remote_addr - $remote_user [$time_local] '
                      '"$request_method $uri $server_protocol" $status $body_bytes_sent';
  ```
  Note: `$uri` excludes query string; `$request_uri` includes it.
- **Traefik**: Configure access logs to omit query strings or use a custom format.
- **Cloudflare**: Access logs are managed by Cloudflare; tokens in query params may
  appear in Cloudflare analytics. Prefer `Authorization` header when possible.
- **Application-level**: The API does not log request URLs or query strings. Uvicorn
  access logs include the full request path including query string by default — disable
  or customize Uvicorn's `--access-log` format in production.

### Metrics Endpoint Protection

Set `ANOMALY_METRICS_AUTH_REQUIRED=true` to require an authenticated admin user
for `/api/metrics`. Default is `false` for backward compatibility.

### Upload Limits

Configure `MAX_UPLOAD_SIZE_BYTES` (default 50 MB) to control maximum file upload size.
