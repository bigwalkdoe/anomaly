from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from anomaly_core.audit import AuditService
from anomaly_core.execution import validate_execution_manifest
from anomaly_core.findings import finding_fingerprint
from anomaly_core.models import (
    Engagement,
    Evidence,
    EvidenceType,
    Finding,
    FindingSeverity,
    Run,
    RunStatus,
    Scope,
    Target,
)
from anomaly_core.policy import evaluate_assessment_request
from anomaly_core.runner import DockerRunner, FakeRunner, RunResult, RunSpec
from anomaly_core.scope import check_scope
from anomaly_tools import ToolSpec as AnomalyToolSpec
from anomaly_tools import get_default_registry
from anomaly_tools.stub import stub_tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

MAX_TARGETS_PER_RUN = 256
MAX_EVIDENCE_TEXT_BYTES = 256 * 1024
MAX_ARTIFACTS_PER_RUN = 100
DEFAULT_RUN_TIMEOUT_S = 300
DEFAULT_RESOURCE_LIMITS = {"mem_limit": "512m", "pids_limit": 256}
TOOL_RESOURCE_PROFILES: dict[str, dict[str, Any]] = {
    "nmap": {"mem_limit": "512m", "pids_limit": 256, "cpu_quota": 100000},
    "masscan": {"mem_limit": "512m", "pids_limit": 256, "cpu_quota": 100000},
    "nuclei": {"mem_limit": "768m", "pids_limit": 512, "cpu_quota": 100000},
    "sqlmap": {"mem_limit": "512m", "pids_limit": 256, "cpu_quota": 100000},
    "ffuf": {"mem_limit": "512m", "pids_limit": 512, "cpu_quota": 100000},
}


def _targets_from_run(run: Run) -> list[str]:
    params = run.params if isinstance(run.params, dict) else {}
    targets = params.get("targets")
    if isinstance(targets, list):
        return [str(t) for t in targets]
    if isinstance(targets, str) and targets:
        return [targets]
    return []


def _tool_params(run: Run) -> dict[str, Any]:
    params = run.params if isinstance(run.params, dict) else {}
    return {k: v for k, v in params.items() if k != "targets"}


def _scope_target_value(value: str) -> str:
    """Reduce a discovered URL to its hostname for scope comparison."""
    parsed = urlparse(str(value))
    return parsed.hostname or str(value)


def _severity(value: str) -> FindingSeverity:
    try:
        return FindingSeverity(str(value))
    except Exception:
        return FindingSeverity.info


async def execute_run(db: AsyncSession, run_id: UUID, runner: Any = None) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise ValueError("Run not found")
    run.status = RunStatus.running
    await db.flush()

    # Load engagement + scope for scope checks (foundation contract).
    try:
        res = await db.execute(
            select(Engagement)
            .options(selectinload(Engagement.scope).selectinload(Scope.entries))
            .where(Engagement.id == run.engagement_id)
        )
        engagement = res.scalar_one()
    except Exception:
        engagement = await db.get(Engagement, run.engagement_id)

    targets = _targets_from_run(run)
    if len(targets) > MAX_TARGETS_PER_RUN:
        run.status = RunStatus.failed
        await AuditService.log(
            actor_id=run.user_id,
            action="policy.denied",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(run, "organization_id", None),
            metadata={
                "reason": "too_many_targets",
                "target_count": len(targets),
                "max_targets": MAX_TARGETS_PER_RUN,
                "op": "assessment.execute",
            },
            db=db,
        )
        await db.commit()
        await db.refresh(run)
        return run
    if engagement is None:
        run.status = RunStatus.failed
        await AuditService.log(
            actor_id=run.user_id,
            action="policy.denied",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(run, "organization_id", None),
            metadata={"reason": "engagement_not_found", "op": "assessment.execute"},
            db=db,
        )
        await db.commit()
        await db.refresh(run)
        return run

    decision = evaluate_assessment_request(engagement, targets, scope_engagement=engagement)
    if not decision.allowed:
        run.status = RunStatus.failed
        await AuditService.log(
            actor_id=run.user_id,
            action="policy.denied",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata=decision.to_metadata(op="assessment.execute"),
            db=db,
        )
        await db.commit()
        await db.refresh(run)
        return run

    run_params = run.params if isinstance(run.params, dict) else {}
    manifest = run_params.get("execution_manifest")
    if manifest is not None:
        ok, reason = validate_execution_manifest(manifest)
        if not ok:
            run.status = RunStatus.failed
            await AuditService.log(
                actor_id=run.user_id,
                action="policy.denied",
                resource_type="run",
                resource_id=run.id,
                engagement_id=run.engagement_id,
                organization_id=getattr(engagement, "organization_id", None),
                metadata={"reason": f"invalid_manifest:{reason}", "op": "assessment.execute"},
                db=db,
            )
            await db.commit()
            await db.refresh(run)
            return run
        m_eng = str(manifest.get("engagement_id") or "")
        m_run = str(manifest.get("run_id") or "")
        m_org = manifest.get("organization_id")
        eng_org = getattr(engagement, "organization_id", None)
        if m_eng != str(run.engagement_id) or m_run != str(run.id):
            run.status = RunStatus.failed
            await AuditService.log(
                actor_id=run.user_id,
                action="policy.denied",
                resource_type="run",
                resource_id=run.id,
                engagement_id=run.engagement_id,
                organization_id=getattr(engagement, "organization_id", None),
                metadata={"reason": "manifest_mismatch", "op": "assessment.execute"},
                db=db,
            )
            await db.commit()
            await db.refresh(run)
            return run
        if (eng_org is None and m_org is not None) or (
            eng_org is not None and str(eng_org) != str(m_org)
        ):
            run.status = RunStatus.failed
            await AuditService.log(
                actor_id=run.user_id,
                action="policy.denied",
                resource_type="run",
                resource_id=run.id,
                engagement_id=run.engagement_id,
                organization_id=getattr(engagement, "organization_id", None),
                metadata={"reason": "manifest_org_mismatch", "op": "assessment.execute"},
                db=db,
            )
            await db.commit()
            await db.refresh(run)
            return run

    result = decision.scope_result
    if result and result.has_warning:
        run.scope_warning = True
        await AuditService.log(
            actor_id=run.user_id,
            action="scope.warning",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"out_of_scope": result.out_of_scope},
            db=db,
        )

    tool_params = _tool_params(run)
    # Log when risky options were explicitly requested (sqlmap safety).
    if tool_params.get("allow_risky_options"):
        await AuditService.log(
            actor_id=run.user_id,
            action="tool.risky_options",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"tool": run.tool, "params": tool_params},
            db=db,
        )

    if runner is None:
        runner_mode = os.environ.get("ANOMALY_RUNNER", "fake").lower()
        runner = DockerRunner() if runner_mode == "docker" else FakeRunner()

    registry = get_default_registry()
    tool = registry.get(run.tool)

    tool_image = f"anomaly-tools-{run.tool}:dev" if run.tool != "stub" else "anomaly-runner:dev"
    command: list[str] | None = None
    if tool is not None:
        spec = AnomalyToolSpec(
            targets=targets,
            params=tool_params,
            engagement_id=str(run.engagement_id),
        )
        try:
            command = tool.build_cmd(spec)
        except Exception:
            command = None

    resource_limits = dict(DEFAULT_RESOURCE_LIMITS)
    resource_limits.update(TOOL_RESOURCE_PROFILES.get(run.tool, {}))
    network = os.environ.get("ANOMALY_RUNNER_NETWORK", "none").strip() or "none"
    if network != "none":
        await AuditService.log(
            actor_id=run.user_id,
            action="runner.network_override",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"tool": run.tool, "network": network},
            db=db,
        )
    run_spec = RunSpec(
        tool=run.tool,
        image=tool_image,
        target_values=targets,
        params=tool_params,
        command=command,
        timeout_s=DEFAULT_RUN_TIMEOUT_S,
        network=network,
        resource_limits=resource_limits,
    )
    try:
        runner_result = await asyncio.wait_for(
            runner.run(run_spec), timeout=run_spec.timeout_s + 10
        )
    except TimeoutError:
        runner_result = RunResult(exit_code=124, stdout="", stderr="Execution timed out")
        await AuditService.log(
            actor_id=run.user_id,
            action="run.timeout",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"tool": run.tool, "timeout_s": run_spec.timeout_s},
            db=db,
        )

    stdout = getattr(runner_result, "stdout", "") or ""
    stderr = getattr(runner_result, "stderr", "") or ""
    exit_code = getattr(runner_result, "exit_code", 0)
    if exit_code == 125:
        await AuditService.log(
            actor_id=run.user_id,
            action="runner.execution_error",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"tool": run.tool, "exit_code": exit_code, "stderr": stderr[:500]},
            db=db,
        )
    artifacts = list(getattr(runner_result, "artifacts", []) or [])
    artifacts_truncated = len(artifacts) > MAX_ARTIFACTS_PER_RUN
    if artifacts_truncated:
        artifacts = artifacts[:MAX_ARTIFACTS_PER_RUN]
        await AuditService.log(
            actor_id=run.user_id,
            action="artifact.quota_exceeded",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={"max_artifacts": MAX_ARTIFACTS_PER_RUN, "tool": run.tool},
            db=db,
        )
    log_bytes = (stdout + "\n" + stderr).encode("utf-8", errors="replace")
    sha = hashlib.sha256(log_bytes).hexdigest()
    stdout_stored = stdout.encode("utf-8", errors="replace")[:MAX_EVIDENCE_TEXT_BYTES].decode(
        "utf-8", errors="replace"
    )
    stderr_stored = stderr.encode("utf-8", errors="replace")[:MAX_EVIDENCE_TEXT_BYTES].decode(
        "utf-8", errors="replace"
    )
    org_id = getattr(engagement, "organization_id", None) if engagement is not None else None
    ev = Evidence(
        run_id=run.id,
        engagement_id=run.engagement_id,
        organization_id=org_id,
        type=EvidenceType.log,
        storage_key=f"logs/{run.id}.txt",
        sha256=sha,
        collector="worker",
        tool=run.tool,
        tool_version=getattr(runner_result, "tool_version", None),
        metadata={
            "stdout": stdout_stored,
            "stderr": stderr_stored,
            "stdout_truncated": len(stdout.encode("utf-8", errors="replace"))
            > MAX_EVIDENCE_TEXT_BYTES,
            "stderr_truncated": len(stderr.encode("utf-8", errors="replace"))
            > MAX_EVIDENCE_TEXT_BYTES,
            "exit_code": getattr(runner_result, "exit_code", 0),
            "sha256": sha,
            "artifact_count": len(artifacts),
            "artifacts_truncated": artifacts_truncated,
            "organization_id": str(org_id) if org_id else None,
            "engagement_id": str(run.engagement_id),
            "run_id": str(run.id),
            "collector": "worker",
            "tool": run.tool,
        },
    )
    db.add(ev)

    # Parse findings via tool wrapper when available; fallback to legacy stub_tool.
    finding_drafts = []
    discovered: list[dict[str, Any]] = []
    parsed = None
    if tool is not None:
        parse_input = stdout
        if run.tool == "stub" and not parse_input.strip() and targets:
            parse_input = f"stub reached {targets[0]}"
        try:
            parsed = tool.parse(parse_input)
        except TypeError:
            try:
                parsed = tool.parse(parse_input, targets, tool_params)  # type: ignore[call-arg]
            except Exception:
                parsed = None
        except Exception:
            parsed = None
        if parsed is not None:
            pf = getattr(parsed, "parsed_findings", None)
            finding_drafts = list(pf) if pf else list(getattr(parsed, "findings", []) or [])
            discovered = list(getattr(parsed, "discovered_targets", []) or [])
    if not finding_drafts and run.tool == "stub":
        legacy = stub_tool(targets=targets)
        for f in getattr(legacy, "findings", []) or []:
            if isinstance(f, dict):
                finding_drafts.append(f)
    if not finding_drafts and tool is None:
        legacy = stub_tool(targets=targets)
        for f in getattr(legacy, "findings", []) or []:
            if isinstance(f, dict):
                finding_drafts.append(f)

    # Create discovered targets (idempotent), but never register out-of-scope values.
    rejected_discovered: list[str] = []
    for t in discovered:
        value = str(t.get("value") or "").strip()
        if not value:
            continue
        if check_scope(engagement, [_scope_target_value(value)]).out_of_scope:
            rejected_discovered.append(value)
            continue
        ttype = str(t.get("type") or "domain")
        exists = await db.scalar(
            select(Target).where(
                Target.engagement_id == run.engagement_id,
                Target.value == value,
                Target.type == ttype,
            )
        )
        if exists is None:
            db.add(
                Target(
                    engagement_id=run.engagement_id,
                    value=value,
                    type=ttype,
                    status=str(t.get("status") or "discovered"),
                    discovered=bool(t.get("discovered", True)),
                )
            )
    if rejected_discovered:
        await AuditService.log(
            actor_id=run.user_id,
            action="scope.discovered_rejected",
            resource_type="run",
            resource_id=run.id,
            engagement_id=run.engagement_id,
            organization_id=getattr(engagement, "organization_id", None),
            metadata={
                "out_of_scope": rejected_discovered,
                "op": "assessment.execute",
            },
            db=db,
        )

    engagement_targets = (
        await db.scalars(select(Target).where(Target.engagement_id == run.engagement_id))
    ).all()
    target_by_value = {str(t.value): t.id for t in engagement_targets}

    for f in finding_drafts:
        target_id = None
        if isinstance(f, dict):
            title = f.get("title", "Stub finding: target reachable")
            severity = _severity(f.get("severity", "info"))
            description = f.get("description", "") or ""
            remediation = f.get("remediation")
            cvss = f.get("cvss")
            tval = f.get("target") or f.get("host") or f.get("url")
            fp = f.get("fingerprint") or finding_fingerprint(
                run.engagement_id, title, description, str(tval) if tval else None
            )
            if tval is not None and str(tval) in target_by_value:
                target_id = target_by_value[str(tval)]
        else:
            title = getattr(f, "title", "Finding")
            severity = _severity(getattr(f, "severity", "info"))
            description = getattr(f, "description", "") or ""
            remediation = getattr(f, "remediation", None)
            cvss = getattr(f, "cvss", None)
            meta = getattr(f, "metadata", {}) or {}
            tval = getattr(f, "target", None) or meta.get("target")
            fp = (
                getattr(f, "fingerprint", None)
                or meta.get("fingerprint")
                or finding_fingerprint(
                    run.engagement_id, title, description, str(tval) if tval else None
                )
            )
            tval = meta.get("target") or meta.get("host") or meta.get("url")
            if tval is not None and str(tval) in target_by_value:
                target_id = target_by_value[str(tval)]

        # Dedup/attach by (engagement_id, fingerprint)
        existing = await db.scalar(
            select(Finding).where(
                Finding.engagement_id == run.engagement_id,
                Finding.fingerprint == str(fp),
            )
        )
        if existing is not None:
            continue
        finding = Finding(
            organization_id=getattr(engagement, "organization_id", None),
            engagement_id=run.engagement_id,
            target_id=target_id,
            title=title,
            severity=severity,
            description=description,
            remediation=remediation,
            cvss=cvss,
            reporter_id=run.user_id,
            fingerprint=str(fp),
        )
        db.add(finding)

    exit_code = getattr(runner_result, "exit_code", 0)
    run.status = RunStatus.succeeded if exit_code == 0 else RunStatus.failed
    await AuditService.log(
        actor_id=run.user_id,
        action="run.complete",
        resource_type="run",
        resource_id=run.id,
        engagement_id=run.engagement_id,
        organization_id=getattr(engagement, "organization_id", None),
        metadata={"status": run.status.value, "tool": run.tool},
        db=db,
    )
    await db.commit()
    await db.refresh(run)
    return run


async def execute_run_inline(db, run_id, runner=None):
    """Compat alias for tool-pack tests."""
    return await execute_run(db, run_id, runner)
