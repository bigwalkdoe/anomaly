# Anomaly API Guide

Base URL: `http://localhost:8000/api`

Interactive documentation: `http://localhost:8000/docs`

## Authentication

All endpoints except `/api/health`, `/api/version`, and `/api/config` require authentication.

### JWT Authentication

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens expire after 15 minutes. Use the refresh token to obtain a new access token:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

## Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login (returns tokens or MFA required) | No |
| POST | `/api/auth/refresh` | Refresh access token | No |
| POST | `/api/auth/logout` | Revoke refresh token | No |
| GET | `/api/auth/me` | Get current user | Yes |

Login response when MFA is enabled:
```json
{"mfa_required": true, "user_id": "uuid", "access_token": null, "refresh_token": null}
```

### MFA (Multi-Factor Authentication)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/mfa/setup` | Setup MFA (returns secret + QR URI) | Yes |
| POST | `/api/mfa/verify` | Verify TOTP and enable MFA | Yes |
| GET | `/api/mfa/status` | Check MFA status | Yes |
| POST | `/api/mfa/disable` | Disable MFA | Yes |
| POST | `/api/mfa/backup-codes` | Regenerate backup codes | Yes |
| POST | `/api/mfa/verify-login` | Verify MFA during login | Yes |

### Engagements

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/engagements` | List engagements | Yes |
| POST | `/api/engagements` | Create engagement | Yes |
| GET | `/api/engagements/{id}` | Get engagement | Yes |
| PATCH | `/api/engagements/{id}` | Update engagement | Yes |
| DELETE | `/api/engagements/{id}` | Delete engagement | Yes |
| PUT | `/api/engagements/{id}/scope` | Update scope | Yes |
| POST | `/api/engagements/{id}/targets` | Add target | Yes |

Engagement modes: `own_infra`, `bug_bounty`, `client`
Engagement statuses: `draft`, `active`, `paused`, `closed`

Scope entry kinds: `in`, `out`

Target types: `domain`, `ip`, `cidr`, `url`, `service`

### Findings

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/engagements/{id}/findings` | List findings | Yes |
| POST | `/api/engagements/{id}/findings` | Create finding | Yes |
| GET | `/api/findings/{id}` | Get finding | Yes |
| PATCH | `/api/findings/{id}` | Update finding | Yes |
| POST | `/api/findings/{id}/status` | Transition status | Yes |
| DELETE | `/api/findings/{id}` | Delete finding | Yes |

Finding severities: `info`, `low`, `medium`, `high`, `critical`
Finding statuses: `new`, `triaged`, `confirmed`, `fixed`, `false-positive`

### Runs

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/engagements/{id}/runs` | List runs | Yes |
| POST | `/api/engagements/{id}/runs` | Create run | Yes |
| GET | `/api/runs/{id}` | Get run | Yes |

Run statuses: `queued`, `running`, `succeeded`, `failed`, `cancelled`

Available tools: `nmap`, `nuclei`, `ffuf`, `sqlmap`, `httpx`, `stub`

### Playbooks

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/engagements/{id}/playbooks` | List playbooks | Yes |
| POST | `/api/engagements/{id}/playbooks` | Create playbook | Yes |
| GET | `/api/engagements/{id}/playbooks/{id}` | Get playbook | Yes |
| PATCH | `/api/engagements/{id}/playbooks/{id}` | Update playbook | Yes |
| DELETE | `/api/engagements/{id}/playbooks/{id}` | Delete playbook | Yes |
| POST | `/api/engagements/{id}/playbooks/{id}/execute` | Execute playbook | Yes |

### Schedules

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/engagements/{id}/schedules` | List schedules | Yes |
| POST | `/api/engagements/{id}/schedules` | Create schedule | Yes |
| DELETE | `/api/engagements/{id}/schedules/{id}` | Delete schedule | Yes |

### API Keys

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/api-keys` | Create API key | Yes |
| GET | `/api/api-keys` | List API keys | Yes |
| DELETE | `/api/api-keys/{id}` | Delete API key | Yes |
| PATCH | `/api/api-keys/{id}/revoke` | Revoke API key | Yes |

Use API keys in the `Authorization` header: `Authorization: Bearer <api_key>`

### WebSocket

| Endpoint | Description | Auth |
|----------|-------------|------|
| WS `/api/ws/runs/{run_id}` | Stream run logs | Yes (token param) |
| WS `/api/ws/notifications` | Receive notifications | Yes (token param) |

### Audit

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/audit` | List audit logs | Yes (admin/member) |

### Dashboard

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/dashboard` | Get dashboard stats | Yes |

### Stats

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/stats` | Get platform stats | Yes |

### Vulnerabilities

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/vulnerabilities/summary` | Get vulnerability summary | Yes |

### Tags

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/tags` | List tags | Yes |
| POST | `/api/tags` | Create tag | Yes |

### Webhooks

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/webhooks` | List webhooks | Yes |
| POST | `/api/webhooks` | Create webhook | Yes |

### Upload

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/upload/engagements/{id}` | Upload evidence file | Yes |

### Evidence

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/evidence` | List evidence | Yes |
| GET | `/api/evidence/{id}/download` | Get download URL | Yes |
| GET | `/api/evidence/{id}/file` | Download file | Yes |

### Reports

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/reports/engagements/{id}/generate` | Generate report | Yes |

### Notifications

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/notifications` | List notifications | Yes |
| POST | `/api/notifications` | Create notification | Yes |
| POST | `/api/notifications/broadcast` | Broadcast to all users | Admin only |

### Metrics

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/metrics` | Prometheus metrics | Yes |

### Health

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/health` | Health check | No |
| GET | `/api/version` | Version info | No |
| GET | `/api/config` | Feature flags | No |

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Error message",
  "detail": null
}
```

Common status codes:
- 200: Success
- 201: Created
- 202: Accepted
- 204: No Content
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 429: Too Many Requests (rate limit or lockout)

## Rate Limiting

API requests are rate-limited to 100 requests per 60 seconds per client IP.

## Account Lockout

After 5 failed login attempts within 15 minutes, the account is locked for 30 minutes.
