# Public deployment verification

**Latest application verification:** [audit fixes and free hardening](HARDENING-VERIFICATION.md) supersedes the earlier implementation record below: 42 backend tests, 3 frontend tests, 2 browser E2E tests, 135 hosted acceptance checks and 38 targeted hosted regressions. Application code `c5d599563d24ea1227abbfcf09dd27b957588a1c`; schema `0003_lead_details`.

Finalization date: **21 October 2026 (Asia/Jakarta)**. Initial deployment/screenshots: 6 October 2026. Public URL: **https://crm-business-sigma.vercel.app**. Public repository: **https://github.com/justinchristroper-arch/crm-business**, branch `main`.

Tested deployed application code: **8edcecb0d6dca485b15ea4f83d57eda6d8b21d46**. Subsequent publication changes contain documentation, evidence, and screenshots only. The final documentation commit can be found with `git log -1`; its own SHA is intentionally not embedded inside itself.

## Hosted acceptance

**131 checks passed** on the real HTTPS application on 21 October 2026, using separate httpx sessions and synthetic data. [Machine-readable results](hosted-acceptance.json) contain check names/outcomes, not cookies, tokens, passwords, or connection strings. Initial hosted acceptance on 6 October had 127 passing checks; the count grows with per-rep analytics rows in the shared demo.

| Boundary | Evidence |
|---|---|
| Authentication | Sales/second Sales/Manager/Admin login; invalid login 401; anonymous workspace 401; logout revokes session; Secure/HttpOnly/SameSite=Strict cookie |
| Lead conversion | Create/edit lead; transactional Company/Contact/Opportunity relationships verified |
| Opportunity | Proposal → Won → Lost with required reason → reopen; closure/reason cleared; value update persisted |
| Tasks | Create overdue task; complete → reopen → complete; overdue state recalculated |
| Authorization | Cross-rep read/write returns 404; Sales user management returns 403; Manager sees team and cannot change outcomes without an explanation (422) |
| Admin | Synthetic user created and disabled through API; existing synthetic QA user activation also checked in browser |
| Audit | Conversion/stage/reopen/value/owner events exist; ordinary audit PUT/DELETE return 405 |
| Analytics | Initial/final Sales and Manager pipeline, won value, win rate, conversion cohort, overdue, At Risk, stage totals, rep totals, average sales cycle recomputed from scoped server records |
| Persistence | Independent second Sales session reads the saved opportunity value; browser reload retains session and task state |
| Database | Neon pooled SSL runtime/direct SSL migrations; explicit seed successful; revision `0002_audit_immutability`; no drift |

## Hosted browser and responsive evidence

Tool-assisted Chromium checks used the production origin, not localhost. Sales created/edited/converted a lead in the UI, created/completed/reopened a task, changed opportunity stage, encountered the required Lost reason, reopened a deal, and opened audit before/after detail. Manager team dashboard and by-rep analytics loaded; a Manager stage change without explanation returned 422 and stayed in the dialog. Admin users page loaded and QA user editing was checked. Refresh preserved an authenticated session and saved task state; logout returned to login.

| Viewport | Inspected |
|---|---|
| 1440 × 1000 | Dashboard/cards, Leads table, pipeline Kanban and dropdown stages, forms, audit detail, Manager analytics |
| 1280 × 900 | Dashboard/card layout and table; no global horizontal overflow |
| 768 × 1024 | Tablet Manager dashboard/navigation; no global horizontal overflow |
| 390 × 844 | Mobile navigation, task form/dialog, task complete/reopen; Kanban contained scroll, stage dropdown saved and retained after refresh; no global horizontal overflow |

Tables and Kanban may scroll within their containers. Stage dropdowns provide an alternative to dragging. These are representative checks, not a complete cross-browser/device certification. [Screenshot manifest](screenshots/README.md) lists the real hosted captures. Shared demo changes mean screenshot totals need not equal the current dashboard.

## Quality gates and deployment

The application-code [GitHub CI run](https://github.com/justinchristroper-arch/crm-business/actions/runs/37486112329) succeeded: **29 PostgreSQL backend tests**, **3 frontend tests**, JS syntax/ESLint, Ruff, asset build, pip dependency check, Alembic head and no drift. The final publication push runs the same pipeline again; see [current runs](https://github.com/justinchristroper-arch/crm-business/actions). One Starlette/httpx test deprecation warning remains.

Frontend/API share Vercel Hobby origin; FastAPI executes in Singapore near Neon Free. `APP_ENV=production`, secure cookies, exact production `ALLOWED_ORIGINS`, `DEMO_MODE=true`, `ENABLE_DEMO_RESET=false`, and Asia/Jakarta report timezone are configured. No migration/seed runs during build, startup, or requests. No paid plan/API was activated. Finalization's browser inspection found no HTTP resource references on the HTTPS page and no application page errors. Vercel error-level log query for the preceding hour returned no logs; this is a bounded observation, not a claim of long-term monitoring. Cold starts, shared demo data/Admin powers, and provider quotas apply. No monitoring drain, load test, or uptime SLA is claimed. See [security limitations](SECURITY-TESTING.md) and [deployment guide](DEPLOYMENT.md).

The separate portfolio repository was not modified. [Portfolio handoff](PORTFOLIO-HANDOFF.md) provides verified URLs, copy, stack, resume bullets, limitations, and a recommended image.

---

# Historical local verification — 6 October 2026

The following record documents the pre-publication implementation. Deployment statements and branch names below describe that historical stage; the public deployment record above supersedes them.

## Implemented architecture/model

Preserved HTML/CSS/JS frontend, same-origin FastAPI REST API, SQLAlchemy, PostgreSQL 17, Alembic, Argon2id/JWT HttpOnly session cookie with DB user/session checks and CSRF. Entities: User, Company, Contact, Lead, Opportunity, Task, AuditEvent; auxiliary session/login-attempt/config tables. Neon/Vercel deployment configuration and guide are provided, not claimed deployed.

## Final local quality gates

| Check | Outcome |
|---|---|
| PostgreSQL backend integration suite | **29 passed** |
| Frontend API adapter tests | **3 passed** |
| JS syntax and ESLint | Passed |
| Ruff backend/migration/build checks | Passed |
| Local production asset build | Passed, public/ generated; Python source parsed |
| pip check | No broken requirements |
| Alembic current | 0002_audit_immutability (head) |
| Alembic check | No new upgrade operations detected |
| Synthetic demo seed | Executed successfully, idempotent |

One test-library warning remains: Starlette deprecates its httpx TestClient path and recommends httpx2. Tests pass; this is not a runtime CRM failure. Direct runtime dependencies are pinned in requirements.txt, npm dependencies locked, verified development Python environment captured in requirements-dev.lock. GitHub CI has been configured but has not been executed remotely.

## Browser evidence

Tool-assisted browser flow against local FastAPI/PostgreSQL:

- Sales Rep login succeeded; private scoped dashboard showed Rp82.5m pipeline, four contacts before the QA record.
- Created synthetic Portfolio QA lead / QA Studio / qa-upgrade@example.com through POST /api/leads (201).
- Converted lead with a Rp7.5m opportunity through server command (200); after reload lead displayed Dikonversi and deal appeared in Kanban.
- Moved deal to Lost; UI required closing reason and server stored it (200). Reopened to Proposal; pipeline returned to Rp90m for that rep (200).
- Logout revoked session and displayed login screen. Mobile sidebar scrolling made logout reachable on a short viewport; closed menu became inert to keyboard focus.
- Manager login showed both Nusantara reps, Rp135m current pipeline, Rp40m Won in 30 days, 67% win rate, 20% lead conversion cohort, and average won sales cycle 36.5 days after QA conversion.
- Manager by-rep table displayed Dimas Sales Rp90m pipeline and Sarah Sales Rp45m pipeline/Rp40m Won.
- Desktop layout visually inspected at 1440×1000; small/default viewport navigation and stage dropdown used during flows.
- Captured browser error/warning log was empty at inspection. Initial unauthenticated /auth/me 401 is expected; successful action/status evidence is present in server logs.

Audit detail viewer was opened in the browser: it showed actor, Lost→Proposal old/new values, closed_at cleared, closing reason cleared, and metadata. Recent history is available on the dashboard. The browser verification is manual/tool-assisted, not an automated comprehensive cross-browser suite. Admin operations, ownership denial, transactional late-failure rollback, assignment, backup converted-link reconstruction, and immutable audit are verified in backend tests. No claim is made that every UI button, drag gesture, or export/import interaction was browser-tested.

## Business rules/auth

Owner/assignee/team enforcement; typed/normalized dedup; transactional conversion/import; stage/close/Lost reason/reopen; stage/owner/value audit including numeric-value equivalence; manager explanation requirement; overdue tasks; configurable At Risk and follow-up tracking; consistent backend formulas. Sales cannot manage users/config or take ownership of others' records. Manager scope is own team; Admin system-wide operations are audited.

## Deployment and limitations

Local PostgreSQL/FastAPI verified. Neon Free project has not been created by the user; user requested a setup guide. Full-stack v2 is **not publicly deployed**, and no GitHub repo was created. Old Sites URL is still v1. No paid API or paid plan was activated.

Remaining scope boundaries: shared demo credentials, no MFA/reset-email/SSO/refresh rotation, no multi-tenant organization isolation, owner-scoped rather than global dedup, no pagination/load testing, large app.js, READ COMMITTED snapshot consistency, migration-style rather than exact-restore JSON import. DB owners can defeat audit protections; production should use restricted runtime DB permissions. Read SECURITY-TESTING.md before presenting security claims.

## Files changed and Git handoff

Frontend: dist/app.js, api.js, model.js, styles.css; package.json/lock, eslint.config.js, tests/api.test.mjs. Old client-side seed/calculations/model tests removed; backend rules replace them. server.mjs forwards to full-stack dev runner.

Backend: backend/config.py, db.py, models.py, schemas.py, auth.py, services.py, main.py, backup.py, seed.py; PostgreSQL integration tests.

Infrastructure: Alembic config/env/revisions, requirements/runtime/dev lock, pyproject.toml, .python-version, .env.example, compose.yaml, vercel.json/.vercelignore, dev/build/local setup scripts, CI replacing static-only Pages deployment, .gitignore, .openai/README.md preserving old Site identity.

Documentation: README, SPEC, DEPLOYMENT, SECURITY-TESTING, CASE-STUDY, VERIFICATION.

Local branch: codex/full-stack-crm. The final response reports the actual commit SHA and post-commit Git status; use `git log -1` and `git status --short` to inspect. Runtime .env, virtualenv, PostgreSQL cluster/logs, generated public assets, and temporary scripts are intentionally ignored and uncommitted.
