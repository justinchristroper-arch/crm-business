# Verifikasi perbaikan audit — 21 Oktober 2026

Demo: **https://crm-business-sigma.vercel.app**. Kode aplikasi yang diuji dan dipromosikan: **c5d599563d24ea1227abbfcf09dd27b957588a1c**, melalui [PR #1](https://github.com/justinchristroper-arch/crm-business/pull/1). Commit dokumentasi berikutnya tidak mengubah kode runtime.

## Hasil

| Pemeriksaan | Bukti |
|---|---|
| Backend PostgreSQL | **42 lulus**, termasuk regression tests audit, assignment, Lead, pagination, sesi, sanitasi error, dan privilege runtime |
| Frontend | **3 lulus**, syntax/ESLint lulus |
| Chromium E2E | **2 lulus**, mencakup konversi detail Lead, Lost/Manager/audit, reload, navigasi mobile dan pagination 55 lead fiktif |
| Ruff, asset build, dependency consistency | Lulus |
| npm audit / pip-audit runtime | Tidak ada advisory yang dikenal ditemukan saat pemeriksaan; bukan jaminan bebas kerentanan |
| Alembic | `0003_lead_details` di Neon dan test; tidak ada schema drift |
| Hosted alur utama | **135 lulus** — [laporan tersanitasi](hardening-hosted-acceptance.json) |
| Hosted regresi hardening | **38 lulus** — [laporan tersanitasi](hosted-hardening-regression.json) |
| Hosted browser | Dashboard Manager desktop 1440 px; Leads/pagination mobile 390 px; lebar body sama dengan viewport; tidak ada HTTP mixed resource atau page error saat inspeksi |
| Runtime DB role | Schema CREATE, audit UPDATE/DELETE/TRUNCATE, dan membership owner seluruhnya false, diverifikasi dengan transaksi read-only |
| Backup/restore drill | Snapshot backup Neon PG18 dipulihkan ke database lokal kosong; checksum, revision dan trigger audit terverifikasi; 95 baris audit saat snapshot |
| GitHub branch protection | main dilindungi, check `verify` wajib/strict termasuk admin, PR wajib tanpa reviewer kedua untuk pemilik tunggal; force-push/delete diblokir |

[CI main yang lulus](https://github.com/justinchristroper-arch/crm-business/actions/runs/39632223158) menjalankan semua quality gates termasuk advisory dan browser E2E. Satu warning deprecation Starlette/httpx pada test client tetap ada; aplikasi dan tes lulus.

## Kasus hosted yang membuktikan perbaikan

- Lead berisi phone/job title dikonversi; hasil Contact mempertahankan kedua nilai.
- Manager mencoba mengganti alasan Lost tanpa change reason: 422. Dengan change reason: tersimpan dan ada event before/after `closing_reason_changed`.
- Perintah stage yang identik mengembalikan revision yang sama.
- Assignment Opportunity tanpa akses parent ditolak 422. Setelah Company dan Contact dibagikan secara eksplisit, assignment diterima dan Sales penerima dapat mengedit deal serta menyelesaikan Task.
- Pencabutan akses parent saat masih diperlukan ditolak 409. Setelah assignment turunan dicabut dahulu, seluruh pencabutan berhasil dan Sales penerima kembali mendapat 404.
- Pagination satu item tetap mengembalikan dashboard total seluruh scope; query dan authorization tetap di server.
- Build staging API/health berhasil dan hash app.js sama dengan source yang diuji, sebelum promosi ke domain publik.

Pemeriksaan hosted hanya mengubah record QA fiktif. Tidak ada token, cookie, connection string, password database, atau dump database dalam laporan yang dipublikasikan. Screenshot sebelumnya tetap merupakan capture nyata bertanggal 6 Oktober; angka dashboard dapat berbeda karena data bersama dan periode waktu.

## Biaya dan batasan

Tetap memakai Vercel Hobby dan Neon Free yang sudah ada. Tidak mengaktifkan trial/upgrade, domain berbayar, Redis, email/SMS, AI, monitoring SaaS atau penyimpanan cloud tambahan. Tooling/test/backup dilakukan dengan perangkat lunak open-source dan runner standar repository publik. Kuota provider tetap berlaku; paket gratis tidak berarti kapasitas tanpa batas.

Ini tetap demo portfolio personal dengan akun bersama. MFA/SSO, pemulihan password email, isolasi tenant, load test skala perusahaan, monitoring/on-call, backup otomatis/offsite dan jaminan SLA/RPO/RTO belum ditambahkan. [Rincian perbaikan dan prosedur operasi](FREE-HARDENING.md) membedakan kontrol yang sudah tersedia dari keputusan operasional berikutnya.
