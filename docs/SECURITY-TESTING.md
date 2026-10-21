# Security and testing boundaries

## Implemented

Argon2id hashes; HS256 JWT with issuer/audience/expiry; DB session revocation; HttpOnly SameSite=Strict cookie (Secure required in production); in-memory CSRF recovered from /auth/me; current DB role/status per request; session revocation on user-management changes. Exact origins/CORS, typed inputs, owner/assignee/team scoping, DB constraints, transactional conversion/import, revision conflict checks, audit actor/old/new/reason and immutable UPDATE/DELETE trigger. Login throttling blocks eight failures per email/client address for 15 minutes; unknown accounts verify a dummy hash. Frontend text escaping, CSV formula handling, CSP/no-store/nosniff/frame headers; env ignored by Git.

## Limitations

- Portfolio-grade, not enterprise security or production certification. Synthetic shared demo credentials include Admin powers.
- No MFA, reset-email flow, verification, SSO, refresh token rotation, session-device UI, or comprehensive abuse/WAF protection.
- Throttling uses ASGI client IP, without trusting arbitrary forwarded headers; proxies can make users share apparent IP.
- Team strings/one assignee; no multi-tenant organization layer or complex ACLs.
- Duplicate constraints are owner-scoped for privacy, not global customer identity resolution.
- A separate least-privilege runtime SQL role now has no audit UPDATE/DELETE/TRUNCATE or schema ownership/CREATE. Offline migration owners can still override protections; audit is not a cryptographic external ledger.
- READ COMMITTED UI snapshots can span concurrent commits. Revision guards writes, not snapshot consistency.
- UI collections use server search/filter/offset pagination with stable ordering, max 100 rows/request, batched company lookup, scoped SQL metrics, and related lookups. No large-scale load test or cursor pagination is claimed. Explicit JSON export still materializes visible data and is intended for low demo volumes.
- UI app.js remains large; future growth should split page/form modules.
- Import is data migration with new IDs/timestamps/ownership, not exact restore; audit actors cannot be forged from backup.
- Provider storage/DB permissions protect secrets at rest; no app-level field encryption. Demo must use fictitious data only.
- Explicit migrations/seed; offline pg_dump/checksum and guarded local restore-drill tooling are provided. Backup schedules/offsite retention and production recovery objectives still require an operational decision. See FREE-HARDENING.md and its verification record.
- Two automated Chromium E2E flows now run locally/CI in addition to tool-assisted hosted checks; these do not constitute exhaustive cross-browser E2E, penetration testing, or load testing.
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
