# Portfolio case study

Personal project for a fictional web studio. The v1 browser-local CRM already demonstrated the sales workflow; v2 upgrades persistence, multi-user authorization, transactional business commands, and manager analytics while keeping the interface.

Choices worth discussing: keeping vanilla JS reduced redesign scope; owner-scoped dedup avoids cross-rep privacy leaks; business commands separate assignment/stage transitions from generic edits; Lost/reopen protect metric consistency; Argon2 + DB-reloaded JWT sessions avoid trusting role claims; PostgreSQL tests exercise actual locks, triggers, transactions, and constraints; Alembic runs explicitly before deployment rather than on every serverless request.

No real-company rollout, revenue impact, conversion-rate improvement, or production-security claim is made. Metrics are calculated using synthetic examples; check VERIFICATION.md for actual local/deployment evidence.

Honest portfolio wording: “Built a B2B CRM portfolio application with a preserved vanilla JavaScript UI, FastAPI/PostgreSQL backend, role/ownership authorization, transactional lead conversion, application audit history protected by PostgreSQL, and manager analytics. Verified business rules with PostgreSQL integration tests.” Add a live link only after public full-stack deployment is tested.
