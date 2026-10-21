# Phase 3: public portfolio publication

This records the initial publication. For the subsequent audit fixes, current schema `0003_lead_details`, runtime privilege separation and latest test results, see [hardening verification](HARDENING-VERIFICATION.md).

Initial work: 6 October 2026. Finalization: 21 October 2026 (Asia/Jakarta).
Starting verified code: 17fd83d9e633fd05db852e6a6581ee6b434ca9e4 on codex/full-stack-crm.

## Pre-publication checks

- Working tree initially clean.
- GitHub CLI authenticated as justinchristroper-arch; crm-business repository not present at preflight.
- .env, .venv, node_modules, artifacts/PostgreSQL files and public build output are ignored.
- Only .env.example is tracked among .env patterns; no tracked local DB files.
- Reachable Git history scanned for the actual local JWT secret, GitHub token patterns, private-key markers, and accidentally committed private/generated paths: no findings.
- README now presents business problem, stack, roles, architecture, and technical highlights before setup instructions.
- Public synthetic demo/test passwords are deliberately labelled as non-production credentials, as required by the demo documentation. No real production secret is published.

## Deployment state

Public repository: https://github.com/justinchristroper-arch/crm-business. Default public branch: main. codex/full-stack-crm was fast-forward merged from the original master base, retaining all commits. origin/main was pushed and synchronized.

GitHub CI run https://github.com/justinchristroper-arch/crm-business/actions/runs/37479537207 succeeded on f108de37a180e3239d48af7c4f967237c2e6cf42: 29 PostgreSQL backend tests, 3 frontend tests, ESLint, Ruff, asset build, pip check, Alembic head 0002_audit_immutability, no schema drift. CI database was disposable PostgreSQL, not Neon. One Starlette/httpx TestClient deprecation warning remains.

Vercel project `justin-c/crm-business` runs on Hobby with GitHub connected. **Public full-stack demo: https://crm-business-sigma.vercel.app**. Frontend assets and FastAPI share one origin; FastAPI region is `sin1`. Python project metadata and `uv.lock` were added so the Vercel uv builder resolves the pinned Python 3.12 runtime successfully. Generated `.vercel` and env files remain ignored.

After the owner accepted Marketplace/Neon terms, provisioning succeeded with Neon **Free** (`free_v3`), database name `crm-business-db`, region `sin1`, built-in Neon Auth disabled, production environment. No paid plan was activated. Runtime uses pooled SSL, migrations use direct SSL; secrets are private environment configuration.

Explicit Alembic upgrade, schema check, and synthetic seed succeeded. Database revision is `0002_audit_immutability`, with no schema drift. Production JWT, secure cookie settings, exact HTTPS allowed origin, demo mode, disabled public reset, and Asia/Jakarta timezone were configured. Migrations do not run during deployment builds or requests.

Application code `8edcecb0d6dca485b15ea4f83d57eda6d8b21d46` deployed successfully and passed GitHub CI run [37486112329](https://github.com/justinchristroper-arch/crm-business/actions/runs/37486112329). Finalization repeated hosted acceptance: **131 checks passed**. Real production browser flows and responsive views at 1440/1280/768/390px were inspected. Eleven original hosted screenshots are in `docs/screenshots/`. See [final verification](VERIFICATION.md) and [portfolio content](PORTFOLIO-HANDOFF.md). Existing Sites v1 and localhost are not used as production evidence for v2.

## Acceptance record policy

Do not mark Phase 3 final until the real public deployment passes requested auth/ownership/business/analytics/persistence/audit flows, responsive checks at 1440/1280/768/390px, and real hosted screenshots are saved in docs/screenshots. Record the tested deployed code SHA separately from subsequent documentation/screenshot commits.

No separate portfolio website repository is edited during this phase.
