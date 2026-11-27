from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from anomaly_core.models import Approval, ApprovalStatus, Engagement, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

APPROVAL_RESOURCE_TYPE = "engagement"


async def record_approval_request(
    db: AsyncSession, engagement: Engagement, requester: User
) -> Approval:
    """Reuse or create the pending governance record for an engagement submission."""
    approval = await db.scalar(
        select(Approval)
        .where(
            Approval.engagement_id == engagement.id,
            Approval.resource_type == APPROVAL_RESOURCE_TYPE,
            Approval.resource_id == engagement.id,
            Approval.status == ApprovalStatus.pending,
        )
        .order_by(Approval.created_at.desc())
    )
    if approval is not None:
        return approval

    approval = Approval(
        organization_id=engagement.organization_id,
        engagement_id=engagement.id,
        resource_type=APPROVAL_RESOURCE_TYPE,
        resource_id=engagement.id,
        requester_id=requester.id,
        status=ApprovalStatus.pending,
    )
    db.add(approval)
    await db.flush()
    return approval


async def record_approval_decision(
    db: AsyncSession, engagement: Engagement, approver: User
) -> Approval:
    """Record an approved governance decision, including direct approvals without a submit."""
    approval = await record_approval_request(db, engagement, approver)
    approval.status = ApprovalStatus.approved
    approval.approver_id = approver.id
    approval.decided_at = datetime.now(UTC)
    await db.flush()
    return approval


def approval_response(approval: Approval) -> dict[str, Any]:
    return {
        "id": str(approval.id),
        "organization_id": str(approval.organization_id) if approval.organization_id else None,
        "engagement_id": str(approval.engagement_id) if approval.engagement_id else None,
        "resource_type": approval.resource_type,
        "resource_id": str(approval.resource_id) if approval.resource_id else None,
        "status": approval.status.value,
        "requester_id": str(approval.requester_id),
        "approver_id": str(approval.approver_id) if approval.approver_id else None,
        "reason": approval.reason,
        "created_at": approval.created_at.isoformat(),
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
