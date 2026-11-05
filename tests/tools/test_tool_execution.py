import uuid

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models.engagement import Engagement, EngagementMode, Scope, ScopeEntry
from anomaly_core.models.finding import Finding
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.models.user import Role, RoleName, User, UserRole
from anomaly_core.runner import FakeRunner, RunResult
from anomaly_worker.executor import execute_run_inline
from sqlalchemy import func, select

NMAP_XML = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/><address addr="10.0.0.5" addrtype="ipv4"/>
<ports><port protocol="tcp" portid="443"><state state="open"/><service name="https"/></port></ports>
</host></nmaprun>
"""

NUCLEI_JSONL = '{"template-id":"t1","info":{"name":"N1","severity":"medium","description":"d"},"host":"https://x.test","matched-at":"https://x.test/"}\n'


async def _setup(db_session, tool: str, targets: list[str]):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.ADMIN))
    if role is None:
        role = Role(name=RoleName.ADMIN)
        db_session.add(role)
        await db_session.flush()
    user = User(
        email=f"{tool}-{uuid.uuid4().hex[:6]}@x.com", name="A", password_hash=hash_password("pw")
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    eng = Engagement(name=f"E-{tool}", mode=EngagementMode.OWN_INFRA, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    for t in targets:
        db_session.add(ScopeEntry(scope_id=scope.id, kind="in", target_value=t))
    run = Run(
        engagement_id=eng.id,
        user_id=user.id,
        tool=tool,
        target_ids=[],
        params={"targets": targets},
        status=RunStatus.QUEUED,
    )
    db_session.add(run)
    await db_session.commit()
    return eng, run


@pytest.mark.asyncio
async def test_nmap_output_creates_findings(db_session):
    eng, run = await _setup(db_session, "nmap", ["10.0.0.5"])
    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout=NMAP_XML, stderr="", artifacts=[], duration_s=1.0)
    )
    await execute_run_inline(db_session, run.id, runner=runner)
    await db_session.refresh(run)
    assert run.status == RunStatus.SUCCEEDED
    count = await db_session.scalar(
        select(func.count()).select_from(Finding).where(Finding.engagement_id == eng.id)
    )
    assert (count or 0) >= 1
    f = await db_session.scalar(select(Finding).where(Finding.engagement_id == eng.id))
    assert f is not None and "443" in f.title


@pytest.mark.asyncio
async def test_nuclei_output_creates_findings(db_session):
    eng, run = await _setup(db_session, "nuclei", ["https://x.test"])
    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout=NUCLEI_JSONL, stderr="", artifacts=[], duration_s=1.0)
    )
    await execute_run_inline(db_session, run.id, runner=runner)
    await db_session.refresh(run)
    assert run.status == RunStatus.SUCCEEDED
    f = await db_session.scalar(select(Finding).where(Finding.engagement_id == eng.id))
    assert f is not None
    assert f.title == "N1"
    assert f.severity.value == "medium"
