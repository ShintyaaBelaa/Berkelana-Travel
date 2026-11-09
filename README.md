# 🧭 Berkelana Travel — Sistem Administrasi

Aplikasi administrasi travel berbasis **Python, Streamlit, dan SQLite** untuk
membantu petugas loket mencatat pelanggan, mengelola rute dan kursi, membuat
pemesanan tiket, memeriksa ketersediaan kursi, mencetak nota, serta mencari dan
membatalkan transaksi.

Aplikasi dibuat **tanpa login** dan sepenuhnya berjalan lokal di komputer
(SQLite tidak memerlukan server database terpisah).

---

## ✨ Fitur

| Menu | Fitur |
|---|---|
| **Dashboard** | Ringkasan pelanggan, rute aktif, pemesanan, tiket, pendapatan, keberangkatan terdekat, rute populer, jadwal terpadat, dan grafik pendapatan. |
| **Pelanggan** | Tambah, cari, lihat detail, ubah, dan hapus pelanggan. Mencegah nama + nomor telepon ganda. |
| **Rute & Tarif** | Tambah, cari, ubah rute/tarif/status, lihat tiga kode jadwal per rute, nonaktifkan jadwal tertentu (misalnya hanya pukul 07:00), dan hapus rute yang belum terpakai. Rute terpakai hanya boleh dinonaktifkan. |
| **Data Kursi** | Denah kursi, tambah, cari, ubah nomor/status, dan hapus kursi yang belum terpakai. |
| **Pemesanan Tiket** | Tambah pelanggan cepat, pilih pelanggan/rute/tanggal/kode jadwal, denah kursi real-time, pilih beberapa kursi, hitung total otomatis, simpan transaksi, dan unduh nota. |
| **Riwayat Pemesanan** | Pencarian multi-kriteria, filter rute dan rentang tanggal, unduh CSV, detail transaksi, nota, dan pembatalan dengan konfirmasi. |
| **Log Aktivitas** | Jejak audit otomatis untuk penambahan, perubahan, penghapusan, dan pembatalan data. Bisa difilter dan diunduh CSV. |

### Yang sengaja tidak dibuat (sesuai ruang lingkup)

- Login dan pembagian hak akses
- Pemesanan mandiri oleh pelanggan
- Pembayaran digital/integrasi bank
- Refund otomatis (pengembalian dana di luar sistem)
- Pengiriman tiket via WhatsApp/email
- Laporan pendapatan bulanan lengkap
- Pengelolaan armada menyeluruh

---

## 🚀 Cara Menjalankan

### 1. Masuk ke folder proyek

```powershell
cd "C:\Users\ASUS\Downloads\New folder\berkelana_travel"
```

### 2. Buat virtual environment (opsional, disarankan)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Pasang dependensi

```powershell
pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```powershell
streamlit run app.py
```

Browser akan terbuka otomatis pada alamat `http://localhost:8501`.

> Jika PowerShell menolak aktivasi virtual environment, jalankan
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` lalu ulangi aktivasi.

### Data contoh

Saat aplikasi pertama kali dijalankan, file `berkelana.db` dibuat otomatis
beserta **data contoh** (6 pelanggan, 5 rute, 15 jadwal, 8 kursi K1–K8, dan 14
transaksi dengan tanggal relatif terhadap hari ini). Data contoh hanya dibuat
sekali saat database baru dibuat.

Kelima rute berangkat dari Semarang dengan tarif dan kode bisnis berikut:

| Rute | Tarif | Kode jadwal (07:00 / 12:00 / 17:00 WIB) |
|---|---|---|
| Semarang → Yogyakarta | Rp85.000 | `SY001` / `SY002` / `SY003` |
| Semarang → Solo | Rp75.000 | `SS001` / `SS002` / `SS003` |
| Semarang → Jepara | Rp75.000 | `SJ001` / `SJ002` / `SJ003` |
| Semarang → Kudus | Rp80.000 | `SK001` / `SK002` / `SK003` |
| Semarang → Pati | Rp90.000 | `SP001` / `SP002` / `SP003` |

Tiga digit terakhir menunjukkan urutan keberangkatan: `001` untuk pukul 07:00,
`002` untuk pukul 12:00, dan `003` untuk pukul 17:00.

Untuk memulai dari database kosong:

1. Hentikan aplikasi (`Ctrl+C`).
2. Hapus `berkelana.db`, `berkelana.db-wal`, dan `berkelana.db-shm` (jika ada).
3. Jalankan `streamlit run app.py` kembali.

Database kosong tetap berisi 8 kursi awal K1–K8 dan counter kode. Pelanggan,
rute, dan transaksi dapat ditambahkan melalui aplikasi.

---

## 🧪 Menjalankan Pengujian

Pengujian aturan bisnis menggunakan `unittest` dan database sementara, sehingga
tidak mengubah data aplikasi:

```powershell
python -m unittest discover -s tests -v
```

Cakupan pengujian (34 skenario):

- Pelanggan ganda dan validasi nomor telepon
- Validasi rute (kota asal ≠ tujuan, tarif > 0, rute ganda ditolak)
- Pembuatan tiga jadwal otomatis dengan kode `SS001`–`SS003`
- Penghapusan rute/pelanggan yang sudah dipakai
- Nomor kursi unik dan berpola K + angka
- Kursi nonaktif tidak dapat dipesan
- Minimal satu kursi dan larangan kursi ganda dalam satu transaksi
- Kursi yang sama tidak boleh dipesan pada rute + tanggal + jam yang sama
- Kursi yang sama tetap boleh dipesan pada tanggal berbeda
- Penolakan jadwal yang sudah lewat dan jam di luar 07:00/12:00/17:00
- Penonaktifan satu jam keberangkatan tanpa menutup jam lain pada rute yang sama
- Status jadwal tetap tersimpan saat rute dinonaktifkan lalu diaktifkan kembali
- Perhitungan total dan penguncian harga saat pemesanan
- Kode jadwal tersimpan pada detail pemesanan
- Kursi kembali tersedia setelah pembatalan
- Kode pemesanan tidak digunakan ulang setelah pembatalan
- Trigger database sebagai pengaman terakhir kursi ganda
- Inisialisasi data contoh (5 rute, 15 jadwal, 14 transaksi)

---

## 🗂️ Struktur Proyek

```text
berkelana_travel/
├── app.py                  # Titik masuk Streamlit, navigasi, sidebar
├── database.py             # Skema SQLite, CRUD, transaksi, aturan bisnis
├── utils.py                # Format rupiah/tanggal, label waktu, teks nota
├── components.py           # CSS, kartu metrik, denah kursi, nota, badge
├── assets/
│   ├── logo.png            # Logo asli Berkelana Travel
│   ├── logo-sidebar.png    # Logo ukuran sidebar (di-embed ke HTML)
│   └── favicon.png         # Ikon tab browser
├── tampilan/
│   ├── dashboard.py        # Dashboard ringkasan
│   ├── pemesanan.py        # Form pemesanan 4 langkah
│   ├── riwayat.py          # Pencarian, detail, nota, pembatalan
│   ├── pelanggan.py        # Pengelolaan pelanggan
│   ├── rute.py             # Pengelolaan rute & tarif
│   ├── kursi.py            # Pengelolaan kursi
│   └── log.py              # Log aktivitas
├── tests/
│   └── test_database.py    # 34 pengujian aturan bisnis
├── .streamlit/
│   └── config.toml         # Tema warna aplikasi
├── requirements.txt
├── berkelana.db            # Dibuat otomatis (tidak disertakan di repo)
└── README.md
```

Pemisahan antarmuka (`tampilan/`, `components.py`) dan pengelolaan database
(`database.py`) mengikuti kebutuhan non-fungsional agar kode mudah diperiksa.

---

## 🗄️ Struktur Database

### `pelanggan`

| Kolom | Keterangan |
|---|---|
| `id_pelanggan` | Primary key teknis |
| `kode_pelanggan` | Kode bisnis unik, contoh `P001` |
| `nama_pelanggan` | Nama, tidak boleh kosong |
| `nomor_telepon` | Hanya angka, tidak boleh kosong |
| `dibuat_pada` | Waktu dibuat |

Constraint unik: pasangan **nama + nomor telepon** (nama tidak peka huruf besar/kecil).

### `rute`

| Kolom | Keterangan |
|---|---|
| `id_rute` | Primary key teknis |
| `kode_rute` | Prefix kode bisnis unik, contoh `SY` |
| `kota_asal`, `kota_tujuan` | Wajib berbeda; satu pasangan rute hanya boleh terdaftar sekali |
| `harga_tiket` | Harus > 0 |
| `aktif` | `1` aktif / `0` nonaktif |
| `dibuat_pada` | Waktu dibuat |

### `jadwal`

| Kolom | Keterangan |
|---|---|
| `id_jadwal` | Primary key teknis |
| `id_rute` | Foreign key rute (cascade) |
| `kode_jadwal` | Kode bisnis unik, contoh `SY001` |
| `jam_keberangkatan` | `07:00`, `12:00`, atau `17:00` |
| `urut_keberangkatan` | `1`, `2`, atau `3` |
| `aktif` | Mengikuti status rute |
| `dibuat_pada` | Waktu dibuat |

Setiap rute otomatis memiliki tiga jadwal. Kode dibentuk dari prefix rute dan
nomor urut tiga digit. Kode dan jam tidak berubah saat tarif atau nama kota
diperbarui agar riwayat transaksi tetap konsisten.

Status jadwal dapat diatur per jam. Menonaktifkan `SS001` hanya menutup
keberangkatan pukul 07:00; `SS002` (12:00) dan `SS003` (17:00) tetap dapat
dipesan selama rutenya aktif. Status masing-masing jadwal tidak berubah saat
rute dinonaktifkan lalu diaktifkan kembali.

### `kursi`

| Kolom | Keterangan |
|---|---|
| `id_kursi` | Primary key teknis |
| `nomor_kursi` | Unik, pola `K` + angka, contoh `K1` |
| `status_aktif` | `1` aktif / `0` nonaktif |

### `pemesanan`

| Kolom | Keterangan |
|---|---|
| `id_pemesanan` | Primary key teknis |
| `kode_pemesanan` | Kode bisnis unik, contoh `PSN001` |
| `id_pelanggan` | Foreign key pelanggan |
| `id_rute` | Foreign key rute |
| `tanggal_keberangkatan` | Format `YYYY-MM-DD` |
| `jam_keberangkatan` | Format `HH:MM` |
| `jumlah_pesan_tiket` | Jumlah kursi yang dipilih |
| `harga_saat_pemesanan` | Snapshot tarif saat transaksi |
| `total_harga` | `jumlah_pesan_tiket × harga_saat_pemesanan` |
| `dibuat_pada` | Waktu transaksi dibuat |

### `detail_pemesanan`

| Kolom | Keterangan |
|---|---|
| `id_detail_pemesanan` | Primary key teknis |
| `id_pemesanan` | Foreign key pemesanan (cascade delete) |
| `id_kursi` | Foreign key kursi |
| `harga_satuan` | Snapshot harga per kursi |

Trigger `trg_cegah_kursi_ganda` menolak kursi yang sama pada kombinasi
**rute + tanggal + jam** yang sama, walaupun pengecekan antarmuka terlewati.

### Tabel pendukung

- `counter` — nomor urut kode bisnis (`P`, `PSN`) agar kode tidak dipakai ulang.
- `log_aktivitas` — jejak audit perubahan data.

---

## 📋 Aturan Bisnis yang Diterapkan

| Aturan | Implementasi |
|---|---|
| **B01** Data pelanggan wajib valid | Nama & telepon wajib diisi; telepon hanya angka. |
| **B02** Pelanggan tidak boleh ganda | Constraint unik nama + telepon dan pesan penolakan jelas. |
| **B03** Rute harus benar | Asal ≠ tujuan; tarif > 0; rute ganda ditolak; kode otomatis. |
| **B04** Rute tidak dihapus jika terpakai | Penghapusan ditolak; admin diarahkan menonaktifkan rute. |
| **B05** Data harus terdaftar | Pelanggan harus ada dan rute/jadwal harus aktif. |
| **B06** Jam keberangkatan | Hanya 07:00, 12:00, dan 17:00 WIB; jadwal yang sudah lewat atau dinonaktifkan ditolak. |
| **B07** Minimal satu kursi | Pemesanan tanpa kursi atau dengan kursi duplikat ditolak. |
| **B08** Kursi tidak boleh sama | Dicek per rute + tanggal + jam, diperkuat trigger database. |
| **B09** Harga saat pemesanan | Harga disimpan di `harga_saat_pemesanan` dan `total_harga`. |
| **B10** Pembatalan | Pemesanan + detail dihapus, kursi kembali tersedia, refund di luar sistem. |

---

## 🧭 Alur Pemakaian Singkat

1. Buka menu **Pelanggan** → tambahkan pelanggan.
2. Buka menu **Rute & Tarif** → pastikan rute aktif dan tarif benar.
3. Buka menu **Data Kursi** → atur kursi yang dijual.
4. Buka menu **Pemesanan Tiket**:
   - Pilih pelanggan.
   - Pilih rute, tanggal, dan kode jadwal (07:00/12:00/17:00 WIB).
   - Pilih kursi yang berwarna hijau.
   - Periksa total, lalu konfirmasi.
   - Unduh/cetak nota.
5. Buka menu **Riwayat Pemesanan** untuk mencari transaksi, membuka nota,
   atau membatalkan pemesanan.
6. Pantau operasional pada menu **Dashboard** dan **Log Aktivitas**.

---

## 🛠️ Troubleshooting

| Masalah | Solusi |
|---|---|
| Port 8501 sudah dipakai | Jalankan `streamlit run app.py --server.port 8502`. |
| Database terkunci | Pastikan hanya satu proses aplikasi yang memakai file DB; hentikan proses lain. |
| Data contoh tidak muncul | Database sudah ada. Hapus `berkelana.db*` lalu jalankan ulang. |
| `streamlit` tidak dikenali | Aktifkan virtual environment atau gunakan `python -m streamlit run app.py`. |
| Tampilan CSS tidak berubah | Lakukan hard refresh browser (`Ctrl+F5`). |

---

## 🔐 Catatan

- Tidak ada autentikasi/login; aplikasi dirancang untuk komputer petugas loket.
- Semua data tersimpan di `berkelana.db` pada folder proyek.
- Pembayaran, refund, dan pengiriman tiket dilakukan di luar sistem.
- Nota tersedia sebagai file teks yang dapat diunduh dan dicetak.
