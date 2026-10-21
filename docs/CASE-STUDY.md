# Portfolio case study

Personal project for a fictional web studio. The v1 browser-local CRM already demonstrated the sales workflow; v2 upgrades persistence, multi-user authorization, transactional business commands, and manager analytics while keeping the interface.

Choices worth discussing: keeping vanilla JS reduced redesign scope; owner-scoped dedup avoids cross-rep privacy leaks; business commands separate assignment/stage transitions from generic edits; Lost/reopen protect metric consistency; Argon2 + DB-reloaded JWT sessions avoid trusting role claims; PostgreSQL tests exercise actual locks, triggers, transactions, and constraints; Alembic runs explicitly before deployment rather than on every serverless request.

No real-company rollout, revenue impact, conversion-rate improvement, or production-security claim is made. Metrics are calculated using synthetic examples; check VERIFICATION.md for actual local/deployment evidence. The full-stack demo runs on Vercel Hobby with Neon Free PostgreSQL; hosted role/business-rule/analytics checks passed against the real HTTPS application.

Honest portfolio wording: “Built and deployed a B2B CRM portfolio application with a vanilla JavaScript UI, FastAPI/PostgreSQL backend, role/ownership authorization, transactional lead conversion, protected application audit history, scoped SQL analytics and server pagination. Validated with 42 PostgreSQL integration tests, 3 frontend tests, 2 browser E2E flows, 135 hosted acceptance checks and 38 targeted hosted regressions.” [Live demo](https://crm-business-sigma.vercel.app) · [Source code](https://github.com/justinchristroper-arch/crm-business).
