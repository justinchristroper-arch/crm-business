# CRM Business

Demo CRM berbahasa Indonesia untuk belajar alur penjualan dan portfolio. Dibuat menggunakan HTML, CSS, dan JavaScript ES modules tanpa dependency runtime.

## Jalankan

Memerlukan Node.js 20+.

```sh
npm run dev
```

Buka http://localhost:3000. Tidak perlu `npm install`, API key, akun database, atau proses build. Verifikasi: `npm run check`.

## Fitur

- Dashboard: nilai deal berhasil pada periode pilihan, pipeline aktif, jumlah kontak, win rate, grafik enam bulan, dan follow-up.
- Kontak: tambah, edit, hapus, pencarian, perusahaan pada profil kontak, ekspor CSV.
- Leads: status dan sumber lead, catatan kebutuhan, konversi ke kontak dengan formulir deal.
- Pipeline: enam tahap, drag-and-drop, pilihan tahap yang dapat digunakan di ponsel/keyboard, nilai penawaran dan target penutupan.
- Tugas: prioritas, tanggal follow-up, penanda terlewat, selesai/buka kembali.
- Laporan: periode 30/90/365 hari, distribusi pipeline, sumber lead, riwayat perubahan.
- Pengaturan: nama workspace, ekspor/impor JSON tervalidasi, reset demo.
- Panduan belajar CRM dan alur penggunaan lengkap.
- Responsive, dialog formulir, label aksesibilitas, dan dukungan reduced motion.

## Model data dan perhitungan

`contacts` menyimpan orang dan nama perusahaannya; perusahaan belum menjadi entitas terpisah. `leads` menyimpan calon klien. `deals` serta `tasks` mengacu ke ID kontak. Kontak yang masih dipakai deal/tugas tidak dapat dihapus. Konversi lead menggunakan email untuk menemukan kontak yang sudah ada.

Nilai deal berhasil adalah nilai kontrak, bukan pembayaran yang diterima. Periode dashboard/laporan berlaku pada metrik penutupan deal. Pipeline dan total kontak menggambarkan data saat ini. Grafik selalu menampilkan enam bulan terakhir. Win rate = deal berhasil / seluruh deal berhasil atau gagal pada periode pilihan. Deal yang dibuka kembali tidak lagi masuk perhitungan penutupan.

## Penyimpanan & batas versi demo

Data fiktif disimpan dalam `localStorage` browser dengan key `crm-business-v1`. Pengunjung memiliki data sendiri; perubahan tidak disinkronkan. Menghapus data browser akan menghapus perubahan. Ekspor backup untuk menyimpannya. Tidak ada login, server API, atau kontrol akses tim dalam versi ini. Jangan memasukkan data pelanggan sungguhan. Google Fonts hanya digunakan untuk tipografi; font sistem menjadi fallback saat offline.

## Deploy gratis & tautkan ke portfolio

Direktori `dist/` berisi seluruh aplikasi siap hosting statis. Dapat dipasang pada subpath; aset memakai URL relatif dan navigasi memakai hash.

### Vercel

Impor repo GitHub sebagai proyek baru, pilih framework **Other**, kosongkan Build Command, dan gunakan Output Directory **dist**. Pakai paket Hobby untuk demo pribadi/nonkomersial dan subdomain bawaan. Tidak ada API key yang perlu diisi. Batas paket dan ketentuan penyedia tetap berlaku.

### GitHub Pages

Workflow `.github/workflows/pages.yml` menerbitkan direktori `dist` saat push ke `main` atau dijalankan manual. Pilih **Settings → Pages → Source → GitHub Actions**. Publikasi memerlukan repo yang mendukung Pages pada paket GitHub Anda.

### Link portfolio

Setelah repo dan hosting publik tersedia, pasang dua tombol pada kartu proyek website portfolio Anda:

```html
<a href="https://DEMO-ANDA.vercel.app" target="_blank" rel="noopener noreferrer">Live Demo</a>
<a href="https://github.com/USERNAME/CRM-Business" target="_blank" rel="noopener noreferrer">Source Code</a>
```

URL di atas adalah placeholder, bukan deployment atau repo yang sudah dibuat. Demo Sites yang dibuat dari chat mulai dengan akses privat; tautan tersebut belum sesuai untuk pengunjung portfolio umum sampai aksesnya dibuka.

## Struktur

```text
dist/index.html      Shell HTML
dist/styles.css     Desain responsive
dist/app.js         Halaman, formulir, interaksi, localStorage
dist/model.js       Data contoh, kalkulasi, validasi backup
tests/              Pengujian logika bisnis
server.mjs          Server preview statis lokal
```

## Pengembangan berikutnya

Tambahkan backend/API dan database, login sungguhan, aturan akses per pengguna, serta perusahaan sebagai tabel tersendiri untuk berlatih full-stack. Integrasi AI, email, dan WhatsApp tidak dibutuhkan versi ini dan harus diperiksa biayanya sebelum diaktifkan.
