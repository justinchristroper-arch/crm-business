# CRM Business — portfolio handoff

**Project name:** CRM Business

**One-line description:** CRM B2B dengan alur lead hingga Won/Lost, akses berbasis role, follow-up, audit perubahan, dan analitik tim menggunakan FastAPI serta PostgreSQL.

**Live demo:** https://crm-business-sigma.vercel.app

**GitHub:** https://github.com/justinchristroper-arch/crm-business

**Stack:** HTML, CSS, JavaScript ES modules, Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Argon2id, JWT/HttpOnly cookies, pytest, Node.js tests, ESLint, Ruff, GitHub Actions, Vercel Hobby, Neon Free.

## Suggested project card

> Aplikasi CRM B2B full-stack untuk mengelola lead, perusahaan, kontak, peluang penjualan, dan tugas follow-up. Mendukung Sales, Manager, dan Admin dengan aturan akses di server, konversi lead dalam satu transaksi, audit perubahan, serta dashboard pipeline dan performa tim. Dibangun sebagai proyek belajar dan portfolio dengan data fiktif.

Buttons for the existing portfolio website (the website itself has not been edited):

```html
<a href="https://crm-business-sigma.vercel.app" target="_blank" rel="noopener noreferrer">Live Demo</a>
<a href="https://github.com/justinchristroper-arch/crm-business" target="_blank" rel="noopener noreferrer">Source Code</a>
```

Open the demo in a new tab; iframe embedding is blocked by frame protection.

## Three resume bullets

- Built and deployed a full-stack B2B CRM using vanilla JavaScript, FastAPI, SQLAlchemy, and Neon PostgreSQL with a same-origin Vercel deployment.
- Implemented server-enforced role/ownership access, transactional lead conversion, Won/Lost/reopen rules, task follow-up, and PostgreSQL-protected application audit history.
- Validated business rules with 29 PostgreSQL integration tests, 3 frontend tests, CI lint/build/migration checks, and 131 hosted acceptance checks.

## Three portfolio highlights

1. **Alur bisnis lengkap:** lead → perusahaan/kontak → opportunity → Won/Lost, dengan alasan penutupan, reopen, dan follow-up.
2. **Multi-user di server:** cakupan Sales, tim Manager, dan Admin; pemeriksaan izin dan audit tidak bergantung pada tampilan browser.
3. **Bukti implementasi:** database bersama Neon, demo HTTPS publik, CI, hasil pengujian hosted, dan screenshot produksi asli.

## Recommended image

Use [manager-dashboard.png](screenshots/manager-dashboard.png), a real 1440 × 1000 production screenshot. It shows pipeline, sales results, follow-up, and team analytics. Copy this PNG into your portfolio's asset directory when integrating later. More images: [manifest](screenshots/README.md).

## Demo login

Choose **Sales Rep**, **Manager**, or **Admin** on the login screen, then submit. Emails: `rep@crm-demo.example`, `manager@crm-demo.example`, `admin@crm-demo.example`. Demo-only shared password: `PortfolioDemo!2026`.

## Validation and limits

29 backend tests, 3 frontend tests, ESLint, Ruff, asset build, dependency check, Alembic head/no drift, and 131 hosted checks passed. UI inspected at widths 1440, 1280, 768, and 390 px. [Detailed evidence](VERIFICATION.md).

This is a personal portfolio demo, not a real-company deployment. Shared accounts, public Admin powers over fake data, cold starts, Free/Hobby quotas, no MFA/SSO/email password recovery, no multi-tenant organization isolation, and no load test/SLA. Data and dashboard totals may change between visits. No measured revenue or business improvement is claimed.

No paid service or API was activated. The app calls its own FastAPI REST API; no AI/API billing is involved. Hosting/database remain subject to provider Free/Hobby terms and quotas. Custom domains or paid upgrades would require a separate decision.
