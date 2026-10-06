# Verification record — 6 October 2026 (Asia/Jakarta)

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
