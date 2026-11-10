from __future__ import annotations

import uuid

from anomaly_reporting import ReportGenerator


def test_report_is_traceable_to_org_engagement_job_execution_evidence():
    """Review Focus #5: report must be traceable.

    Trace to org/engagement/job/execution/findings/evidence.
    """
    org_id = str(uuid.uuid4())
    eng_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    ev_sha = "a" * 64
    findings = [
        {
            "title": "F",
            "severity": "low",
            "description": "d",
            "status": "new",
            "remediation": "",
            "run_id": run_id,
            "evidence_sha256": ev_sha,
        }
    ]
    gen = ReportGenerator()
    # Expect traceability-aware API (may accept context/metadata)
    try:
        content = gen.generate_markdown(
            "Eng",
            findings,
            context={
                "organization_id": org_id,
                "engagement_id": eng_id,
                "job_id": run_id,
                "execution_id": run_id,
            },
        )
    except TypeError:
        content = gen.generate_markdown("Eng", findings)
    assert org_id in content
    assert eng_id in content
    assert run_id in content
    assert ev_sha in content or "sha256" in content.lower()
