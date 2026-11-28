# Production Readiness Checklist

This is the canonical release gate for Anomaly. It is a checklist to be satisfied with recorded evidence, **not** a declaration that the platform is production-ready. Anomaly remains **pre-production / active development** until the blockers below are closed.

Each box requires a linked artifact in the release record: command output, a config export with secrets redacted, a dashboard screenshot, or a named reviewer's sign-off. "Checked manually" without evidence is not sufficient.

## Release gates

### Code and quality

- [ ] `ruff check .` passes on the release commit; link the command output.
- [ ] `python3 -m mypy packages apps` passes on the release commit; link the command output.
- [ ] The full `pytest` suite passes with the exact target set in [Evidence commands](#evidence-commands); link the summary line and test count.
- [ ] CI is green for the release commit, including lint, typecheck, tests, and security scans.

### Migration and data

- [ ] `alembic heads` reports exactly one head, `b2c3d4e5f6a7 (head)`; link the output.
- [ ] `alembic upgrade head` succeeds against a clean PostgreSQL database and `alembic check` reports no new operations; link both outputs.
- [ ] Production backups are verified by a restore test, and the restore point is recorded in the release record.
- [ ] Seed/demo data is absent from the production database; link the verification query or snapshot.

### Security and configuration

- [ ] All default secrets are replaced, including `JWT_SECRET`, database, Redis, and MinIO credentials; record the secret manager paths, never the values.
- [ ] `ANOMALY_CORS_ORIGINS` is set to explicit trusted origins (or `CORS_ALLOW_ORIGINS` is used consistently); wildcard origins are absent.
- [ ] `ANOMALY_METRICS_AUTH_REQUIRED=true` is set and `/api/metrics` rejects anonymous access; link the response.
- [ ] `MAX_UPLOAD_SIZE_BYTES` is set to the approved limit and oversized uploads are rejected; link the response.
- [ ] Security headers are verified on API responses, including `Content-Security-Policy` on `/docs` and `/redoc`; link the header dump.
- [ ] WebSocket clients authenticate with the token param or `Authorization: Bearer` header; unauthenticated upgrades are rejected; link both responses.
- [ ] TLS is terminated in front of the API and web UI; link the certificate/ingress configuration.
- [ ] Rate limiting, account lockout, and MFA settings match the security policy in [SECURITY.md](../SECURITY.md).

### Execution and evidence

- [ ] `RUNNER_MODE` and `ANOMALY_INLINE_RUNS` are unset or disabled in production; evidence shows runs use the isolated runner path.
- [ ] Runner network isolation is verified: `ANOMALY_RUNNER_NETWORK` is `none` or an explicitly reviewed restricted network; link the runner config.
- [ ] Scope and policy decisions are verified for a sample run: out-of-scope targets are denied/logged and audit events are present; link the audit extract.
- [ ] Evidence objects have SHA/provenance metadata and report traceability is present in the sampled run; link the evidence/report records.
- [ ] Run creation with `Idempotency-Key` is verified: a retry returns the original run with `202` and `idempotent_replay`, with no duplicate enqueue or inline execution; link both responses and the audit events.
- [ ] Audit log retention and access controls are configured and verified against [SECURITY.md](../SECURITY.md).

### Release sign-off

- [ ] Release owner is named in the release record.
- [ ] Every gate above links evidence collected from the release commit and the target environment.
- [ ] Residual risks are listed with owner and review date.
- [ ] Rollback procedure is documented and the last restore/rollback drill is linked.

## Operational verification

Run these checks on a recurring schedule, not only at release time:

- **Daily:** confirm API/worker health, failed-run rate, queue depth, and alert delivery.
- **Weekly:** review audit events for denied scope/policy decisions, idempotent replays, and unexpected admin actions.
- **Weekly:** confirm backups completed and `alembic check` still reports no drift in the deployed environment.
- **Monthly:** review `ANOMALY_CORS_ORIGINS`, `ANOMALY_METRICS_AUTH_REQUIRED`, `MAX_UPLOAD_SIZE_BYTES`, and TLS certificate expiry.
- **After every runner/image change:** re-run one scoped assessment end to end and verify runner isolation, evidence integrity, and report traceability.
- **After every API change:** re-check `Idempotency-Key` replay behavior, `Authorization: Bearer` on WebSockets, and admin-only endpoints.

## Evidence commands

Run from the repository root with the workspace virtualenv and environment loaded:

```bash
set -a && source .env && set +a
export PYTHONPATH=apps/api/src:apps/worker/src:apps/cli/src:packages/core/src:packages/tools/src:packages/ai/src:packages/reporting/src:packages/integrations/src:packages/common/src

ruff check .
python3 -m mypy packages apps
.venv/bin/python -m pytest -q tests/api tests/core tests/ai tests/tools tests/security tests/docs

cd packages/core
../../.venv/bin/alembic heads
../../.venv/bin/alembic upgrade head
../../.venv/bin/alembic check
```

Record the exact pytest pass count and the `alembic heads` output in the release record. `pytest` output alone is not evidence unless the target list and commit SHA are recorded with it.

## Known blockers

The platform stays pre-production while the gaps in [README.md](../README.md) remain open:

- consistent Organization/Workspace enforcement across every API, WebSocket, export, and worker surface;
- governed execution coverage for every execution entry point, including hardened isolated runner containment and limits;
- comprehensive object-store checksum verification, retention enforcement, and end-to-end traceability;
- session/browser hardening, dependency/security remediation SLAs, staging/monitoring/backup-recovery automation, and authenticated runtime QA.

A gate cannot be marked complete by pointing at a planned feature. Blocker closure requires shipped code plus evidence.

## Sign-off

The release record must contain:

- named release owner and reviewer;
- date and release commit SHA;
- links to all evidence artifacts;
- explicit acceptance or waiver of each residual risk, with owner and review date;
- rollback/restore verification reference.

Without all five, the checklist is incomplete and the release is not approved.
