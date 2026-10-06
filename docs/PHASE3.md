# Phase 3: public portfolio publication

Date: 6 October 2026 (Asia/Jakarta).
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

Vercel CLI authenticated; scope justin-c (JustinC) verified as Hobby. Project justin-c/crm-business created, FastAPI detected, GitHub repository connected. Generated .vercel and .env.local are ignored. Deployment list returned no deployments.

Neon provisioning was attempted through Vercel Marketplace with explicit verified Free plan free_v3, region sin1, built-in Neon Auth disabled, environment production. The CLI returned action_required / integration_terms_acceptance_required. No production database was created, and no paid plan was activated.

**Required owner action:** review and accept terms at https://vercel.com/justin-c/~/integrations/accept-terms/neon?source=cli, then tell the agent to resume. The CLI requests personal browser/dashboard completion; the agent did not accept legal terms on the user's behalf.

Once confirmed, retry the same provisioning command (first reconcile whether a resource has already appeared, to avoid duplicates), retrieve env variables privately, run migrations/seed explicitly, configure secure production env/origins, deploy, and complete hosted acceptance/responsive/screenshot checks. Full-stack production URL, Neon migration/seed, hosted flows, and screenshots are still pending. Existing Sites v1 and localhost are not production evidence for v2.

## Acceptance record policy

Do not mark Phase 3 final until the real public deployment passes requested auth/ownership/business/analytics/persistence/audit flows, responsive checks at 1440/1280/768/390px, and real hosted screenshots are saved in docs/screenshots. Record the tested deployed code SHA separately from subsequent documentation/screenshot commits.

No separate portfolio website repository is edited during this phase.
