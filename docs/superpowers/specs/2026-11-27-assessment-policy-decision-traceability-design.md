# Assessment policy decision traceability design

**Intent:** make every governed assessment request traceable from decision to reason and scope inputs. Today only denials are audited with partial metadata, while allowed requests have no explicit policy decision record and execution manifests hard-code an allowed decision.

**Goals:**
- Record one audit event for each assessment policy evaluation in the API request path, for both allow and deny outcomes.
- Include the decision outcome, reason, operation source, requested targets, and scope result (`in_scope`, `out_of_scope`, `has_warning`).
- Preserve the existing `policy.denied` action for denials so existing consumers keep working.

**Non-goals:**
- Add a new database model for policy decisions.
- Change policy evaluation semantics or approval requirements.
- Rework executor/scheduler audit flows beyond sharing decision metadata formatting.

**Approaches:**
1. **Shared metadata formatter + API recorder (chosen):** add a formatter on `PolicyDecision` in core and a recorder in `apps/api/src/anomaly_api/assessment.py`; wire legacy and v1 run creation. Smallest change that covers API request traceability without new schema.
2. **New `policy_decisions` table:** durable first-class records, but needs migration/API surface and is disproportionate to the bounded traceability gap.
3. **Only enrich denials:** least code, but leaves allowed decisions untraceable and fails the stated goal.

**Design:**
- `PolicyDecision.to_metadata()` returns JSON-safe metadata with `allowed`, `reason`, `op`, and, when a scope result exists, `targets`, `in_scope`, `out_of_scope`, and `has_warning`. Existing decision-specific keys such as `status` are preserved.
- `record_assessment_policy_decision(...)` logs `policy.denied` for denied requests or `policy.allowed` for allowed requests using the shared formatter, with engagement/org context and `source` set by the caller.
- `enforce_assessment_policy(...)` calls the recorder before raising HTTP 403 and accepts an optional `source` (default `assessment.request`).
- Legacy and v1 run creation pass their source identifiers so audit records distinguish request paths.
- Execution manifests continue to use the decision formatter instead of a hard-coded allowed policy decision; scheduler and executor use the same formatter for their existing denial audits.
