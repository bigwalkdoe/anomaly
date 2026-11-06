# Anomaly User Guide

Welcome to Anomaly - an open-source, multi-user penetration-testing and cyber-operations platform.

## Getting Started

### Accessing the Platform

1. Start the platform services:
   ```bash
   cd anomaly
   docker compose up -d
   ```

2. Access the web UI at `http://localhost:3000`

3. Access the API at `http://localhost:8000` (API docs at `/docs`)

### Authentication

#### Registering an Account

Navigate to `/register` or use the API:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","name":"User","password":"securepass123"}'
```

#### Logging In

Navigate to `/login` or use the API:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

The response includes an access token and refresh token. Use the access token in the `Authorization` header for subsequent requests:
```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/auth/me
```

#### Multi-Factor Authentication (MFA)

Anomaly supports TOTP-based MFA (Google Authenticator, Authy, etc.).

**Enable MFA:**
```bash
curl -X POST http://localhost:8000/api/mfa/setup \
  -H "Authorization: Bearer <access_token>"
```

Response includes a secret key, provisioning URI (for QR code), and backup codes.

**Verify and Enable:**
```bash
curl -X POST http://localhost:8000/api/mfa/verify \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"123456"}'
```

**Login with MFA:**
1. Login with email/password - response includes `mfa_required: true`
2. Verify with TOTP code:
```bash
curl -X POST http://localhost:8000/api/mfa/verify-login \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"123456"}'
```

### Engagements

Engagements are the core of Anomaly - they define the scope and context for security testing.

#### Create an Engagement

```bash
curl -X POST http://localhost:8000/api/engagements \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Internal Network Assessment","mode":"own_infra"}'
```

#### List Engagements

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/engagements
```

#### View Engagement Details

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/engagements/<id>
```

#### Update Scope

Define in-scope and out-of-scope targets:
```bash
curl -X PUT http://localhost:8000/api/engagements/<id>/scope \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"entries":[{"kind":"in","target_value":"example.com"},{"kind":"out","target_value":"evil.com"}]}'
```

### Findings

Findings represent security vulnerabilities discovered during engagements.

#### Create a Finding

```bash
curl -X POST http://localhost:8000/api/engagements/<id>/findings \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"SQL Injection","severity":"high","description":"..."}'
```

#### List Findings

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/engagements/<id>/findings
```

#### Update Finding Status

```bash
curl -X POST http://localhost:8000/api/findings/<id>/status \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"status":"triaged"}'
```

### Runs

Runs represent tool executions against targets.

#### Start a Run

```bash
curl -X POST http://localhost:8000/api/engagements/<id>/runs \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"tool":"nmap","targets":["example.com"]}'
```

#### List Runs

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/engagements/<id>/runs
```

### Reports

Generate reports from engagement findings.

#### Generate a Report

```bash
curl -X GET http://localhost:8000/api/reports/engagements/<id>/generate?format=markdown \
  -H "Authorization: Bearer <access_token>"
```

### API Keys

API keys allow programmatic access without username/password.

#### Create an API Key

```bash
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"My API Key","scopes":"*"}'
```

The response includes the actual key value - save it securely as it won't be shown again.

### Roles and Permissions

- **admin**: Full access to all engagements and system settings
- **pentester**: Can create/run tools, manage findings within assigned engagements
- **client_viewer**: Read-only access to assigned engagements

## Support

For issues and feature requests, visit: https://github.com/bigwalkdoe/anomaly
