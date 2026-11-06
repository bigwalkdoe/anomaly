# Anomaly Phase 2: Security Hardening & Production Readiness

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden security (MFA, account lockout), add real-time notifications, complete documentation, and prepare for production deployment.

**Architecture:** Extend existing auth with TOTP MFA, add WebSocket notification channel, enhance CI/CD with security scanning, write comprehensive docs.

**Tech Stack:** Python 3.12, pyotp, qrcode, existing FastAPI/WebSocket stack

**Spec:** `docs/superpowers/specs/2026-11-03-anomaly-design.md`

## File Structure

```
anomaly/
├── packages/core/src/anomaly_core/mfa.py          # TOTP MFA implementation
├── packages/core/src/anomaly_core/models/mfa.py   # MFA model (secret, enabled, backup codes)
├── apps/api/src/anomaly_api/routers/mfa.py        # MFA endpoints (setup, verify, disable)
├── apps/api/src/anomaly_api/routers/notifications.py # Enhanced with WebSocket broadcast
├── docs/USER_GUIDE.md                             # User guide
├── docs/DEPLOYMENT_GUIDE.md                       # Production deployment
├── docs/API_GUIDE.md                              # API reference
└── tests/                                         # Tests for all new features
```

---

### Task 1: MFA (Multi-Factor Authentication)

**Files:**
- Create: `packages/core/src/anomaly_core/mfa.py`
- Create: `packages/core/src/anomaly_core/models/mfa.py`
- Modify: `packages/core/src/anomaly_core/models/__init__.py`
- Create: `apps/api/src/anomaly_api/routers/mfa.py`
- Modify: `apps/api/src/anomaly_api/main.py`
- Test: `tests/api/test_mfa.py`

**Interfaces:**
- `MFASecret` model: user_id, secret_key, is_enabled, backup_codes, created_at
- `generate_totp_secret()` -> str
- `generate_backup_codes()` -> list[str]
- `verify_totp(secret, code)` -> bool
- Endpoints: `POST /api/mfa/setup`, `POST /api/mfa/verify`, `POST /api/mfa/disable`, `GET /api/mfa/status`
- Login flow: if MFA enabled, require TOTP code after password

- [ ] **Step 1: Write failing tests** (setup, verify, disable, login with MFA)
- [ ] **Step 2: Implement mfa.py** (TOTP generation/verification)
- [ ] **Step 3: Implement MFA model** (secret, backup codes)
- [ ] **Step 4: Implement MFA router** (setup/verify/disable/status)
- [ ] **Step 5: Modify login** to require MFA code when enabled
- [ ] **Step 6: Run tests and commit**

---

### Task 2: Account Lockout

**Files:**
- Modify: `apps/api/src/anomaly_api/routers/auth.py`
- Create: `packages/core/src/anomaly_core/models/login_attempt.py`
- Test: `tests/api/test_lockout.py`

**Interfaces:**
- `LoginAttempt` model: user_id, success, ip_address, user_agent, created_at
- Lockout: 5 failed attempts within 15 minutes -> lock for 30 minutes
- Reset on successful login

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Implement LoginAttempt model**
- [ ] **Step 3: Modify login** to track attempts and enforce lockout
- [ ] **Step 4: Run tests and commit**

---

### Task 3: Real-Time WebSocket Notifications

**Files:**
- Modify: `apps/api/src/anomaly_api/routers/ws.py`
- Modify: `apps/api/src/anomaly_api/routers/notifications.py`
- Test: `tests/api/test_ws_notifications.py`

**Interfaces:**
- WebSocket channel for notification broadcasts
- `POST /api/notifications/broadcast` (admin only)
- Client receives real-time notifications via WebSocket
- Notification types: info, warning, error, success

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Implement WebSocket notification channel**
- [ ] **Step 3: Implement broadcast endpoint**
- [ ] **Step 4: Run tests and commit**

---

### Task 4: Documentation

**Files:**
- Create: `docs/USER_GUIDE.md`
- Create: `docs/DEPLOYMENT_GUIDE.md`
- Create: `docs/API_GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Write USER_GUIDE** (auth, engagements, findings, runs, reports)
- [ ] **Step 2: Write DEPLOYMENT_GUIDE** (docker-compose, helm, environment variables)
- [ ] **Step 3: Write API_GUIDE** (endpoint reference, auth, examples)
- [ ] **Step 4: Update README** (quick start, features)
- [ ] **Step 5: Commit**

---

### Task 5: Performance & Security Testing

**Files:**
- Modify: `performance/locustfile.py`
- Create: `tests/security/test_auth_security.py`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Enhance locustfile** (auth, engagements, findings, runs workflows)
- [ ] **Step 2: Add security tests** (SQL injection, XSS, auth bypass)
- [ ] **Step 3: Add security scan to CI**
- [ ] **Step 4: Run and commit**

---

### Self-Review

1. MFA: TOTP-based, backup codes, login flow integration
2. Lockout: 5 failures/15min -> 30min lockout, reset on success
3. Notifications: WebSocket broadcast, admin-only broadcast endpoint
4. Docs: User guide, deployment guide, API guide, README update
5. Tests: Load testing, security tests, CI integration
