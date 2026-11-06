# Anomaly CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Typer CLI sharing schemas with API, commands for auth, engagements, runs, findings, reports, sync, config.

**Architecture:** Create `apps/cli` with Typer app, HTTP client using httpx, config via env/file.

**Tech Stack:** Python 3.12, typer, rich, httpx
