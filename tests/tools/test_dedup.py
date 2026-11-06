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

NUCLEI_JSONL = '{"template-id":"dup-t","info":{"name":"Dup","severity":"low"},"host":"https://d.test","matched-at":"https://d.test/"}\n'


async def _setup(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is None:
        role = Role(name=RoleName.admin)
        db_session.add(role)
        await db_session.flush()
    user = User(
        email=f"dup-{uuid.uuid4().hex[:6]}@x.com", name="A", password_hash=hash_password("pw")
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    eng = Engagement(name="Dedup", mode=EngagementMode.own_infra, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    scope = Scope(engagement_id=eng.id)
    db_session.add(scope)
    await db_session.flush()
    db_session.add(ScopeEntry(scope_id=scope.id, kind="in", target_value="https://d.test"))
    await db_session.commit()
    return user, eng


@pytest.mark.asyncio
async def test_duplicate_fingerprint_attaches_not_duplicates(db_session):
    user, eng = await _setup(db_session)
    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout=NUCLEI_JSONL, stderr="", artifacts=[], duration_s=1.0)
    )
    for _ in range(2):
        run = Run(
            engagement_id=eng.id,
            user_id=user.id,
            tool="nuclei",
            target_ids=[],
            params={"targets": ["https://d.test"]},
            status=RunStatus.queued,
        )
        db_session.add(run)
        await db_session.commit()
        await execute_run_inline(db_session, run.id, runner=runner)
    count = await db_session.scalar(
        select(func.count()).select_from(Finding).where(Finding.engagement_id == eng.id)
    )
    assert count == 1
