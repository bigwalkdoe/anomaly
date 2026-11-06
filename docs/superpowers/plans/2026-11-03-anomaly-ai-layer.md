# Anomaly AI Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provider-agnostic LLM layer with Ollama/OpenAI/Anthropic support, finding/report drafting, tool suggestion, and audit logging of all AI calls.

**Architecture:** Create `packages/ai` with provider interface, prompts, and services. Every AI call logged via AuditService. Human approval required for destructive actions on client scope.

**Tech Stack:** Python 3.12, httpx, pydantic v2

**Spec:** `docs/superpowers/specs/2026-11-03-anomaly-design.md`
