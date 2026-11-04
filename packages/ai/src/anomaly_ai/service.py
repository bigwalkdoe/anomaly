from __future__ import annotations

from typing import Any

from anomaly_ai.providers import AIMessage, AIProvider, get_provider
from anomaly_core.audit import AuditService
from sqlalchemy.ext.asyncio import AsyncSession


class AIService:
    def __init__(self, provider: AIProvider | None = None, db: AsyncSession | None = None):
        self.provider = provider or get_provider()
        self.db = db

    async def complete(self, messages: list[AIMessage], actor_id=None, engagement_id=None, **kwargs) -> Any:
        resp = await self.provider.complete(messages, **kwargs)
        if self.db is not None:
            try:
                await AuditService.log(
                    actor_id=actor_id,
                    action="ai.complete",
                    resource_type="ai",
                    resource_id=None,
                    engagement_id=engagement_id,
                    metadata={"model": resp.model, "usage": resp.usage},
                    db=self.db,
                )
                await self.db.commit()
            except Exception:
                pass
        return resp

    async def draft_finding(self, run_output: str, **kwargs):
        messages = [
            AIMessage(role="system", content="You are a security analyst. Draft a finding from tool output."),
            AIMessage(role="user", content=run_output),
        ]
        return await self.complete(messages, **kwargs)

    async def draft_report(self, findings_summary: str, **kwargs):
        messages = [
            AIMessage(role="system", content="You are a report writer. Draft an engagement report."),
            AIMessage(role="user", content=findings_summary),
        ]
        return await self.complete(messages, **kwargs)

    async def suggest_tools(self, objective: str, **kwargs):
        messages = [
            AIMessage(role="system", content="Suggest appropriate pentest tools and commands."),
            AIMessage(role="user", content=objective),
        ]
        return await self.complete(messages, **kwargs)
