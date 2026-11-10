from __future__ import annotations

import hashlib
import uuid

import pytest
from anomaly_core.models import Evidence, EvidenceType


@pytest.mark.asyncio
async def test_evidence_integrity_checksum_and_provenance(db_session):
    """Review Focus #4: evidence must have SHA-256 checksum and provenance."""
    payload = b"artifact-bytes"
    sha = hashlib.sha256(payload).hexdigest()
    ev = Evidence(
        type=EvidenceType.log,
        storage_key="logs/test.txt",
        metadata={
            "sha256": sha,
            "organization_id": str(uuid.uuid4()),
            "engagement_id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "collector": "test",
            "tool": "stub",
        },
    )
    db_session.add(ev)
    await db_session.commit()
    await db_session.refresh(ev)
    meta = ev.metadata or {}
    assert meta.get("sha256") == sha
    assert meta.get("organization_id")
    assert meta.get("engagement_id")
    assert meta.get("run_id")
