# Security Hardening Guide

## Overview

This document outlines security hardening practices for the Anomaly platform.

## Authentication & Authorization

### JWT Configuration

- Use strong, randomly generated JWT secrets (minimum 256 bits)
- Set short access token TTL (15 minutes default)
- Set refresh token TTL (7 days default)
- Implement refresh token rotation (used tokens are revoked)
- Store refresh tokens hashed in the database

### API Keys

- API keys are prefixed with `anomaly_` and use URL-safe tokens
- Keys are hashed (bcrypt) before storage
- Keys can be revoked at any time
- Each key has scoped permissions

### Password Policy

- Minimum 12 characters recommended
- bcrypt hashing with appropriate cost factor
- Account lockout after repeated failed attempts

## Network Security

### CORS

- Configure `allow_origins` to specific trusted domains in production
- Avoid `*` in production deployments

### Rate Limiting

- RateLimitMiddleware limits requests per client IP
- Default: 100 requests per 60 seconds per client
- Adjust based on deployment requirements

### Headers

- X-Request-ID header added to all responses for tracing
- Security headers added to API responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy` (docs-safe policy for `/docs`/`/redoc`, restrictive `default-src 'none'` elsewhere)
- Consider adding additional deployment-specific hardening as needed

## Container Security

### Runner Containers

- Run as non-root user
- Read-only root filesystem where possible
- No privileged mode
- No host network access
- Resource limits (CPU, memory, timeout) per run
- Writable scratch volume only for tool output

### API/Worker Containers

- Run as non-root user (`anomaly`)
- Minimal base image (python:3.12-slim)
- No unnecessary packages installed

## Secrets Management

### Docker Secrets

- Use Docker secrets for production deployments
- Secrets mounted as files in `/run/secrets/`
- Never commit secrets to version control

### Environment Variables

- `JWT_SECRET` - Must be strong and unique per deployment
- `DATABASE_URL` - Include strong password
- `MINIO_SECRET_KEY` - Strong secret key
- `REDIS_PASSWORD` - Strong Redis password

## Scope Enforcement

- All tool runs are checked against engagement scope before execution
- Out-of-scope targets generate warnings (warn-and-log policy)
- Scope warnings are recorded in the audit log
- Cross-engagement access returns 404 (not 403) to prevent enumeration

## Audit Logging

- All state-changing actions are recorded
- Audit log is append-only and immutable
- Every AI call is logged with model, token counts, and resulting action
- Scope warnings are logged with full context (target, user, engagement)

## Dependency Security

- Regular `safety check` scans for vulnerable dependencies
- `bandit` SAST scan for code vulnerabilities
- `gitleaks` for secret detection in git history
- Keep dependencies updated

## Production Checklist

The canonical release gate is the [Production Readiness Checklist](docs/PRODUCTION_READINESS.md). It records evidence for each gate; use it for release approval. The summary below highlights security controls that most often drift. Link every completed item to evidence in the canonical checklist; do not mark a gate complete from this summary alone.

- [ ] Set `ANOMALY_METRICS_AUTH_REQUIRED=true` and verify `/api/metrics` rejects anonymous access
- [ ] Set `MAX_UPLOAD_SIZE_BYTES` to the approved limit and verify oversized uploads are rejected
- [ ] Prefer `Authorization: Bearer` for WebSocket clients; the token param remains available for browser clients
- [ ] Change all default passwords/secrets
- [ ] Configure strong JWT secret
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS with specific origins
- [ ] Set up rate limiting appropriate for your traffic
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up monitoring and alerting
- [ ] Review and test scope enforcement
- [ ] Review audit log retention policy
- [ ] Conduct penetration test before production use
