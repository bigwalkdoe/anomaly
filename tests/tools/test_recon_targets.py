import json
import uuid

import pytest
from anomaly_core.auth import hash_password
from anomaly_core.models.engagement import Engagement, EngagementMode, Scope, Target
from anomaly_core.models.run import Run, RunStatus
from anomaly_core.models.user import Role, RoleName, User, UserRole
from anomaly_core.runner import FakeRunner, RunResult
from anomaly_tools.recon import parse_recon_output
from anomaly_worker.executor import execute_run_inline
from sqlalchemy import func, select

SAMPLE = "\n".join(
    [
        json.dumps(
            {"url": "https://app.example.com", "host": "app.example.com", "status_code": 200}
        ),
        json.dumps(
            {"url": "https://api.example.com/health", "host": "api.example.com", "status_code": 200}
        ),
    ]
)


def test_parse_recon_output_discovers_targets():
    result = parse_recon_output(SAMPLE, targets=["example.com"])
    assert len(result.discovered_targets) >= 2
    values = {t["value"] for t in result.discovered_targets}
    assert "https://app.example.com" in values or "app.example.com" in values


@pytest.mark.asyncio
async def test_recon_creates_discovered_targets(db_session):
    role = await db_session.scalar(select(Role).where(Role.name == RoleName.ADMIN))
    if role is None:
        role = Role(name=RoleName.ADMIN)
        db_session.add(role)
        await db_session.flush()
    user = User(
        email=f"recon-{uuid.uuid4().hex[:6]}@x.com", name="A", password_hash=hash_password("pw")
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    eng = Engagement(name="Recon", mode=EngagementMode.OWN_INFRA, owner_id=user.id)
    db_session.add(eng)
    await db_session.flush()
    db_session.add(Scope(engagement_id=eng.id))
    run = Run(
        engagement_id=eng.id,
        user_id=user.id,
        tool="recon",
        target_ids=[],
        params={"targets": ["example.com"]},
        status=RunStatus.QUEUED,
    )
    db_session.add(run)
    await db_session.commit()

    runner = FakeRunner(
        result=RunResult(exit_code=0, stdout=SAMPLE, stderr="", artifacts=[], duration_s=1.0)
    )
    await execute_run_inline(db_session, run.id, runner=runner)
    count = await db_session.scalar(
        select(func.count())
        .select_from(Target)
        .where(Target.engagement_id == eng.id, Target.discovered.is_(True))
    )
    assert (count or 0) >= 2
