# Anomaly Enterprise UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the entire `apps/web` product UI to an enterprise-production standard with a Vercel-like level of clarity, a dark-charcoal cybersecurity identity, restrained professional cyber/technical accents, and full light/dark theme support across every screen and state.

**Architecture:** Token-first rebuild on the existing Next.js 15 App Router + React 19 + Tailwind 4 stack. Replace the current hand-rolled `app/globals.css` utility dump with a properly wired Tailwind 4 pipeline (`postcss.config.mjs`, `@import "tailwindcss"`, `@custom-variant dark`, CSS-variable semantic tokens mapped via `@theme inline`), add a lightweight class-based theme system, rebuild the app shell and `components/ui` primitives on semantic tokens, then migrate every route to the system while preserving API contracts, auth/route-guard behavior, and existing data flows.

**Tech Stack:** Next.js 15.0.0 (App Router), React 19, TypeScript, Tailwind CSS 4 + `@tailwindcss/postcss` + `tailwindcss-animate` (already in deps), Radix primitives already present (`@radix-ui/react-*`), `clsx` + `tailwind-merge` via `lib/utils.ts`, lucide icons via `components/ui/icons.tsx`.

**Spec:** `docs/superpowers/specs/2026-11-06-enterprise-ui-design.md` (approved). The plan argues from the spec; executors read both.

## Global Constraints

- **Full product scope:** all routes under `apps/web/app/*` (auth, dashboard, engagements + detail/new, findings + detail, runs + detail/new, reports, playbooks + new, schedules + new, settings) brought to the same production bar.
- **Both themes required:** `light` and `dark`, class-based (`.dark` on `<html>`), persisted, system preference as default. No dark-only hacks; no unreadable contrast in either theme.
- **Identity (from spec):** Vercel-like clarity/restraint; dark charcoal foundation (deep graphite layered surfaces, not pure black) in dark mode; cool disciplined neutrals in light mode; restrained cyber/technical accent (cyan/blue spectrum) for focus/active/primary emphasis only; semantic severity/status colors meaningful and consistent in both themes.
- **Preserve behavior/contracts:** routes, `NEXT_PUBLIC_API_URL` client API base, bearer + refresh auth flow (`lib/api.ts`), `RequireAuth` guards, login `?next` redirect, and existing data-loading patterns remain intact unless a targeted UX fix is required for correctness.
- **Accessibility baseline:** keyboard navigability, visible focus rings, semantic labels/landmarks/headings where appropriate, sufficient contrast in both themes, and non-color cues for severity/status meaning.
- **Semantic tokens, not ad-hoc hex in components:** define tokens in `app/globals.css`; components use semantic utility classes (existing names like `bg-background`, `text-foreground`, `text-muted-foreground`, `bg-primary`, `text-primary-foreground`, `border-input`, `bg-card`, `bg-accent`, `ring-ring`, `bg-destructive`, etc., plus new severity/status tokens). Hardcoded palette classes in feature code (e.g., `bg-red-100 text-red-800` for severity) are replaced by semantic severity/status variants.
- **Verification gate (every task that changes UI/build):** `cd apps/web && npx tsc --noEmit` and `NEXT_TELEMETRY_DISABLED=1 npm run build` pass. Manual smoke in both themes for affected flows before considering a screen task done.
- **No new heavy dependencies** unless clearly justified; prefer existing Radix deps and lightweight in-repo patterns.

## Review Focus

1. **Tailwind v4 not actually applied / token classes missing** — symptoms: pages render unstyled or with wrong colors after replacing globals; `bg-primary`, `border-input`, `ring-ring` resolve incorrectly. A reasonable person expects the app to look styled and themed after build. Pin by: `postcss.config.mjs` exists with `@tailwindcss/postcss`, `globals.css` starts with `@import "tailwindcss"` and `@custom-variant dark (&:where(.dark, .dark *))`, build succeeds, and token classes render in both themes.
2. **Theme flash / hydration mismatch** — loading a page in dark mode briefly flashes light (or errors). A reasonable person expects the chosen theme to apply before content paints. Pin by: an inline no-flash script/class strategy in `app/layout.tsx` (or equivalent) sets `.dark` from persisted/system preference before hydration; verify no console hydration errors.
3. **Severity/status unreadable in one theme** — critical/high badges or run states lose contrast in dark or light. A reasonable person expects “Critical” to be immediately legible in both themes. Pin by: severity/status token definitions have light+dark values and are used via shared helpers/components; smoke check findings/runs/engagement status in both themes.
4. **Auth/guard regressions during redesign** — restyled pages drop `RequireAuth`, break login `?next`, or stop sending tokens (API already fixed). A reasonable person expects sign-in → protected navigation → sign-out to still work. Pin by: manual smoke (login, refresh persistence, protected redirect, sign-out) and preserving `lib/api.ts`/auth components’ behavior.
5. **Focus/keyboard invisible** — custom styling removes outlines/rings. A reasonable person expects Tab focus to be visible on buttons/links/inputs in both themes. Pin by: primitives define `focus-visible` ring styles using `--ring`/accent tokens and no global `outline: none` without replacement; spot-check keyboard nav on shell and forms.

---

## File Structure

**Create/modify (foundation):**
- Create: `apps/web/postcss.config.mjs` — registers `@tailwindcss/postcss`.
- Modify: `apps/web/app/globals.css` — **replace** hand-rolled utilities with Tailwind v4 import, `@custom-variant dark`, base resets compatible with the design system, and theme tokens (`:root` / `.dark` + `@theme inline` semantic mapping). Owns all visual tokens.
- Modify: `apps/web/app/layout.tsx` — theme no-flash handling (`suppressHydrationWarning` on `<html>` as needed) and wraps app with theme provider if used.
- Create: `apps/web/components/ThemeProvider.tsx` — lightweight client theme context (`theme`, `setTheme`, `resolvedTheme`), persistence (`localStorage` key e.g. `anomaly-theme`), system preference, toggles `.dark` on `document.documentElement`.
- Create: `apps/web/components/ThemeToggle.tsx` — accessible toggle control using tokens.

**Shell & layout:**
- Modify: `apps/web/components/layout/layout.tsx` (or split into `AppShell.tsx`/`Sidebar.tsx`/`TopNav.tsx` if clearer; preserve exports used by pages) — enterprise shell, responsive behavior, themed, includes theme toggle and correct sign-out.

**Primitives (`apps/web/components/ui/*`):**
- Modify: `button.tsx`, `input.tsx`, `select.tsx`, `label.tsx`, `badge.tsx`, `card.tsx`, `table.tsx`, `empty-state.tsx`, `icons.tsx` as needed — normalize on tokens, focus states, variants including semantic severity/status for badges.
- Create/modify as needed: small shared helpers e.g. `severity.ts` / `status.ts` (mapping domain values → badge/label variants + text labels) to eliminate hardcoded color classes in pages.

**Routes (`apps/web/app/**/page.tsx`):**
- Modify all route pages listed in Global Constraints to use the shell + primitives + semantic states; remove hardcoded palette classes and ad-hoc layout where replaced.

**No backend changes.** No changes to `lib/api.ts` auth/refresh behavior except only if strictly required (avoid).

---

### Task 1: Wire Tailwind CSS 4 correctly

**Files:**
- Create: `apps/web/postcss.config.mjs`
- Modify: `apps/web/app/globals.css`

**Interfaces:**
- Produces: a working Tailwind 4 pipeline; `@import "tailwindcss"` processed; `@custom-variant dark (&:where(.dark, .dark *))` available; existing semantic token class names used by components (`bg-background`, `text-muted-foreground`, `bg-primary`, `border-input`, `ring-ring`, etc.) resolve to defined CSS variables.

- [ ] **Step 1: Inspect current Tailwind/PostCSS state**

Run: `cd /home/deon/dev/github/anomaly/apps/web && ls postcss.config.* tailwind.config.* 2>&1; node -e "require.resolve('@tailwindcss/postcss')" 2>&1 | tail -2`
Expected: confirms no postcss/tailwind config files and `@tailwindcss/postcss` is resolvable (installed in `node_modules`).

- [ ] **Step 2: Create `apps/web/postcss.config.mjs`**

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
export default config;
```

- [ ] **Step 3: Replace `apps/web/app/globals.css` with a Tailwind 4 + token foundation (minimal, buildable)**

Implement `globals.css` containing, in order: `@import "tailwindcss";`, `@custom-variant dark (&:where(.dark, .dark *));`, `:root` light tokens, `.dark` charcoal/cyber tokens, `@theme inline` mapping semantic variables to Tailwind color tokens (at minimum: `--color-background`, `--color-foreground`, `--color-card`, `--color-card-foreground`, `--color-popover`, `--color-popover-foreground`, `--color-primary`, `--color-primary-foreground`, `--color-secondary`, `--color-secondary-foreground`, `--color-muted`, `--color-muted-foreground`, `--color-accent`, `--color-accent-foreground`, `--color-destructive`, `--color-destructive-foreground`, `--color-border`, `--color-input`, `--color-ring`), and base layer rules for `body`/borders/focus defaults that do not break the app. Remove the old hand-rolled utility dump. **Direction values:** dark base = deep charcoal/graphite (not pure black), light = cool neutrals, accent = restrained cyan/blue, all tuned for contrast. Include `tailwindcss-animate` compatibility if needed by existing patterns (verify during build; add `@plugin`/import only if required by v4 setup in this repo).

- [ ] **Step 4: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS (build may show style changes; no type/build errors). If build fails due to Tailwind v4/plugin syntax in this environment, adjust to the documented v4-compatible syntax and re-run.

- [ ] **Step 5: Commit**

```bash
git add apps/web/postcss.config.mjs apps/web/app/globals.css
git commit -m "feat(web): wire Tailwind v4 and add theme token foundation"
```

### Task 2: Theme provider, no-flash behavior, and toggle

**Files:**
- Create: `apps/web/components/ThemeProvider.tsx`
- Create: `apps/web/components/ThemeToggle.tsx`
- Modify: `apps/web/app/layout.tsx`

**Interfaces:**
- Produces: `ThemeProvider` (client) exporting theme state/toggle for the app; root `<html>` receives/retains `class="dark"` when resolved dark; preference persisted under `anomaly-theme` with values `light|dark|system`; a `ThemeToggle` component usable in the shell.

- [ ] **Step 1: Implement `ThemeProvider.tsx`**

Client component that reads persisted preference (or `system`), resolves via `matchMedia('(prefers-color-scheme: dark)')`, applies/removes `dark` on `document.documentElement`, persists on change, and exposes context/hook (e.g., `useTheme`). Keep it lightweight (no new dependency).

- [ ] **Step 2: Add no-flash theme initialization in `layout.tsx`**

Add `suppressHydrationWarning` on `<html>` if using a pre-hydration class/script strategy. Add a minimal inline script (safe/static string) before hydration that sets `document.documentElement.classList` based on `localStorage['anomaly-theme']` / system preference, so dark users don’t flash light. Wrap `{children}` with `ThemeProvider` inside `<body>` (preserving `AuthProvider`).

- [ ] **Step 3: Implement `ThemeToggle.tsx`**

Accessible button/control (labeled, keyboard/focus-visible) that cycles or selects light/dark/system per chosen UX (builder’s call; keep clear). Uses semantic tokens, no hardcoded colors.

- [ ] **Step 4: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS. Manual: set theme, refresh — no flash, preference persists.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/ThemeProvider.tsx apps/web/components/ThemeToggle.tsx apps/web/app/layout.tsx
git commit -m "feat(web): add light/dark theme system with toggle"
```

### Task 3: Severity/status semantics and shared UI helpers

**Files:**
- Modify: `apps/web/app/globals.css` (add semantic severity/status tokens/utility patterns if needed)
- Create: `apps/web/components/ui/severity.ts` (or `lib/severity.ts`)
- Create: `apps/web/components/ui/status.ts` (or `lib/status.ts`)
- Modify: `apps/web/components/ui/badge.tsx`

**Interfaces:**
- Produces: `severityVariant(severity: string): { className: string; label: string }` (or equivalent) covering `critical|high|medium|low|info|unknown`; `statusVariant(domain,status)` for runs/findings/engagements; `Badge` supports/uses semantic variants. Replaces hardcoded `bg-red-100 text-red-800` patterns in pages.

- [ ] **Step 1: Define severity/status token classes in `globals.css` (both themes)**

Add CSS variables/utilities (or Tailwind token-backed classes) for severity and status that maintain contrast and the approved cyber-professional feel. Critical/high must be unmistakable; accent (cyan) reserved for active/technical emphasis, not severity except where semantically appropriate.

- [ ] **Step 2: Implement shared mappers and update `Badge`**

Export typed helpers mapping raw API values (case-insensitive) to labels + class names; default safely for unknown values. Ensure badges include text labels (non-color cue).

- [ ] **Step 3: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/globals.css apps/web/components/ui/badge.tsx apps/web/components/ui/severity.ts apps/web/components/ui/status.ts
git commit -m "feat(web): add semantic severity and status UI tokens"
```
*(Adjust paths if helpers placed under `lib/`.)*

### Task 4: Enterprise app shell (sidebar, top bar, layout)

**Files:**
- Modify: `apps/web/components/layout/layout.tsx` (and any files it’s split into)
- Modify: pages only if shell prop/API changes require it (keep `TopNav`/`Sidebar` exports compatible where practical)

**Interfaces:**
- Produces: a themed, responsive, accessible shell with clear active navigation, workspace context, `ThemeToggle`, and working sign-out; uses tokens (no hardcoded grays/blues). Collapsed/mobile behavior is usable (builder decides exact responsive pattern; must remain navigable).

- [ ] **Step 1: Redesign shell structure/styles on tokens**

Apply charcoal/cool-neutral surfaces, subtle borders, restrained cyan accent for active/focus states, consistent spacing/typography. Preserve navigation items/routes and `useAuth` logout behavior. Remove hardcoded user assumptions.

- [ ] **Step 2: Integrate `ThemeToggle` and responsive nav access**

Ensure navigation is reachable on narrow viewports (menu/drawer or equivalent) — a reasonable person can use the app without a wide desktop.

- [ ] **Step 3: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS. Manual smoke: navigate all primary routes, toggle theme, sign out.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/layout apps/web/components/ThemeToggle.tsx
git commit -m "feat(web): redesign enterprise app shell and navigation"
```

### Task 5: Normalize core UI primitives

**Files:**
- Modify: `apps/web/components/ui/button.tsx`, `input.tsx`, `select.tsx`, `label.tsx`, `card.tsx`, `table.tsx`, `empty-state.tsx` (and others present/used)

**Interfaces:**
- Produces: primitives with consistent radii/spacing/typography, `focus-visible` rings using `--ring`, disabled/loading states, and full theme compatibility. No primitive relies on the removed hand-rolled global utility sheet.

- [ ] **Step 1: Update each primitive to the token system**

Keep APIs stable where pages depend on them; extend variants only when needed. Ensure form controls and tables read clearly in both themes (headers, row hover, borders).

- [ ] **Step 2: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/ui
git commit -m "feat(web): normalize UI primitives for enterprise theme system"
```

### Task 6: Auth screens (login, register) + global error/not-found states

**Files:**
- Modify: `apps/web/app/login/page.tsx`, `apps/web/app/register/page.tsx`
- Create/modify if missing: `apps/web/app/not-found.tsx` (and `error.tsx`/global error handling only if appropriate/low-risk)

**Interfaces:**
- Produces: polished, themed auth experience aligned with Anomaly identity; preserves form behavior, validation feedback, register/login API calls, and login `?next` redirect. Clear error/success messaging.

- [ ] **Step 1: Redesign auth pages using primitives/tokens**

Centered, calm layout; accessible labels/errors; theme-aware. Keep Shield/Anomaly mark treatment consistent with shell.

- [ ] **Step 2: Add/align not-found (and minimal global error state if added)**

Themed, helpful navigation back to safe routes.

- [ ] **Step 3: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS. Manual smoke: register validation, login success/failure, `?next` redirect.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/login apps/web/app/register apps/web/app/not-found.tsx apps/web/app/error.tsx
git commit -m "feat(web): redesign auth and global fallback states"
```
*(Only add files that were created/modified.)*

### Task 7: Dashboard (enterprise operator overview)

**Files:**
- Modify: `apps/web/app/page.tsx` (and any extracted dashboard components under `components/` if created)

**Interfaces:**
- Produces: themed dashboard with clear metric hierarchy, recent activity/findings/runs sections (using real data where endpoints exist; honest, well-designed empty/loading/error states where not), and actionable navigation. No hardcoded palette classes.

- [ ] **Step 1: Rebuild dashboard layout and states on tokens/primitives**

Apply Vercel-like spacing/clarity, semantic status/severity, and responsive grid behavior. Keep `RequireAuth` and data fetching intact.

- [ ] **Step 2: Run verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS. Manual smoke: authenticated load, API error state, theme toggle.

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/page.tsx apps/web/components
git commit -m "feat(web): redesign dashboard for enterprise operator workflow"
```

### Task 8: Engagements (list, detail, new placeholder)

**Files:**
- Modify: `apps/web/app/engagements/page.tsx`, `apps/web/app/engagements/[id]/page.tsx`, `apps/web/app/engagements/new/page.tsx`

**Interfaces:**
- Produces: consistent list/detail/create-placeholder UX with semantic status/mode rendering, strong table/detail hierarchy, and correct loading/empty/error/not-found handling.

- [ ] **Step 1: Migrate engagements screens to shell/primitives/semantic helpers**

Remove hardcoded severity/status/mode color maps; preserve links, actions, and data flows.

- [ ] **Step 2: Run verification + manual smoke**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Manual: list loads, open detail, navigate back/new, both themes.

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/engagements
git commit -m "feat(web): redesign engagements workflows"
```

### Task 9: Findings (list, detail placeholder)

**Files:**
- Modify: `apps/web/app/findings/page.tsx`, `apps/web/app/findings/[id]/page.tsx`

**Interfaces:**
- Produces: severity-first triage readability, semantic badges, clear filters/status presentation (within existing capabilities), and consistent states.

- [ ] **Step 1: Migrate findings screens; replace hardcoded severity colors**

- [ ] **Step 2: Run verification + manual smoke (both themes, severity legibility)**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/findings
git commit -m "feat(web): redesign findings and severity presentation"
```

### Task 10: Runs (list, detail placeholder, new placeholder)

**Files:**
- Modify: `apps/web/app/runs/page.tsx`, `apps/web/app/runs/[id]/page.tsx`, `apps/web/app/runs/new/page.tsx`

**Interfaces:**
- Produces: clear run/status visibility, semantic status/warning rendering (scope warnings), consistent with findings/engagements.

- [ ] **Step 1: Migrate runs screens to the system**
- [ ] **Step 2: Run verification + manual smoke**
- [ ] **Step 3: Commit**

```bash
git add apps/web/app/runs
git commit -m "feat(web): redesign runs workflows"
```

### Task 11: Reports, Playbooks, Schedules, Settings (remaining product surfaces)

**Files:**
- Modify: `apps/web/app/reports/page.tsx`, `apps/web/app/playbooks/page.tsx`, `apps/web/app/playbooks/new/page.tsx`, `apps/web/app/schedules/page.tsx`, `apps/web/app/schedules/new/page.tsx`, `apps/web/app/settings/page.tsx`

**Interfaces:**
- Produces: all remaining routes at the same enterprise bar; placeholders (where flows aren’t fully implemented) are intentional, themed, and helpful—not dead/broken-looking. Reports flow preserves authenticated generation behavior.

- [ ] **Step 1: Migrate each surface to tokens/primitives/states**

- [ ] **Step 2: Run verification + manual smoke across all routes in both themes**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Manual route sweep: `/login`, `/register`, `/`, `/engagements`, `/findings`, `/runs`, `/reports`, `/playbooks`, `/schedules`, `/settings` and key detail/new routes.

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/reports apps/web/app/playbooks apps/web/app/schedules apps/web/app/settings
git commit -m "feat(web): redesign remaining product surfaces"
```

### Task 12: Accessibility/contrast polish, cleanup, and final verification

**Files:**
- Modify: any files needed for focus/contrast/ARIA/landmark fixes discovered in sweep
- Modify: `apps/web/app/globals.css` and primitives only as needed for final token tuning

**Interfaces:**
- Produces: production-ready pass — no color-only severity meaning, visible focus everywhere, reasonable landmarks/headings, cleaned dead hardcoded palette usage in feature pages, and stable builds.

- [ ] **Step 1: Sweep for remaining hardcoded status/severity palette classes and token gaps**

Run: `cd /home/deon/dev/github/anomaly/apps/web && grep -rn 'bg-\(red\|green\|yellow\|blue\|orange\|purple\)-[0-9]\|text-\(red\|green\|yellow\|blue\|orange\|purple\)-[0-9]' app components --include='*.tsx' | head -40`
Expected: only intentional, reviewed exceptions (ideally none in feature/status rendering). Replace stragglers with semantic helpers.

- [ ] **Step 2: Keyboard/focus and theme-contrast sanity pass**

Tab through shell, login, a table/list, and primary actions in **light and dark**; confirm visible focus and legible severity/status.

- [ ] **Step 3: Final verification**

Run: `cd /home/deon/dev/github/anomaly/apps/web && npx tsc --noEmit && NEXT_TELEMETRY_DISABLED=1 npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/web
git commit -m "chore(web): accessibility, contrast, and enterprise UI polish"
```

---

## Self-Review Notes (for the author)
- Spec coverage: identity/themes/full product/shell/primitives/all routes/accessibility/verification mapped to Tasks 1–12; behavior/contracts preserved by constraint. Gaps found during execution should become tasks/steps, not ad-hoc drift.
- Token names chosen to match existing component usage (`background/foreground/card/primary/secondary/muted/accent/destructive/border/input/ring` + `*-foreground`) to minimize breakage while replacing the broken hand-rolled globals.
- TDD: no frontend unit-test harness exists in `apps/web` today; plan uses typecheck/build + explicit manual smoke/contrast checks as verification. If a test harness is added later, pin token/helper logic with unit tests (out of scope unless requested).
- Proportion: steps state decisions/signatures/values and verification; implementers write component bodies against the token system and spec, not copied from a transcript.
