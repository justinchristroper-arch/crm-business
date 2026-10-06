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

Neon plugin is available but not installed/connected at preflight. A suggestion was made to allow the user to install/connect it. No Neon production database has been provisioned yet. This is an authentication/provisioning dependency, not a completed deployment.

Vercel CLI authentication is being checked. Full-stack production URL, migrations/seed against Neon, hosted acceptance flows, and production screenshots are pending. The existing Sites v1 and localhost previews are not production evidence for v2.

## Acceptance record policy

Do not mark Phase 3 final until the real public deployment passes requested auth/ownership/business/analytics/persistence/audit flows, responsive checks at 1440/1280/768/390px, and real hosted screenshots are saved in docs/screenshots. Record the tested deployed code SHA separately from subsequent documentation/screenshot commits.

No separate portfolio website repository is edited during this phase.
