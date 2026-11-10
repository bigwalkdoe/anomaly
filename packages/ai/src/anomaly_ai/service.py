from __future__ import annotations

import json
import re
from typing import Any

from anomaly_core.audit import AuditService
from anomaly_tools.registry import get_default_registry
from sqlalchemy.ext.asyncio import AsyncSession

from anomaly_ai.providers import AIMessage, AIProvider, AIResponse, get_provider


def _truncate(text: str | None, limit: int = 4096) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _extract_json(text: str) -> Any:
    # Try fenced block first
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return json.loads(fence.group(1))
    # Try raw object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


def _normalize_suggestion(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "tool": str(item),
            "reason": "",
            "targets_hint": "",
            "params": {},
            "priority": "medium",
        }
    return {
        "tool": str(item.get("tool", "")).strip(),
        "reason": str(item.get("reason", "") or ""),
        "targets_hint": str(item.get("targets_hint", "") or ""),
        "params": item.get("params") if isinstance(item.get("params"), dict) else {},
        "priority": str(item.get("priority", "medium") or "medium"),
    }


class AIService:
    def __init__(self, provider: AIProvider | None = None, db: AsyncSession | None = None):
        self.provider = provider or get_provider()
        self.db = db

    async def complete(
        self, messages: list[AIMessage], actor_id=None, engagement_id=None, **kwargs
    ) -> AIResponse:
        resp = await self.provider.complete(messages, **kwargs)
        if self.db is not None:
            try:
                await AuditService.log(
                    actor_id=actor_id,
                    action="ai.complete",
                    resource_type="ai",
                    resource_id=None,
                    engagement_id=engagement_id,
                    metadata={
                        "model": resp.model,
                        "usage": resp.usage,
                        "provider": getattr(self.provider, "name", None),
                    },
                    db=self.db,
                )
                await self.db.commit()
            except Exception:
                pass
        return resp

    async def draft_finding(self, run_output: str, **kwargs):
        messages = [
            AIMessage(
                role="system",
                content="You are a security analyst. Draft a finding from tool output.",
            ),
            AIMessage(role="user", content=run_output),
        ]
        return await self.complete(messages, **kwargs)

    async def draft_report(self, findings_summary: str, **kwargs):
        messages = [
            AIMessage(
                role="system", content="You are a report writer. Draft an engagement report."
            ),
            AIMessage(role="user", content=findings_summary),
        ]
        return await self.complete(messages, **kwargs)

    async def suggest_tools(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
        actor_id=None,
        engagement_id=None,
        **kwargs,
    ) -> dict[str, Any]:
        registry = get_default_registry()
        tools = registry.list_tools()
        tool_lines = []
        for name in tools:
            t = registry.get(name)
            supported = getattr(t, "supported_target_types", []) if t else []
            tool_lines.append(f"- {name} (targets: {', '.join(supported) if supported else 'any'})")
        tools_block = "\n".join(tool_lines) if tool_lines else "- (none)"

        schema = (
            '{"suggestions":[{"tool":"...","reason":"...","targets_hint":"...",'
            '"params":{},"priority":"low|medium|high"}],"notes":"..."}'
        )
        system = (
            "You are a penetration testing assistant. Suggest appropriate tools and next steps. "
            "Only suggest tools from the available list. "
            "Return ONLY valid JSON matching this schema (no extra text):\n"
            f"{schema}\n\nAvailable tools:\n{tools_block}"
        )
        user_parts = [f"Objective: {objective}"]
        if context:
            try:
                user_parts.append("Context: " + json.dumps(context, default=str))
            except Exception:
                user_parts.append(f"Context: {context!r}")
        messages = [
            AIMessage(role="system", content=system),
            AIMessage(role="user", content="\n".join(user_parts)),
        ]

        resp = await self.complete(
            messages, actor_id=actor_id, engagement_id=engagement_id, **kwargs
        )
        provider_name = getattr(self.provider, "name", None) or "unknown"
        raw_text = resp.content or ""
        parse_success = False
        suggestions: list[dict[str, Any]] = []
        notes: str | None = None
        try:
            parsed = _extract_json(raw_text)
            if isinstance(parsed, dict):
                items = parsed.get("suggestions") or []
                if isinstance(items, list):
                    suggestions = [_normalize_suggestion(x) for x in items]
                    notes_val = parsed.get("notes")
                    notes = str(notes_val) if notes_val is not None else None
                    parse_success = True
        except Exception:
            parse_success = False
            suggestions = []
            notes = None

        result = {
            "provider": provider_name,
            "model": resp.model,
            "suggestions": suggestions if parse_success else [],
            "notes": notes if parse_success else None,
            "raw": None if parse_success else raw_text,
            "parse_success": parse_success,
            "usage": resp.usage or {"prompt_tokens": 0, "completion_tokens": 0},
        }

        if self.db is not None:
            try:
                prompt_text = "\n".join(m.content for m in messages)
                await AuditService.log(
                    actor_id=actor_id,
                    action="ai.suggest_tools",
                    resource_type="ai",
                    resource_id=None,
                    engagement_id=engagement_id,
                    metadata={
                        "provider": provider_name,
                        "model": resp.model,
                        "usage": resp.usage,
                        "objective_len": len(objective or ""),
                        "parse_success": parse_success,
                        "suggestion_count": len(result["suggestions"]),
                        "prompt": _truncate(prompt_text),
                        "response": _truncate(raw_text),
                    },
                    db=self.db,
                )
                await self.db.commit()
            except Exception:
                pass

        return result
