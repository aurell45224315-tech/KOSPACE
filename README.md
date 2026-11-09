# 🏡 KOSPACE — Sistem Administrasi Pengelolaan Kos

Aplikasi administrasi kos untuk **satu pengguna (pemilik kos)** tanpa login. Dibangun dengan **Python**, **Streamlit**, dan **SQLite**, dijalankan secara lokal melalui terminal VS Code.

Seluruh antarmuka menggunakan **Bahasa Indonesia**. Penghuni tidak memiliki akses ke aplikasi; pencatatan dilakukan sepenuhnya oleh pemilik kos.

---

## ✨ Fitur utama

| Halaman | Isi |
|---|---|
| 🏠 **Dashboard** | Ringkasan kamar, okupansi, penerimaan bulan ini, tunggakan, grafik pendapatan 6 bulan, pembayaran terbaru, sewa aktif, dan aktivitas terakhir. |
| 🚪 **Kamar** | Daftar dan filter 25 kamar, rekap per tipe, tambah kamar, detail kamar, ubah, dan hapus dengan pengaman B10. |
| 👤 **Penghuni** | Daftar dan pencarian penghuni, tambah, detail profil, riwayat sewa/pembayaran, ubah, dan hapus dengan pengaman B10. |
| 📄 **Sewa** | Daftar kontrak, pembuatan sewa dengan deteksi bentrok, detail tagihan per periode, catat pembayaran, akhiri sewa, ubah tanggal/harga, dan hapus dengan pengaman B10. |
| 💳 **Pembayaran** | Daftar tagihan per periode dengan status otomatis, pencatatan pembayaran, riwayat transaksi, detail pembayaran, dan koreksi/hapus pembayaran. |
| 🕘 **Riwayat** | Riwayat per penghuni, riwayat per kamar, linimasa transaksi, dan log aktivitas sistem. |
| ⚙️ **Pengaturan** | Informasi database, muat ulang data contoh, hapus transaksi, bersihkan penghuni, reset total, ekspor CSV/ZIP, dokumentasi aturan bisnis, dan profil tim. |

Fitur pendukung:

- Status **kamar**, **sewa**, dan **pembayaran** diperbarui otomatis.
- Pencegahan **jadwal sewa bertabrakan** pada kamar yang sama.
- **Harga sewa disalin** saat kontrak dibuat agar riwayat tidak berubah ketika harga kamar berubah.
- **Log aktivitas** untuk tambah, ubah, hapus, pembayaran, dan reset.
- Ekspor data ke **CSV** dan **ZIP berisi 5 CSV**.
- Pesan kesalahan yang ramah untuk pelanggaran aturan bisnis.
- Tombol aksi pada Dashboard langsung membuka tab yang dituju (mis. **Catat pembayaran** membuka tab pencatatan).
- Tampilan responsif dengan sidebar, kartu statistik, badge status, dan grafik.

---

## 🧱 Teknologi

- **Python 3.10+** (diuji pada Python 3.14)
- **Streamlit** 1.50+ (diuji pada 1.63)
- **SQLite** (modul bawaan Python)
- **pandas** 2.0+ (tabel dan ekspor CSV)
- **Altair** 5.0+ (grafik bawaan Streamlit)

---

## 🚀 Cara menjalankan

### 1. Buka folder proyek di VS Code

Buka terminal VS Code, lalu masuk ke folder proyek:

```powershell
cd "C:\Users\LENOVO\Downloads\KOSPACE FINAL"
```

### 2. (Disarankan) Buat virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Jika PowerShell menolak aktivasi, jalankan sekali:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Pasang dependensi

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```powershell
streamlit run app.py
```

Atau:

```powershell
python -m streamlit run app.py
```

Browser akan terbuka otomatis di `http://localhost:8501`.

### 5. Menghentikan aplikasi

Tekan `Ctrl + C` di terminal.

---

## 💾 Database

- Lokasi: `kospace.db` di folder proyek yang sama dengan `app.py`.
- Format tanggal di database: **YYYY-MM-DD**.
- Format tanggal di tampilan: **DD-MM-YYYY**.
- Foreign key SQLite selalu diaktifkan (`PRAGMA foreign_keys = ON`).
- Database, 25 kamar, dan data contoh dibuat otomatis pada saat aplikasi pertama kali dijalankan.

### Skema utama

| Tabel | Primary Key | Atribut |
|---|---|---|
| `kamar` | `id_kamar` | `nomor_kamar` (unik), `tipe`, `harga_bulanan`, `fasilitas`, `status` |
| `penghuni` | `id_penghuni` | `nama`, `telepon`, `telepon_ortu`, `alamat` |
| `sewa` | `id_sewa` | `id_penghuni` (FK), `id_kamar` (FK), `tanggal_mulai`, `tanggal_selesai`, `durasi`, `harga_bulanan`, `status_sewa` |
| `pembayaran` | `id_pembayaran` | `id_sewa` (FK), `periode_bulan`, `periode_tahun`, `tanggal_bayar`, `nominal`, `status_pembayaran` |

Tabel tambahan:

- `log_aktivitas` — jejak aktivitas sistem.
- `meta` — penanda inisialisasi dan status data contoh.

### Format ID otomatis

| Entitas | Format | Contoh |
|---|---|---|
| Kamar | `K` + 3 digit | `K001` |
| Penghuni | `P` + 3 digit | `P001` |
| Sewa | `S` + 3 digit | `S001` |
| Pembayaran | `BY` + 3 digit | `BY001` |

Nomor kamar (A01, B01, C01) adalah kode bisnis yang dikenal pemilik dan **harus unik**.

---

## 📐 Data kamar standar

| Tipe | Nomor | Jumlah | Harga/bulan | Fasilitas |
|---|---|---|---|---|
| Tipe A | A01–A05 | 5 | Rp1.300.000 | AC, Wi-Fi, kamar mandi dalam |
| Tipe B | B01–B10 | 10 | Rp950.000 | AC, Wi-Fi, kamar mandi luar |
| Tipe C | C01–C10 | 10 | Rp700.000 | Kipas angin, Wi-Fi, kamar mandi luar |

Total: **25 kamar**.

---

## 📋 Aturan bisnis yang diterapkan

### B01 — Nomor kamar unik
Nomor kamar tidak boleh sama dengan kamar lain. Sistem menolak penambahan atau perubahan nomor yang sudah dipakai.

### B06 — Tanggal selesai setelah tanggal mulai
Sewa ditolak jika `tanggal_selesai <= tanggal_mulai`. Untuk mode durasi otomatis, tanggal selesai dihitung inklusif:
`selesai = tanggal_mulai + durasi bulan − 1 hari`.

### B08 — Nominal pembayaran
Nominal harus **lebih dari 0** dan **sama dengan `harga_bulanan` pada sewa**. Pembayaran sebagian belum didukung. Nominal berbeda ditolak dengan pesan yang menjelaskan harga yang benar.

### B10 — Larangan hapus data yang memiliki riwayat
- Kamar tidak bisa dihapus jika memiliki riwayat sewa.
- Penghuni tidak bisa dihapus jika memiliki catatan sewa.
- Sewa tidak bisa dihapus jika sudah memiliki pembayaran.
- Pembayaran boleh dihapus untuk memperbaiki salah catat.

### B14 — Satu periode hanya sekali
Satu sewa hanya boleh memiliki satu pembayaran untuk kombinasi bulan dan tahun yang sama. Upaya pembayaran ganda ditolak. Database juga memiliki `UNIQUE (id_sewa, periode_bulan, periode_tahun)`.

### Deteksi jadwal bertabrakan
Dua sewa pada kamar yang sama dianggap bentrok jika:

```
mulai_baru <= selesai_lama  DAN  selesai_baru >= mulai_lama
```

Sistem menampilkan detail sewa yang bentrok dan menyarankan tanggal mulai setelah sewa terakhir berakhir. Pemeriksaan dilakukan saat membuat dan mengubah sewa.

### Status otomatis

**Status kamar**
- `Ditempati` — ada sewa `Aktif` yang mencakup tanggal hari ini.
- `Tersedia` — tidak ada sewa seperti itu.

**Status sewa**
- `Aktif` — tanggal selesai belum terlewati.
- `Selesai` — tanggal selesai sudah terlewati, atau sewa diakhiri lebih awal.

**Status pembayaran per periode**
- `Lunas` — pembayaran periode tersebut sudah dicatat.
- `Belum Dibayar` — belum dibayar dan belum melewati jatuh tempo.
- `Terlambat` — belum dibayar dan sudah melewati jatuh tempo.

Jatuh tempo adalah **tanggal 10** setiap bulan. Untuk periode pertama, jatuh tempo tidak boleh mendahului tanggal masuk sewa.

### Normalisasi basis data
- **1NF** — setiap kolom berisi satu nilai dan setiap tabel memiliki primary key.
- **2NF** — primary key satu kolom, sehingga tidak ada ketergantungan parsial.
- **3NF** — data penghuni dan kamar tidak diduplikasi di sewa/pembayaran, kecuali `harga_bulanan` yang sengaja disalin sebagai snapshot harga kontrak.

---

## 🧪 Data contoh

Pada run pertama, aplikasi otomatis mengisi:

- 25 kamar standar.
- 6 penghuni contoh.
- 6 kontrak sewa dengan tanggal relatif terhadap hari ini.
- 16 pembayaran, termasuk satu periode yang sengaja terlambat untuk menguji status `Terlambat`.

Data contoh dapat dimuat ulang atau dihapus melalui **Pengaturan → Database**.

> **Penting:** menu **Muat ulang data contoh** menghapus seluruh sewa, pembayaran, dan penghuni, lalu mengisi ulang data contoh. Gunakan dengan hati-hati.

### Reset

- **Hapus semua sewa & pembayaran** — mempertahankan kamar dan penghuni.
- **Bersihkan penghuni tanpa riwayat** — hanya menghapus penghuni yang belum pernah memiliki sewa.
- **Reset total** — menghapus semua data dan membuat ulang 25 kamar kosong. Konfirmasi dengan mengetik `RESET`.

Untuk memulai dari nol sepenuhnya, hentikan aplikasi, hapus `kospace.db`, lalu jalankan ulang. Database baru akan dibuat beserta data contoh.

---

## 📤 Ekspor data

Di **Pengaturan → Ekspor data** tersedia:

- ZIP berisi `kamar.csv`, `penghuni.csv`, `sewa.csv`, `pembayaran.csv`, dan `tagihan.csv`.
- Unduhan CSV terpisah untuk setiap entitas.
- CSV menggunakan encoding UTF-8 dan tanggal format database `YYYY-MM-DD` agar mudah diolah di Excel.

Daftar tagihan dan riwayat pembayaran juga dapat diunduh langsung dari halaman **Pembayaran**, sedangkan linimasa dan log dapat diunduh dari halaman **Riwayat**.

---

## 📁 Struktur proyek

```text
KOSPACE FINAL/
├── app.py                     # Entry point Streamlit, sidebar, navigasi
├── requirements.txt           # Dependensi Python
├── README.md
├── kospace.db                 # Database SQLite (dibuat otomatis)
├── .streamlit/
│   └── config.toml            # Tema dan konfigurasi server
└── kospace/
    ├── __init__.py
    ├── db.py                  # Skema, koneksi, query baca, seed kamar
    ├── logic.py               # Aturan bisnis, validasi, status, laporan
    ├── ui.py                  # CSS, komponen tampilan, format, navigasi
    ├── components.py          # Form pembayaran yang dipakai ulang
    └── views/
        ├── dashboard.py
        ├── kamar.py
        ├── penghuni.py
        ├── sewa.py
        ├── pembayaran.py
        ├── riwayat.py
        └── pengaturan.py
```

---

## 🛠️ Pemecahan masalah

| Masalah | Solusi |
|---|---|
| `streamlit: command not found` | Jalankan `python -m streamlit run app.py` atau pastikan virtual environment aktif. |
| Port 8501 sudah dipakai | Jalankan `python -m streamlit run app.py --server.port 8502`. |
| Perubahan kode tidak muncul | Muat ulang browser atau hentikan lalu jalankan ulang Streamlit. |
| Data ingin dikembalikan ke contoh | **Pengaturan → Database → Muat ulang data contoh**. |
| Aplikasi ingin benar-benar kosong | **Pengaturan → Database → Reset total** atau hapus `kospace.db` saat aplikasi berhenti. |
| Database terkunci | Pastikan hanya satu proses Streamlit yang berjalan dan tutup koneksi lain ke `kospace.db`. |

---

## 🔒 Batasan versi ini

- Tanpa login dan tanpa akses untuk penghuni.
- Belum ada pembayaran online.
- Belum ada deposit, token listrik, kuitansi, atau pengingat WhatsApp.
- Belum ada deployment ke internet; aplikasi dirancang untuk berjalan lokal.
- Nominal pembayaran harus penuh sesuai harga sewa (tidak ada pembayaran sebagian).

---

## 👩‍💻 Tim penyusun

**Kelompok 4** — Pemrograman Bisnis & Perancangan Sistem Administrasi

| Nama | NIM |
|---|---|
| Alya Nafisah | 4.52.24.3.02 |
| Marensya Aurellya | 4.52.24.3.15 |
| Permata Rayya A. A. | 4.52.24.3.21 |
| Shintia Nova P. A. | 4.52.24.3.25 |

Dosen pengampu: **Dwi Budi Santoso, S.Kom., M.Kom.**

---

© 2026 KOSPACE · Sistem Administrasi Pengelolaan Kos
