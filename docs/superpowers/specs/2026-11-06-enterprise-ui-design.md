# Anomaly Enterprise UI — Design Spec

**Date:** 2026-11-06  
**Status:** Draft (pending approval)  
**Scope:** Full `apps/web` product UI (Next.js 15 App Router, React 19, Tailwind 4)

## Intent and why

Anomaly’s current web UI is functionally patched but visually inconsistent and hard to use (“chaos”). The goal is to bring the **entire product** to an **enterprise-production** standard: calm, trustworthy, and efficient for day-to-day security operations (engagements, findings/triage, runs, reports), with the same quality bar applied to auth, settings, and secondary screens.

The product should feel like a professional operator console—comparable in clarity and polish to Cloudflare/Vercel dashboards—while retaining Anomaly’s own identity: **dark charcoal foundations and a cybersecurity aesthetic**, with **professional, technical accents** and unambiguous security signals.

## Goals

- **Enterprise-production quality across the full product:** every route/screen, including loading, empty, error, success, and permission/unauthenticated states.
- **Both light and dark themes from the start**, with a consistent Vercel-like level of clarity and restraint.
- **Anomaly identity:** dark charcoal base in dark mode; cool, disciplined neutrals in light mode; restrained cyber/technical accents used meaningfully (focus, active navigation, key actions/data highlights), never decorative noise.
- **Strong security semantics:** severity (critical/high/medium/low/info), run/status, and scope/warning signals are clear, consistent, and readable in both themes.
- **Maintainable foundation:** a token-first design system on the existing stack so new/updated screens don’t reintroduce inconsistency.
- **Accessibility baseline (production):** keyboard navigability, visible focus states, sufficient color contrast in both themes, semantic structure/labels, and non-color cues where status meaning matters.
- **Preserve behavior and contracts:** existing routes, API contracts, and core data flows remain intact unless a specific UX fix is required for correctness.

## Non-goals

- Rewriting the backend, changing API contracts, or redesigning product features/workflows beyond what’s needed for a coherent, usable UI.
- Adding new product capabilities (e.g., new scanning features) except where minimal UI is required to make existing flows usable (e.g., replacing a broken 404 target with a clear, intentional state).
- Pixel-perfect cloning of Cloudflare or Vercel; they are quality/direction references, not brand sources.
- Building a separate marketing site.

## Anti-goals (what would make this a failure even if it “looks new”)

- A reskinned-but-still-inconsistent UI: pages that look different, use ad-hoc colors/spacing, or bypass the design system.
- Themes that only partially work (dark-only styling hacks, unreadable contrast, severity colors that fail in one theme).
- Cyber aesthetics that reduce clarity (neon overload, low-contrast text, decorative effects harming readability).
- Breaking auth, routing, data loading, or existing user flows while redesigning visuals.
- Inaccessible interactive elements (missing focus, unlabeled controls, color-only status meaning).

## Constraints

- **Stack (fixed):** Next.js 15 (App Router), React 19, Tailwind CSS 4, existing component locations (`components/ui`, `components/layout`, `components/*`), existing routes under `apps/web/app/*`.
- **Backend/API:** FastAPI backend; frontend must continue to work against current API shapes (bearer auth, refresh flow as implemented, existing endpoints). `NEXT_PUBLIC_API_URL` remains the client API base.
- **Current state:** auth/token handling, route guards, and missing-route placeholders were recently fixed for staging; design-system consistency, theming, and production polish remain.
- **Delivery:** full product in scope; work should be executed in a safe, verifiable order (foundation → shell/primitives → screens), but the target is the whole product at the same quality bar.

## Approaches considered

1. **Token-first rebuild on the current stack (chosen).** Define Anomaly design tokens (charcoal surfaces, text/border scales, cyber accent, semantic severity/status) as theme-aware variables; wire into Tailwind 4/global styles; rebuild the app shell and core primitives on those tokens; migrate every screen and state to the system. *Tradeoff:* more upfront foundation work, but it removes inconsistency at the source and makes full light/dark coverage reliable.
2. **Token foundation + adopt proven accessible component patterns for complex primitives (incorporated into #1 where helpful).** Use established, accessible patterns/implementations for tricky interactions (dialogs, menus/selects, focus management) while styling them to Anomaly. *Tradeoff:* faster/safer for accessibility on complex widgets; requires discipline to keep visuals cohesive.
3. **Screen-by-screen reskin without rebuilding the foundation (rejected).** *Tradeoff:* fastest visual change, but preserves underlying chaos and makes robust dual-theme enterprise quality unlikely.

**Decision:** Approach **1**, incorporating proven accessible patterns from **2** for complex primitives where they reduce risk.

## Design (how)

### 1) Visual identity and tokens

- **Themes:** `light` and `dark`, user-selectable, persisted; respect system preference as default (implementation detail). Theme implemented via class/data attribute on the root (compatible with Tailwind 4 + CSS variables).
- **Dark (primary character):** deep charcoal/graphite layered surfaces (background, raised, overlay), high-legibility foreground, subtle borders; avoid pure black/harsh contrast.
- **Light:** cool, disciplined neutrals (not warm/beige), matching structure and hierarchy to dark.
- **Cyber/technical accent (professional, restrained):** a cool technical accent family (e.g., cyan/blue spectrum) for focus rings, active nav, primary actions/links, and selected states—used sparingly. Accent must meet contrast requirements and never compete with severity.
- **Semantic colors (meaningful, consistent in both themes):** severity `critical | high | medium | low | info`; statuses for runs/findings/engagements; `warning` (scope), `success`, `destructive`. Each has foreground/background/border treatments that pass contrast and include non-color cues (labels/icons/badges) where appropriate.
- **Typography/spacing/radius/shadows:** a restrained scale aligned with Vercel-like clarity (readable type, consistent spacing rhythm, subtle radii/elevation). Use system/Inter (already present) unless a change is justified; keep it consistent.
- **Token delivery:** CSS custom properties in `globals.css` (or theme files) mapped into Tailwind 4 theme utilities so components use semantic classes/tokens, not hardcoded hex values (except controlled token definitions).

### 2) App shell and navigation

- A consistent, production shell for authenticated areas: clear hierarchy (workspace/context → page → content), responsive sidebar/top navigation behavior, obvious active state, accessible keyboard/focus, and theme toggle placement.
- Navigation reflects the full product IA (dashboard, engagements, findings, runs, reports, playbooks, schedules, settings/auth-related surfaces) with consistent treatment for primary vs secondary items.
- Preserve `RequireAuth`/auth flows; sign-out and session states remain correct. Public/auth pages (login/register) share the same identity/system.

### 3) Core primitives (design system layer)

Rebuild/normalize primitives in `components/ui` (and supporting layout components) on tokens:
- Buttons, links-as-actions, inputs, selects, textareas, labels, form messages
- Cards/surfaces, badges/pills (including severity/status variants), tables, pagination/empty/loading patterns
- Dialogs/drawers/menus/popovers where used (accessible focus management)
- Toasts/inline alerts for feedback
- Page headers, section headers, stat/metric displays, skeletons

All primitives: theme-aware, keyboard/focus-visible, consistent spacing/typography, and reusable.

### 4) Full-screen migration (all routes)

Bring every screen to the same bar using the primitives/tokens:
- **Auth:** login, register (and related states/errors)
- **Dashboard:** real-data presentation patterns, clear metrics, recent activity areas with proper states
- **Engagements:** list, detail, create/placeholder flows as applicable
- **Findings:** list/triage views, detail/placeholder, severity-first readability
- **Runs:** list, detail/placeholder, status/log-oriented clarity
- **Reports:** generation/view flows and feedback
- **Playbooks, Schedules:** list/create placeholders or implemented flows, consistent states
- **Settings:** clear, intentional layout (even if feature-light)
- **Global:** 404/not-found, error boundaries/states where present, responsive behavior

For each screen: coherent layout, correct data/loading/empty/error/forbidden handling, no dead-end broken links, and consistent severity/status rendering.

### 5) Accessibility and quality

- Visible focus rings (accent-aligned, contrast-safe) on all interactive elements.
- Labels/ARIA where needed; semantic headings and landmarks in the shell.
- Contrast checked for text, UI boundaries, and severity/status in **both** themes (builder to verify).
- Avoid color-only meaning for critical states.
- Keep interactions predictable (no disruptive motion; respect reduced-motion if added—sensible default).

### 6) Verification

- `npx tsc --noEmit` and `next build` pass.
- Manual smoke of key flows in both themes: sign-in → dashboard → engagements → findings → runs → reports → sign-out; confirm guards/redirects.
- Visual/contrast sanity pass on severity/status and primary surfaces in light and dark.

## My calls (sensible defaults, stated plainly)

- **Theme mechanism:** CSS-variable tokens + Tailwind 4 theme mapping + a small, standard theme toggle/provider approach compatible with Next 15 App Router (builder to pick the lightest-weight reliable implementation; avoid unnecessary dependencies).
- **Accent hue:** a restrained cyan/technical accent family as shown in the approved direction, tuned for contrast in both themes.
- **Responsive behavior:** desktop-first operator workflows with solid tablet/narrow support; no separate mobile app design.
- **Motion:** minimal and purposeful; no gratuitous animation.
- **Copy/IA:** keep existing labels/routes; clarify microcopy only where it improves usability/correctness.

## Open questions / left to the builder

- Exact token values (hex/oklch), spacing/radius scale, and final accent tuning—**must** satisfy contrast and the approved charcoal/cyber, Vercel-like direction in both themes.
- Best-fit accessible primitive implementations already compatible with the repo (use existing Radix deps where present/pattern fits) vs lightweight in-house patterns for simple cases.
- Whether any screen needs minor IA restructuring to eliminate confusion (builder may propose small, behavior-preserving UX fixes; flag anything that changes meaning/workflow).
- Performance details (code splitting, avoiding heavy client bundles) consistent with Next 15 best practices.

## Risks

- **Scope size:** full-product, dual-theme redesign is large; mitigate by token/shell/primitives first, then systematic screen migration with frequent verification.
- **Contrast regressions:** severity + charcoal + accents can fail contrast; mitigate with token-level checks in both themes.
- **Behavior regressions:** refactoring shared layout/components can break flows; mitigate by preserving contracts, keeping auth/data logic stable, and smoke-testing core paths.
- **Tailwind 4/theming integration details:** builder must align token strategy with the project’s Tailwind 4 setup.

## Out of scope for this doc

- Backend/API changes, new security features, deployment topology changes (beyond the already-running containers), and non-web clients.
