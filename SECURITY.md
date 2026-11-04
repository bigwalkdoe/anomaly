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
- Consider adding: X-Content-Type-Options, X-Frame-Options, CSP

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
