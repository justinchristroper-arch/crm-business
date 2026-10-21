# Neon Free + Vercel deployment guide

## Status/cost

Full-stack v2 is live at **https://crm-business-sigma.vercel.app**, backed by Neon PostgreSQL. Public source: https://github.com/justinchristroper-arch/crm-business (`main`). Vercel project `justin-c/crm-business` uses Hobby; the Marketplace database `crm-business-db` uses Neon Free (`free_v3`), region `sin1`, with Neon Auth disabled. The original Sites v1 is superseded by this deployment.

The owner accepted integration terms before provisioning. Alembic migrations and explicit synthetic seed completed successfully; current schema revision is `0003_lead_details`. Runtime uses a restricted SQL role through pooled SSL connections; migrations use the separate offline owner role/direct SSL connection. Production JWT secret and database credentials remain in ignored env files/provider configuration. This guide also describes how to reproduce the setup; no additional project is needed for the existing demo.

Target zero cost for low personal/noncommercial portfolio traffic, within provider quotas. Do not activate paid plans/integrations or buy a domain. Check Free/Hobby labels before provisioning. Sources: [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Neon plans](https://neon.com/docs/introduction/plans), [FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi), [Neon pooling](https://neon.com/docs/connect/connection-pooling).

## 1. Neon Free

1. Sign in to Neon and create a project on **Free**, e.g. crm-business-portfolio.
2. Select a region appropriate to the Vercel region.
3. Copy pooled/direct connection strings from Connect into ignored env files, never Git/chat/public documents.
4. `DATABASE_URL` = pooled; `MIGRATION_DATABASE_URL` = direct. Preserve SSL parameters such as sslmode=require. postgresql:// and postgresql+psycopg:// are accepted.
5. Use a separate branch/database for preview/testing; TEST_DATABASE_URL must be disposable and end `_test`.

The current demo already uses separate restricted application and schema-migration DB roles. The application role has no schema ownership/CREATE or audit UPDATE/DELETE/TRUNCATE. For a new environment, provision it explicitly with `python -m scripts.runtime_role` as described in [free hardening operations](FREE-HARDENING.md); it never runs automatically during startup/build.

## 2. Vercel env

| Key | Production value |
|---|---|
| DATABASE_URL | Neon pooled SSL URL |
| JWT_SECRET | Unique random secret, at least 32 characters |
| APP_ENV | production |
| COOKIE_SECURE | true |
| ALLOWED_ORIGINS | ["https://crm-business-sigma.vercel.app"] for the existing demo |
| DEMO_MODE | true for synthetic portfolio accounts |
| ENABLE_DEMO_RESET | false recommended |
| REPORT_TIMEZONE | Asia/Jakarta |
| DEMO_PASSWORD | Optional override before first seed |

MIGRATION_DATABASE_URL can remain local/offline; Vercel build must not run migrations. No TEST_DATABASE_URL is needed in production. Store secrets as encrypted/sensitive env values, never frontend variables. Preview origins require explicit allowlisting and separate DB environment, not wildcards.

Generate a secret into a **new ignored file**, without printing it:

```python
from pathlib import Path
import secrets
path = Path('.env.production.local')
if path.exists():
    raise RuntimeError('Preserve existing file')
path.write_text('JWT_SECRET=' + secrets.token_urlsafe(48) + '\n')
```

Transfer its value to Vercel's environment editor privately; do not reuse the development secret.

## 3. Migration/seed

Configure an ignored local `.env` for the intended Neon branch; preserve the original local env privately. Reconfirm target project/branch/database in dashboard without printing its connection URL.

```sh
alembic upgrade head
alembic current
alembic check
python -m backend.seed
```

DEMO_MODE=true is needed for synthetic seed. Do not migrate from several instances simultaneously. Review migrations/test isolated branches/take operational backups before future destructive changes. No schema changes occur in startup/request/build.

## 4. Vercel Hobby

1. Push `main` to your GitHub repository. The existing public repository is already connected to Vercel.
2. Import repo on **Hobby**, framework **FastAPI**, root at repo root, Python 3.12 or supported compatible version.
3. Entry point is backend.main:app in pyproject.toml. Build command `python scripts/build.py` copies dist assets to public for CDN. The Vercel uv builder uses the Python 3.12 project dependencies in pyproject.toml and committed uv.lock; requirements.txt also pins runtime dependencies for pip/local/CI.
4. Do not configure the project as a dist-only static deployment.
5. Set env vars and actual stable production origin before testing login.
6. Verify successful Vercel build, /api/health, login and complete CRM flow. Local asset build is not proof of a successful hosted deployment.

SQLAlchemy NullPool and pooled Neon URL accommodate serverless connections. Cold starts/provider request and payload limits apply. Browser request timeout is 20 seconds; reload before retrying a mutation whose outcome is unknown.

## 5. Verification

Test Rep create/convert/close/reopen/audit, other Rep private-data denial, Manager team metrics/reason enforcement, Admin user/config, session invalidation, reload persistence, mobile/keyboard dropdowns, error states, logout, exact-origin cookies. Public demo accounts share synthetic data, including Admin powers; no real customer data.

## Portfolio links

Use these verified URLs on your existing portfolio project card:

```html
<a href="https://crm-business-sigma.vercel.app" target="_blank" rel="noopener noreferrer">Live Demo</a>
<a href="https://github.com/justinchristroper-arch/crm-business" target="_blank" rel="noopener noreferrer">Source Code</a>
```

Linking is supported; iframe embedding is intentionally blocked by frame protection. This task does not modify your existing portfolio website. See [portfolio handoff](PORTFOLIO-HANDOFF.md) for card text, resume bullets, and the recommended screenshot.
