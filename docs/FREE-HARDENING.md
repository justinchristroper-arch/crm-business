# Perbaikan audit tanpa layanan berbayar

Tanggal: 21 Oktober 2026. Tujuan tetap demo portfolio personal, dengan Vercel Hobby dan Neon Free yang sudah ada. Tidak membeli domain, menambah layanan SaaS, mengaktifkan trial, atau menaikkan paket.

## Perbaikan aplikasi

- Perubahan `closing_reason` pada stage yang sama wajib memiliki alasan perubahan untuk Manager/Admin di luar owner/assignee, dan menghasilkan `closing_reason_changed` dengan before/after/actor/reason. Perintah stage tanpa perubahan menjadi no-op; revision basi tetap ditolak.
- Assignment memeriksa owner dan assignee pada relasi Company→Contact→Opportunity→Task. Assignment yang belum memiliki akses relasi ditolak 422, tanpa membuka akses secara implisit. Pencabutan akses induk ditolak 409 selama masih dibutuhkan record turunan. Berikan akses berurutan: Company, Contact, Opportunity, Task; cabut dari turunan ke induk. Pemeriksaan relasi mengunci row untuk menyelaraskan perubahan bersamaan.
- Lead menyimpan telepon dan jabatan, termasuk edit, konversi ke contact baru, dan impor/ekspor. Contact existing yang dipakai kembali tidak ditimpa diam-diam. Migrasi `0003_lead_details` mempertahankan default database agar versi aplikasi sebelumnya tetap kompatibel saat rolling deployment.
- Dashboard menggunakan agregasi SQL sesuai scope user; nilainya tidak bergantung pada halaman daftar yang sedang dibuka.
- Daftar utama memakai pencarian/filter/pagination server, 50 item per halaman UI, maksimum 100 per permintaan. Endpoint `/api/{resource}/page` menyediakan items/offset/limit/total/has_more. Endpoint list lama dibatasi 100; backup eksplisit tetap mengekspor data yang diizinkan.
- Workspace memuat koleksi terbatas dan lookup relasi yang diperlukan. Nama perusahaan dimuat secara batch, bukan satu query per deal. Form menyediakan pencarian relasi di server. Jumlah relasi Company/Contact dihitung di SQL.
- Logging JSON terstruktur mencatat request ID, route template, status, durasi, dan event keamanan yang diizinkan; tanpa payload, query string, cookie, token, password, atau email. Error 500 memakai pesan umum dan request ID; validation error tidak mengulang password/input sensitif.
- Maksimal lima sesi aktif per akun. Login membersihkan sesi expired/revoked akun tersebut; script maintenance menyediakan dry run dan cleanup auth global. Akun demo ditolak jika `DEMO_MODE=false`, termasuk sesi yang sudah ada.

## Pembatasan database

Role SQL `crm_runtime` dibuat langsung melalui SQL, tanpa keanggotaan owner/neon_superuser, tanpa hak membuat database/role, tanpa schema CREATE/DDL/TRUNCATE. Tabel audit hanya mengizinkan SELECT/INSERT. Tabel aplikasi lain menerima CRUD yang memang dibutuhkan endpoint.

Kredensial pemilik skema digunakan secara offline untuk migrasi dan backup. Connection string/password duplikat yang disediakan integrasi Vercel juga diganti menjadi kredensial runtime; jangan meninggalkan owner URL dalam variabel runtime lain. File kredensial dan backup di-ignore Git. Setelah migrasi tabel baru, terapkan grant yang ditinjau secara eksplisit; jangan memberikan seluruh privilege default pada tabel masa depan.

Provisioning untuk lingkungan baru:

```sh
python -m scripts.runtime_role
```

Jalankan hanya dengan konfigurasi owner/migrasi yang benar. Perintah menulis `.env.runtime.local`, menolak overwrite file atau mengambil alih role existing yang berprivilege/owning objects, dan tidak mencetak secret. Jangan upload file tersebut atau kredensial migrasi. Secret runtime dikonfigurasi ke provider secara privat.

## Operasi gratis

```sh
python -m scripts.maintenance
python -m scripts.maintenance --apply
python -m scripts.database_backup backup --output artifacts/backup-UNIQUE.dump
```

Maintenance tanpa `--apply` hanya menghitung kandidat. Dengan `--apply`, hanya menghapus sesi expired/revoked dan percobaan login lebih lama dari tujuh hari; audit bisnis dipertahankan. Tidak menambah cron/layanan berbayar.

Backup menggunakan pg_dump custom archive dengan snapshot transaksi konsisten dan manifest checksum. Gunakan client PostgreSQL sesuai major server; Neon saat diperiksa memakai PostgreSQL 18. `CRM_POSTGRES_BIN` dapat menunjuk direktori alat lokal. File dump berisi data sensitif meskipun bukan connection string; simpan privat, lindungi/enkapsulasi dengan enkripsi sesuai kebijakan, dan jangan commit.

Restore drill hanya mengizinkan database **loopback kosong** berakhiran `_restore_test`, memakai URL melalui environment `RESTORE_TEST_DATABASE_URL`:

```sh
python -m scripts.database_backup restore-drill --archive artifacts/backup-UNIQUE.dump
```

Perintah memeriksa checksum, menolak database nonkosong, memulihkan dalam satu transaksi, dan memeriksa revision. Ownership/privilege tidak disalin oleh restore; role runtime harus diprovision ulang sebelum target dijadikan lingkungan aplikasi. Perintah ini tidak dapat digunakan langsung untuk overwrite database Neon. JSON ekspor aplikasi tetap merupakan migrasi append, bukan backup pemulihan penuh.

Backup otomatis, retensi offsite, alert pihak ketiga, dan jaminan RPO/RTO belum diaktifkan. Tentukan kebutuhan tersebut sebelum operasional perusahaan; jangan menganggap script manual sebagai pemantauan 24 jam.

**Drill yang dijalankan:** backup snapshot Neon PostgreSQL 18 memakai pg_dump 18, checksum cocok, lalu restore ke database PostgreSQL lokal kosong. Revision `0003_lead_details`, 95 baris audit, dan trigger `crm_audit_immutable` terverifikasi pulih. Data sumber Neon hanya dibaca. Ini membuktikan satu latihan pemulihan, bukan jaminan pemulihan operasional berkelanjutan.

## Quality gates

- Regression tests mencakup alasan Lost/Won melalui stage dan PUT, no-op/revision, assignment dan pencabutan akses, detail lead/impor, scope pagination, agregat, pembatasan sesi, sanitasi error, dan privilege runtime.
- Dua tes Playwright pada database lokal/CI terpisah: lead→contact→opportunity, perubahan Lost dan guard Manager/audit; serta navigasi mobile dan pagination 55 lead.
- CI menjalankan backend/frontend/lint/build/migration/dependency checks, npm audit, pip-audit runtime, dan browser E2E. Actions dipin ke commit SHA; Dependabot disiapkan.
- Gunakan branch protection dengan pemeriksaan `verify` wajib dan larangan force-push/delete. Perubahan melalui PR diuji sebelum merge. Untuk pemilik tunggal, tidak mewajibkan persetujuan reviewer kedua yang tidak tersedia.

## Batasan yang sengaja tetap berlaku

Demo publik tetap menyediakan akun bersama termasuk Admin dengan data fiktif. Website ini tidak diubah menjadi deployment operasional perusahaan. MFA/SSO, pemulihan akun email, multi-tenant, laporan keuangan periode terkunci, dan SLA belum diterapkan. Pembatasan autentikasi saat ini tetap per email+client; belum ada klaim perlindungan DDoS/load test menyeluruh. Eksport/impor JSON dibatasi ukuran/500 record per koleksi, bukan solusi backup skala besar.

Semua perbaikan di atas tidak membutuhkan API berbayar. Vercel Hobby/Neon Free tetap mempunyai kuota dan ketentuan. Jika kuota habis, pertahankan pembatasan paket gratis dan tunggu reset/kurangi penggunaan; tidak mengaktifkan upgrade otomatis. Penggunaan operasional komersial harus memakai hosting dengan ketentuan yang sesuai, terpisah dari demo personal ini.
