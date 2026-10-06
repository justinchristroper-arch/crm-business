# Security and testing boundaries

## Implemented

Argon2id hashes; HS256 JWT with issuer/audience/expiry; DB session revocation; HttpOnly SameSite=Strict cookie (Secure required in production); in-memory CSRF recovered from /auth/me; current DB role/status per request; session revocation on user-management changes. Exact origins/CORS, typed inputs, owner/assignee/team scoping, DB constraints, transactional conversion/import, revision conflict checks, audit actor/old/new/reason and immutable UPDATE/DELETE trigger. Login throttling blocks eight failures per email/client address for 15 minutes; unknown accounts verify a dummy hash. Frontend text escaping, CSV formula handling, CSP/no-store/nosniff/frame headers; env ignored by Git.

## Limitations

- Portfolio-grade, not enterprise security or production certification. Synthetic shared demo credentials include Admin powers.
- No MFA, reset-email flow, verification, SSO, refresh token rotation, session-device UI, or comprehensive abuse/WAF protection.
- Throttling uses ASGI client IP, without trusting arbitrary forwarded headers; proxies can make users share apparent IP.
- Team strings/one assignee; no multi-tenant organization layer or complex ACLs.
- Duplicate constraints are owner-scoped for privacy, not global customer identity resolution.
- DB owner can override trigger/TRUNCATE; audit is not a cryptographic external ledger. Use restricted runtime DB permissions.
- READ COMMITTED UI snapshots can span concurrent commits. Revision guards writes, not snapshot consistency.
- Scoped collections are returned for low data volumes; no cursor pagination/load testing. Metrics aggregate in Python; serialization may do multiple ORM reads. Large datasets need SQL aggregation, eager loading, and pagination.
- UI app.js remains large; future growth should split page/form modules.
- Import is data migration with new IDs/timestamps/ownership, not exact restore; audit actors cannot be forged from backup.
- Provider storage/DB permissions protect secrets at rest; no app-level field encryption. Demo must use fictitious data only.
- Explicit migrations/seed; Neon operational backup/restore drills not verified.
- Browser checks are tool-assisted, not automated cross-browser E2E, penetration testing, or load testing.
- Swagger uses CDN script/style only on /api/docs; normal app scripts are restricted to self.
- Disposable Windows cluster is loopback-only trust auth, never a production database configuration.

## Test coverage

Dedicated PostgreSQL `_test` DB is migrated and truncated per test. Coverage: auth/hash/session/logout/bad password, CSRF/origin, DB role/active reload, role/ownership IDOR, scoped lists/export/analytics/audit, manager team access, duplicate normalization, transactional conversion/reuse/rollback, Won/Lost/closing reason, reopen/stale revision, privileged change reason, owner/value audit, overdue/completion/risk/config, manual follow-up, immutable DB audit, dashboard formulas/window/sales cycle, Admin deactivation, import rollback, foreign relation protection, blocked opportunity deletion.

Frontend Node tests cover same-origin cookies/CSRF, rejected responses/network failures, canonical stage/payload mapping. ESLint/syntax checks cover JS. Tests do not prove every UI interaction.

```sh
npm run check
ruff check backend migrations scripts/build.py
pytest -q
alembic current
alembic check
python scripts/build.py
pip check
```

CI uses disposable PostgreSQL and synthetic, non-production test credentials. Actual final check results appear in VERIFICATION.md.
