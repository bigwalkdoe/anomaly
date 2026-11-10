# Anomaly Full Platform Design Blueprint

Product architecture • system design • security engineering • implementation strategy

Security Operations & Intelligence Platform

Discover. Investigate. Validate. Respond. Govern.

## TARGET-STATE ARCHITECTURE

Prepared 10 November 2026
Design specification — not a claim of implemented or verified functionality.

## Contents

1. Product definition
2. Target-state system architecture
3. Application modules
4. Identity, tenancy and authorization
5. Data architecture
6. Backend architecture
7. Execution engine and isolation
8. Frontend and UX blueprint
9. API architecture
10. Observability and operations
11. Deployment and infrastructure
12. Security engineering baseline
13. Subscription and commercial architecture
14. Implementation roadmap
15. Repository restructuring
16. Quality gates and release criteria
17. First production-grade vertical slice
18. Final architectural decisions
19. Blueprint acceptance checklist
20. Implementation next steps

## Document use

Use this blueprint as the target-state design reference. Before implementation, compare it against the live repository, preserve working components, document deviations and convert approved changes into small, testable GitHub issues.

## Important qualification

This document describes a proposed architecture. It does not establish that the repository currently implements these capabilities, nor does it constitute a completed source-code audit, penetration test or production-readiness certification.

## 1. Product definition

Anomaly should become a unified security operations control plane that manages the full security assessment and investigation lifecycle. Its differentiation should be orchestration, governance, evidence integrity and intelligence—not merely a user interface that launches individual security tools.

### 1.1 Product vision

Unify authorized offensive security, defensive monitoring, AI-assisted investigation, automation, evidence management and reporting within one governed platform.

Capability | Purpose
--- | ---
Asset intelligence | Maintain an inventory and relationship model for authorized assets.
Vulnerability management | Discover, classify, prioritize and track weaknesses.
Offensive security | Coordinate authorized assessments through controlled execution.
Defensive monitoring | Ingest events, detect suspicious activity and manage incidents.
AI intelligence | Correlate, explain and summarize security information.
Automation | Orchestrate repeatable, policy-governed workflows.
Governance | Enforce scope, authorization, approvals and auditability.
Evidence management | Preserve verifiable evidence and provenance.
Reporting | Produce technical, executive and compliance-oriented outputs.

### 1.2 Target customers

- Managed Security Service Providers (MSSPs).
- Internal enterprise security teams and SOCs.
- Penetration-testing consultancies.
- DevSecOps and platform security teams.
- Small and medium-sized businesses.

### 1.3 Positioning

Primary: Security Operations Platform. Supporting: AI-assisted security assessment and vulnerability intelligence. Avoid positioning Anomaly exclusively as a penetration-testing product; that would constrain future defensive and governance capabilities.

## 2. Target-state system architecture

Presentation: Next.js dashboard | CLI | REST API | WebSockets
Identity & API: OIDC | RBAC | tenant context | rate limits
Core control plane: Organizations / Engagements / Assets / Vulnerabilities Policy / Workflow / AI Intelligence / Evidence / Reporting
Job orchestration: Redis queue | scheduler | event contracts
Execution: isolated assessment runners | defensive collectors

Use a modular monolith for the central control plane, with independently deployable workers and isolated execution services. This retains strong domain boundaries without introducing premature microservice complexity.

Data: PostgreSQL | Redis | MinIO | search/indexing

### 2.1 Architectural principles

- All user-facing operations pass through centralized identity and authorization.
- Every assessment operation requires explicit scope validation.
- AI cannot bypass policy or grant itself execution permissions.
- Tool execution never runs inside the API process.
- Workers operate with scoped identities and least privilege.
- Evidence is traceable to an organization, engagement, job and execution.
- Sensitive operations generate auditable events.
- Modules communicate through documented interfaces and versioned event contracts.

### 2.2 Core control-plane components

Component | Responsibility
--- | ---
Identity and tenancy | Authentication, membership, roles, tenant context.
Engagement manager | Scope, exclusions, approvals, dates and ownership.
Asset intelligence | Asset inventory, observations and relationships.
Vulnerability manager | Findings, CVEs, risk and remediation lifecycle.
Policy engine | Authorization decisions, quotas and execution constraints.
Workflow orchestrator | Job lifecycle, scheduling, retries and state transitions.
AI intelligence | Analysis, retrieval, structured proposals and usage controls.
Evidence and reporting | Evidence provenance, integrity, retention and exports.

## 3. Application modules

### 3.1 Workspace dashboard

Provide a real-time operational overview: security posture, active engagements, monitored assets, critical/high findings, open incidents, running assessments, failed jobs, recent events, risk distribution, activity timeline and system health.

Filters should include organization, workspace, engagement, date range, severity and asset category. Scores must derive from documented metrics, not arbitrary AI-generated ratings.

### 3.2 Asset intelligence

Maintain domains, subdomains, IP addresses, hosts, services, technologies, cloud assets, certificates, ownership, tags, relationships and historical changes. Asset lifecycle: DISCOVERED → UNVERIFIED → VALIDATED → AUTHORIZED → MONITORED → ARCHIVED. Discovery must never imply permission to test.

### 3.3 Vulnerability management

Support discovery, CVE/CWE classification, CVSS scoring, exploitability context, affected-asset mapping, duplicate detection, remediation tracking, exceptions, risk acceptance, reassessment and trend analysis. CVSS is severity—not complete business risk. Include asset criticality, exposure, exploit intelligence and business impact.

### 3.4 Offensive security operations

Coordinate authorized tools such as Nmap, Nuclei, HTTPX, FFUF, SQLMap, OWASP ZAP and Nikto. Each adapter needs version identification, structured input, timeout, resource limits, output normalization, error classification, scope enforcement and audit logging. The central policy engine—not the adapter—decides authorization.

### 3.5 Defensive monitoring and incident management

Provide security event ingestion, normalization, detection rules, alert correlation, incident creation, assignment, investigation timelines, evidence attachment, response playbooks and closure. Keep the detection engine independent of offensive assessment runners while sharing appropriate asset and evidence models.

### 3.6 AI intelligence

Support finding explanation, prioritization assistance, duplicate analysis, evidence summaries, executive report drafts, remediation recommendations, incident timelines, natural-language search and security knowledge retrieval. AI should propose actions; policy and authorization services determine whether they can execute.

### 3.7 Engagement management

Record customer, owner, authorized users, scope, exclusions, start/expiry dates, permitted assessment types, execution limits, approvals, evidence retention and reporting requirements. Lifecycle: DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE → COMPLETED → ARCHIVED.

### 3.8 Evidence management

Treat evidence as a first-class entity. Store evidence ID, organization, engagement, asset, finding, job, type, storage location, SHA-256 checksum, creation time, collector identity, tool/version, classification and retention policy.

### 3.9 Reporting and compliance

Generate executive assessments, technical penetration-testing reports, vulnerability assessments, incident investigations, asset inventories, remediation progress, posture reports and audit exports. Support PDF, HTML, Markdown, JSON and CSV. Compliance mappings must be versioned and must not imply certification.

### Recommended severity bands

Severity | CVSS reference | Suggested treatment
--- | --- | ---
Critical | 9.0–10.0 | Immediate review and containment/remediation planning.
High | 7.0–8.9 | Priority remediation.
Medium | 4.0–6.9 | Planned remediation.
Low | 0.1–3.9 | Routine remediation.
Informational | N/A | Context and investigation.

## 4. Identity, tenancy and authorization

Platform → Organization A → Workspace 1 → Engagement 1 & Engagement 2
Platform → Organization A → Workspace 2
Platform → Organization B → Workspace 1 → Engagement 3

Identity and authorization are foundational security subsystems. Model the hierarchy as Platform → Organization → Workspace → Engagement. Tenant context must be derived from authenticated membership and server-side authorization, never trusted solely from a client-supplied organization identifier.

### 4.1 Recommended roles

Role | Scope / responsibility
--- | ---
Platform Owner | Platform-wide administration.
Organization Owner | Organization governance and ownership.
Organization Admin | Users, settings and policies.
Security Admin | Security configuration and controls.
Security Analyst | Investigation and analysis.
Pentester | Authorized assessments only.
Incident Responder | Incident operations.
Auditor | Read-only audit access.
Viewer | Restricted dashboard access.

Use permission-based authorization beneath roles. Example permissions include engagement.read/create/approve/execute; asset.read/manage; finding.read/update/accept_risk; evidence.read/export; incident.read/assign/close; organization.manage; user.manage; policy.manage; and audit.read.

### 4.2 Authentication design

- OAuth 2.0 / OpenID Connect.
- TOTP MFA and single-use recovery codes.
- Secure session management, revocation and rotation.
- Scoped, expiring API keys and service credentials.
- Optional enterprise SAML SSO.
- Resource-level authorization and administrative audit trails.
- Secure, HttpOnly, SameSite browser cookies and appropriate CSRF protection.

### 4.3 Authorization enforcement

Evaluate organization membership, resource ownership, engagement scope, requested permission and contextual policy at the service/data-access layer. Apply checks consistently to APIs, worker tasks, WebSockets, evidence retrieval and report exports. Frontend menu visibility is not a security boundary.

## 5. Data architecture

PostgreSQL should be the system of record. Redis supports transient state and job coordination. MinIO stores evidence and larger artifacts. Add specialized data stores only when measured workload requirements justify them.

Domain | Core entities / tables
--- | ---
Identity | users, roles, permissions, sessions, mfa_methods
Tenancy | organizations, memberships, workspaces
Engagements | engagements, scopes, approvals

Domain | Core entities / tables
Assets | assets, asset_relationships, asset_observations
Assessment | scans, jobs, executions, tool_versions
Vulnerabilities | findings, vulnerabilities, cve_records
Incidents | incidents, alerts, security_events
Evidence | evidence, evidence_access, evidence_versions
Automation | workflows, workflow_runs, workflow_steps
AI | ai_sessions, model_usage, ai_actions
Governance | policies, policy_decisions, approvals
Billing | plans, subscriptions, usage_records
Audit | audit_events, audit_checkpoints

### 5.1 Core relationships

Organization 1--N Workspaces
Organization 1--N Memberships; User 1--N Memberships
Workspace 1--N Engagements
Engagement 1--N Scopes, Assets, Jobs, Approvals, Incidents
Asset 1--N Findings
Job 1--N Executions and Evidence
Finding 1--N Evidence
Organization 1--N Policies
User 1--N Audit Events

### 5.2 Data isolation

- Mandatory organization identifiers on tenant-owned records.
- PostgreSQL Row-Level Security where appropriate.
- Explicit tenant context in application services and transactions.
- Scoped repository access and database permissions.
- Object storage paths partitioned by tenant.
- Authorization before object retrieval and report download.
- Automated cross-tenant isolation tests.

### 5.3 Event architecture

```json
{
  "event_id": "uuid",
  "event_type": "assessment.completed",
  "schema_version": 1,
  "organization_id": "uuid",
  "engagement_id": "uuid",
  "job_id": "uuid",
  "occurred_at": "2026-11-10T10:00:00Z",
  "payload": {}
}
```

Use versioned event contracts and a transactional outbox for reliable publication. Consumers must be idempotent and schemas should evolve compatibly.

Recommended events include asset.discovered, asset.validated, engagement.approved, engagement.expired, assessment.requested/started/completed/failed, finding.created/updated, evidence.collected, incident.created/closed, workflow.completed and policy.denied.

## 6. Backend architecture

Retain the existing FastAPI and Next.js direction unless source-level review identifies a material reason to change it.

Layer | Recommended technology | Responsibility
--- | --- | ---
Frontend | Next.js + TypeScript | Web application and typed contracts.
Backend | FastAPI + Python | Application API and services.
Validation | Pydantic | Typed request/response schemas.
ORM | SQLAlchemy 2 | Database access.
Migrations | Alembic | Schema evolution.
Database | PostgreSQL | Primary persistence.
Queue | Redis + ARQ initially | Background processing.
Object storage | MinIO | Evidence and artifacts.
Realtime | WebSockets | Live updates.
AI | Provider adapters | Model orchestration.
Monitoring | Prometheus + Grafana | Metrics and operations.
Containers | Docker | Runtime packaging and isolation.
Orchestration | Kubernetes | Production scheduling.

### 6.1 Suggested package boundaries

```
apps/
  api/
  worker/
  scheduler/
  runner/
  cli/
  web/
packages/
  identity/
  tenancy/
  engagements/
  assets/
  vulnerabilities/
  incidents/
  evidence/
  orchestration/
  policy/
  ai/
  integrations/
  reporting/
  audit/
  common/
```

### 6.2 Layering rules

```
HTTP / API
  → Application Services
    → Domain Logic
      → Repository Interfaces
        → Infrastructure Adapters
          → PostgreSQL / Redis / MinIO
```

- Routers should not contain business logic.
- Domain logic should not depend on FastAPI.
- Repository interfaces isolate persistence concerns.
- Tool adapters must not make authorization decisions.
- Application services define transaction boundaries.
- Shared packages must not become dumping grounds.

## 7. Execution engine and isolation architecture

The runner is among the most sensitive components. It should be a separate trust boundary with a narrowly defined input contract and no unrestricted platform credentials.

```
API | Policy Engine → Authorization → Approval Check | Job Queue → Worker → Execution Scheduler | Isolated Runner | Result Normalizer → Evidence Store
```

### 7.1 Execution manifest

A runner receives an authenticated execution manifest containing job ID, organization ID, engagement ID, approved scope reference, tool identifier/version, resource limits, expiration, output destination and execution policy. Credentials must be short-lived and scoped.

### 7.2 Isolation levels

Level | Environment | Intended use
--- | --- | ---
Development | Local containers | Development and testing.
Standard | Restricted containers | Routine approved operations.
Enhanced | Dedicated isolated workers | Higher-risk operations.
High assurance | Separate VM or dedicated execution node | Stronger tenant separation.

### 7.3 Container hardening baseline

```yaml
security_opt: no-new-privileges:true
read_only: true
cap_drop: ALL
pids_limit: 128
mem_limit: 512m
cpus: 1.0
tmpfs: /tmp:size=64m,noexec,nosuid,nodev
```

This is illustrative, not universal. Some tools require narrowly justified capabilities or writable paths. Additional controls: no Docker socket, no host PID namespace, no host filesystem mounts, explicit egress/DNS policies, image provenance and scanning, cleanup, scoped credentials and cancellation.

### 7.4 Scope enforcement

Validate every resolved destination, not only the originally supplied domain. Account for allowlists, exclusions, DNS resolution, redirects, IPv4/IPv6, private and link-local addresses, DNS rebinding, scope expiry and scope changes during execution. A redirect or DNS change must not silently authorize a new target.

### 7.5 Job lifecycle

```
CREATED → VALIDATING → AWAITING_APPROVAL → QUEUED → RUNNING → COLLECTING_RESULTS → COMPLETED

FAILED

CANCELLED
```

Retries should be limited to transient failures. Do not automatically repeat operations with unsafe side effects. Record state transitions and their causes.

## 8. Frontend and UX blueprint

The frontend should resemble a professional security operations console: information-dense, navigable and accessible, without becoming visually cluttered.

### 8.1 Main navigation

```
ANOMALY
• Workspace: Overview | Activity | System Health
• Intelligence: Assets | Attack Surface | Vulnerabilities | Risk
• Operations: Engagements | Assessments | Executions | Workflows | Tools
• Defense: Security Events | Alerts | Incidents | Investigations
• AI Intelligence: Assistant | Analysis | Knowledge | Usage
• Evidence: Repository | Findings | Reports
• Governance: Policies | Approvals | Audit Trail | Compliance
• Administration: Organization | Users/Roles | Integrations
• API Keys | Notifications | Billing | Settings
```

Use permission-aware navigation, but enforce access on the server. Core pages include Overview, Assets, Asset Details, Engagements, Assessment Details, Vulnerabilities, Finding Details, Incidents, AI Assistant, Evidence, Reports, Policies and Administration.

### 8.2 Visual design system

Token | Value | Use
--- | --- | ---
Midnight navy | #101927 | Main background
Slate | #1B293B | Panels and surfaces
Electric cyan | #42C9E8 | Primary accent
Violet | #8B7CFF | AI features
Critical | Red status token | Critical severity
High | Amber status token | High severity
Resolved | Green status token | Resolved state

Design rules: dark theme default with light option; high information density; consistent spacing and typography; keyboard access; responsive layouts; clear loading/empty/error/success states; accessible contrast; never communicate severity by color alone.

### 8.3 Key interaction flows

- New engagement: create → select organization/workspace → define authorized scope and exclusions → assign users → set execution policy → submit for approval → activate.
- Finding remediation: discovery → validation → risk calculation → owner assignment → remediation → reassessment → verified resolution.

## 9. API architecture

Use versioned REST APIs as the primary integration contract, with base path /api/v1/.

Resource | Example endpoint
--- | --- | ---
Authentication | /auth/login
Organizations | /organizations
Users | /users

Resource | Example endpoint
--- | --- | ---
Workspaces | /workspaces
Engagements | /engagements
Scopes | /engagements/{id}/scopes
Assets | /assets
Findings | /findings
Vulnerabilities | /vulnerabilities
Assessments | /assessments
Jobs | /jobs
Incidents | /incidents
Evidence | /evidence
Reports | /reports
Workflows | /workflows
Policies | /policies
Approvals | /approvals
Audit events | /audit-events
Integrations | /integrations

### 9.1 API standards

- OpenAPI documentation and consistent response envelopes.
- Pagination, filtering and sorting.
- Strict request validation and structured errors.
- Correlation IDs and idempotency keys for sensitive operations.
- Rate limits, API versioning and audit event generation.
- No internal exception traces or secrets in responses.

Example response:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "queued"
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

### 9.2 Realtime

Use authenticated WebSockets for job progress, scan status, incident updates, alerts, workflow progress and system health. Authorize each subscription against its resource and support revocation.

## 10. Observability and operations

Anomaly must be observable as a platform in its own right.

Area | Metrics
--- | ---
Application | Request rate, error rate, P50/P95/P99 latency, auth failures, authorization denials.
Workers | Queue depth, execution time, failure rate, retries, worker availability.
Runners | CPU/memory, duration, termination count, resource-limit violations.
Business | Active engagements, findings created/resolved, evidence storage, AI token use, organization usage.

### 10.1 Structured logging

```json
{
  "timestamp": "2026-11-10T10:00:00Z",
  "level": "INFO",
  "service": "anomaly-worker",
  "event": "job.completed",
  "organization_id": "uuid",
  "job_id": "uuid",
  "correlation_id": "uuid"
}
```

Never log passwords, API secrets, authentication tokens, unredacted sensitive evidence or private keys.

### 10.2 Alerting

- API downtime and elevated error rates.
- Database connectivity and queue backlog.
- Repeated runner crashes or abnormal resource consumption.
- Suspicious authentication and unauthorized access.
- Evidence storage failures and backup failures.
- Unexpected usage spikes and critical service degradation.

## 11. Deployment and infrastructure blueprint

Support development, staging and production with consistent architecture and environment-specific configuration.

Environment | Purpose | Controls
--- | --- | ---
Development | Fedora workstation / Docker Compose | Synthetic data, local services, developer credentials.
Staging | Isolated infrastructure | Integration and security testing; no uncontrolled production data.
Production | Hardened deployment | Customer data, monitoring, backups, approvals and restricted access.

### 11.1 Infrastructure components

Component | Deployment recommendation
--- | ---
Web frontend | Next.js container or managed hosting.
API | FastAPI containers.
Worker / scheduler | Dedicated processes and identities.
Runner | Isolated execution nodes.
PostgreSQL | Managed or hardened private database.
Redis | Private queue infrastructure.
MinIO | Private object storage.
Monitoring | Prometheus and Grafana.
Reverse proxy | TLS termination and routing.
Secrets | External secrets manager.

Do not expose PostgreSQL, Redis, MinIO administration or runner control interfaces directly to the public internet.

### 11.2 Network topology

```
Internet | Reverse Proxy
    |
    +---- Web UI + API
            | Identity / Policy
            | Application Core
            | Redis Queue
            | Workers
            | Isolated Runners
    PostgreSQL <--> Core
    MinIO <--> Evidence
    Prometheus <--> Services
```

### 11.3 Backup and recovery

- Automated PostgreSQL backups and point-in-time recovery.
- MinIO object versioning and encrypted off-site copies.
- Configuration and infrastructure-as-code backups.
- Documented restore procedures and regular restoration exercises.
- Define RPO and RTO based on business requirements.

Metric | Proposed initial target
--- | --- | ---
RPO | 15 minutes
RTO | 4 hours
Backup verification | Daily
Recovery exercise | Quarterly

These are proposed objectives, not verified capabilities. Confirm feasibility and cost against the selected infrastructure.

## 12. Security engineering baseline

Control | Required implementation
--- | --- | ---
Authentication | OIDC, MFA, secure sessions.
Authorization | RBAC plus resource-level policies.
Tenancy | Tenant isolation and RLS where appropriate.
Secrets | External secrets manager.
Transport | TLS.
Database | Encryption at rest and least privilege.
Evidence | Checksums, access controls, retention.
Execution | Sandboxed, non-root runners.
Network | Segmentation and egress controls.
AI | Prompt-injection resistance and tool authorization.
Audit | Append-only, independently verifiable events.
Dependencies | Vulnerability scanning and update policy.
Containers | Image scanning and hardened runtime.
CI/CD | Protected deployment approvals.
Recovery | Encrypted backups and tested restoration.

### 12.1 Threat modelling with STRIDE

Threat | Example | Mitigation
--- | --- | ---
Spoofing | Stolen API credentials | MFA, short-lived tokens.
Tampering | Modified evidence | Hashing, immutable versions.
Repudiation | User denies launching assessment | Auditable event trail.
Information disclosure | Cross-tenant evidence access | Isolation and authorization.
Denial of service | Excessive jobs | Quotas and resource limits.
Elevation of privilege | Runner compromises host | Runtime isolation.

### 12.2 Standards to use as references

- OWASP ASVS and OWASP API Security Top 10.
- NIST Secure Software Development Framework (SSDF).
- CIS Docker and Kubernetes Benchmarks.
- SLSA principles for software supply-chain integrity.
- NIST SP 800-61 for incident response.

Treat these as engineering references and control mappings. Their inclusion does not imply certification or compliance.

## 13. Subscription and commercial architecture

Design for commercial multi-tenancy even if the first release is self-hosted. Keep entitlement evaluation separate from core authorization: a user may be authorized to perform an operation while the subscription may not include the feature or usage allowance.

Edition | Target customer | Indicative capabilities
--- | --- | ---
Community | Individual researchers and labs | Local deployment, asset inventory, basic assessments, findings and reports, limited integrations.
Professional | Consultants and small teams | Multiple engagements, advanced assessment management, AI intelligence, workflows, reporting and collaboration.
Enterprise | Large organizations and MSSPs | SSO, advanced RBAC, custom retention, dedicated runners, compliance features, audit exports and enterprise integrations.

### 13.1 Metering dimensions

- Active assets and assessment execution minutes.
- Completed assessments and workflow executions.
- Evidence storage and retention period.
- AI token consumption and model costs.
- Users, seats and dedicated runner capacity.

Use immutable usage records, idempotent ingestion, reconciliation and explicit quota behavior. Avoid making every feature depend on one arbitrary usage metric.

## 14. Implementation roadmap

Implement incrementally. Preserve sound existing components and build a secure vertical slice before expanding into every module.

Phase | Workstream | Estimate
--- | --- | ---
0 | Repository audit and baseline | 1 week
1 | Core architecture and security foundations | 2 weeks
2 | Identity, tenancy and governance | 2–3 weeks
3 | Assets and engagement management | 2 weeks
4 | Assessment and execution engine | 3–4 weeks
5 | Findings, evidence and reporting | 2 weeks
6 | AI intelligence and workflows | 2–3 weeks
7 | Defensive operations | 3–4 weeks
8 | Production hardening | 2–3 weeks

Estimates assume focused engineering capacity. Actual duration depends on current implementation quality, team size, dependencies and test coverage.

### 14.1 Phase exit criteria

Phase | Deliverables / exit criteria
--- | --- | ---
0 — Baseline | Inventory apps, packages, endpoints, tables, integrations, tests, deployments and technical debt. Every subsystem has an implementation status and owner.
1 — Core | Standard config, domain boundaries, error handling, structured logging, migrations, event contracts and shared authorization interfaces.
2 — Security | Identity hardening, MFA, RBAC, tenant isolation, policy engine, approvals and audit pipeline. Cross-tenant tests pass.
3 — Intelligence | Asset inventory, relationships, scope validation, engagement lifecycle, findings and risk prioritization.
4 — Execution | Scheduler, tool registry, manifests, isolated runners, output normalization, cancellation and audit. Approved operation executes safely.
5 — Evidence | Evidence repository, integrity, retention, finding relationships and reports. Engagement yields traceable report.
6 — AI | Provider abstraction, structured outputs, policy-gated proposals, workflows, metering and audit.
7 — Defense | Event ingestion, detections, alerts, incidents, investigation timeline and response playbooks.
8 — Production | Hardened images, Kubernetes, monitoring, recovery, security regression, load tests, deployment approvals and runbooks.

## 15. Repository restructuring blueprint

```
anomaly/
  apps/
    web/
    api/
    worker/
    scheduler/
    runner/
    cli/
  packages/
    identity/
    tenancy/
    engagements/
    assets/
    vulnerabilities/
    incidents/
    evidence/
    orchestration/
    policy/
    ai/
    integrations/
    reporting/
    audit/
    common/
  infrastructure/
    docker/
    kubernetes/
    helm/
    monitoring/
    networking/
    secrets/
  database/
    migrations/
    schemas/
    seeds/
  contracts/
    api/
    events/
    tool-manifests/
  tests/
    unit/
    integration/
    security/
    tenancy/
    runner/
    performance/
    e2e/
  docs/
    architecture/
    adr/
    security/
    operations/
    api/
    development/
  scripts/
  .github/workflows/
  docker-compose.yml
  docker-compose.prod.yml
  pyproject.toml
  Makefile
  SECURITY.md
  CONTRIBUTING.md
  README.md
```

Do not immediately rename or move everything. First map the live repository to target logical boundaries. Avoid restructuring that breaks imports, deployment paths, CI or staging.

### 15.1 Architecture decision records

ADR | Decision
--- | ---
001 | Modular monolith versus microservices.
002 | Multi-tenant data isolation.
003 | Identity and authorization architecture.
004 | Runner isolation model.
005 | Assessment scope enforcement.
006 | Event and job architecture.
007 | Evidence integrity and retention.
008 | AI provider and execution architecture.
009 | Deployment topology.
010 | Observability and audit architecture.
011 | Subscription and usage metering.
012 | API and event versioning.

## 16. Quality gates and release criteria

A running frontend and healthy containers do not establish production readiness. Release decisions must be based on measurable, repeatable evidence.

Area | Release requirement
--- | --- | ---
Authentication | MFA and session tests pass.
Authorization | No unresolved critical access-control defects.
Tenancy | Cross-tenant isolation tests pass.
Runner | Isolation and escape-resistance tests pass.
Scope | Unauthorized targets are rejected.
AI | Tool execution is policy-gated.
Evidence | Integrity checks pass.
Database | Migration and restoration tests pass.
CI | Required tests and security scans pass.
Monitoring | Critical service failures generate alerts.
Recovery | RPO/RTO exercises meet approved targets.
Documentation | Deployment and incident procedures exist.

Require zero unresolved critical or high-severity security defects for production release unless a formally documented exception is approved by the responsible security authority.

### 16.1 Engineering KPIs

- API P95 latency and error rate.
- Worker job success rate and queue latency.
- Assessment completion rate.
- Evidence integrity verification rate.
- Cross-tenant authorization regression count.
- Mean time to recover.
- Vulnerability remediation time.
- Deployment failure rate.

## 17. First production-grade vertical slice

Prove the platform's essential components work together before expanding into the full feature set.

Step | Expected behavior
--- | --- | ---
1. User authenticates | Organization membership and permissions are loaded.
2. User creates engagement | Scope and exclusions are recorded.
3. Engagement receives approval | Authorization and approver are audited.
4. User requests assessment | Policy validates authorization and scope.
5. Worker executes | An isolated runner performs the approved operation.
6. Results are normalized | Findings are stored and associated with assets.
7. Evidence is preserved | Checksums and provenance are recorded.
8. Report is generated | Organization receives a traceable report.

This vertical slice validates identity, tenancy, engagement, policy, queue, runner, findings, evidence and reporting in one end-to-end workflow. It is the recommended first major release milestone.

## 18. Final architectural decisions

Decision area | Recommendation
--- | --- | ---
Product | Security Operations Platform.
Architecture | Modular monolith plus isolated execution services.
Frontend | Next.js and TypeScript.
Backend | FastAPI and Python.
Database | PostgreSQL.
Queue | Redis / ARQ initially.
Object storage | MinIO.
Authentication | OIDC and MFA.
Authorization | RBAC plus resource-level policy engine.
Multi-tenancy | Organization isolation plus RLS where appropriate.
Execution | Ephemeral, isolated runners.
AI | Provider-independent gateway.
Events | Versioned event contracts and transactional outbox.
Observability | Prometheus, Grafana and structured logs.
Deployment | Docker Compose for development; Kubernetes for production.
Commercial model | Community, Professional and Enterprise.

Keep identity, engagements, assets, findings, governance and reporting in a well-structured control-plane application initially. Separate execution, workers and resource-intensive processing because they have different security and scaling requirements.

## 19. Blueprint acceptance checklist

### Architecture

- Document system context and component architecture
- Define domain boundaries and dependency rules
- Create the ADR catalogue
- Document API and event contracts

### Security

- Implement tenant isolation
- Verify RBAC and resource-level authorization
- Harden MFA and session management
- Implement centralized policy enforcement
- Harden runner isolation
- Implement scope validation
- Implement evidence integrity controls

### Core functionality

- Complete asset intelligence
- Complete engagement management
- Complete vulnerability management
- Complete assessment orchestration
- Complete evidence repository
- Complete reporting

### Operations

- Implement incident management
- Implement defensive event ingestion
- Implement AI intelligence controls
- Implement workflow automation
- Implement monitoring and alerting

### Production

- Implement CI security gates
- Test database recovery
- Test runner containment
- Complete load testing
- Complete deployment documentation
- Conduct independent security assessment

## 20. Implementation next steps

The blueprint becomes executable when it is reconciled against the actual repository. Do not treat this target-state document as an instruction to rewrite the entire codebase.

### Recommended execution sequence

Stage | Deliverable
--- | ---
1. Baseline | Inventory every application, package, endpoint, table, integration and deployment.
2. Gap analysis | Map existing implementation against each blueprint component; label implemented, partial, missing, deprecated or unverified.
3. Architecture decisions | Finalize the 12 ADRs with explicit trade-offs and migration consequences.
4. Implementation specification | Define exact files, migrations, interfaces, API contracts and tests.
5. Execution | Create prioritized GitHub issues and small pull requests with clear acceptance criteria.
6. Verification | Run security, integration, regression, recovery and deployment tests.

### Repository-aware implementation deliverables

- Architecture gap analysis: current components versus target architecture.
- Repository restructuring plan: exact files/packages to retain, modify, create or deprecate.
- Database and API specification: migrations, relationships, endpoint contracts and event schemas.
- GitHub implementation backlog: prioritized issues, dependencies, acceptance criteria and security tests.

### Preservation rule

Preserve existing working functionality. Prefer additive migrations and incremental refactoring. No destructive restructuring or staging deployment changes before backups are verified and the current environment is documented.

### Final recommendation

Build Anomaly as a secure, extensible security operations control plane in which asset intelligence, authorized assessments, defensive investigations, AI analysis, evidence and governance operate as one coherent system. Prioritize security correctness, tenant isolation, scope enforcement and execution containment before expanding feature breadth.

---

Document status: Target-state design blueprint • Version 1.0 • 10 November 2026

Prepared from the design requirements discussed in this conversation. Repository-specific implementation status and technical claims require separate source-level verification.
