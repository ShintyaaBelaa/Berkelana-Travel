# 🚌 Berkelana Travel — Sistem Administrasi

Aplikasi administrasi travel berbasis **Python, Streamlit, dan SQLite**. Aplikasi
membantu petugas loket mencatat pelanggan, mengelola rute/tarif dan kursi, membuat
pemesanan tiket dengan denah kursi, menghitung total otomatis, mencari riwayat,
mencetak nota, dan membatalkan pemesanan.

Aplikasi berjalan **tanpa login**, sesuai ruang lingkup perancangan, dan seluruh
data disimpan pada file `berkelana.db` di folder proyek.

---

## ✨ Fitur

| Kode | Fitur | Keterangan |
|------|-------|------------|
| F01 | Kelola pelanggan | Tambah, cari, ubah, dan hapus pelanggan yang belum bertransaksi. |
| F02 | Cegah pelanggan ganda | Kombinasi nama + nomor telepon yang sama ditolak. |
| F03 | Kelola rute & tarif | Tambah, ubah tarif, aktif/nonaktif, hapus rute yang belum dipakai. |
| F04 | Kelola kursi | Tambah, ubah nomor/status, hapus kursi yang belum dipakai. |
| F05 | Buat pemesanan | Pilih pelanggan, rute, tanggal, jam, dan kursi. |
| F06 | Cek ketersediaan | Kursi terisi pada jadwal yang sama ditandai dan tidak dapat dipilih. |
| F07 | Hitung total | Total = jumlah kursi × harga saat pemesanan. |
| F08 | Simpan transaksi | Header pemesanan + detail kursi, kode `PSN001`, `PSN002`, … |
| F09 | Cari & batalkan | Pencarian multi-filter, detail nota, ekspor CSV, pembatalan. |
| F10 | Dashboard | Ringkasan pelanggan, rute, pemesanan, tiket, pendapatan, dan okupansi. |

Fitur tambahan: nota dapat diunduh sebagai `.txt` atau `.html` siap cetak,
pengujian otomatis aturan bisnis, dan halaman dokumentasi di dalam aplikasi.

---

## 🧭 Aturan bisnis yang diterapkan

| Kode | Aturan |
|------|--------|
| B01 | Nama & nomor telepon wajib; nomor hanya angka (7–15 digit). |
| B02 | Nama + nomor telepon yang sama tidak boleh didaftarkan dua kali. |
| B03 | Kota asal ≠ kota tujuan dan tarif > 0. |
| B04 | Rute yang sudah dipakai tidak boleh dihapus; hanya bisa dinonaktifkan. |
| B05 | Pelanggan harus terdaftar dan rute harus aktif. |
| B06 | Jadwal keberangkatan harus setelah waktu sekarang. |
| B07 | Minimal satu kursi dan tidak ada kursi ganda dalam satu pemesanan. |
| B08 | Satu kursi tidak boleh dipakai dua kali pada rute + tanggal + jam yang sama. |
| B09 | Harga disimpan per detail saat pemesanan; perubahan tarif tidak mengubah nota lama. |
| B10 | Pembatalan menghapus pemesanan + detail sehingga kursi kembali tersedia. |

Aturan kursi ganda juga dijaga oleh **trigger SQLite** sehingga tetap aman
walaupun dua proses menyimpan secara bersamaan.

---

## 🚀 Menjalankan aplikasi

Prasyarat: **Python 3.10+** (diuji pada Python 3.14).

```bash
# 1. Masuk ke folder proyek
cd "berkelana travel"

# 2. (Opsional) buat virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Pasang dependensi
python -m pip install -r requirements.txt

# 4. Jalankan
streamlit run app.py
```

Buka alamat yang ditampilkan Streamlit (biasanya `http://localhost:8501`).

Di Windows, Anda juga bisa klik dua kali **`jalankan.bat`** — skrip akan
memasang dependensi bila Streamlit belum tersedia, lalu menjalankan aplikasi.

---

## 🗄️ Struktur database

Lima entitas sesuai ERD:

```
pelanggan (1) ─────< pemesanan >───── (1) rute
                         │
                         │ (1)
                         ▼
                  detail_pemesanan
                         ▲
                         │ (1)
                       kursi
```

| Tabel | Kolom penting |
|-------|---------------|
| `pelanggan` | `id_pelanggan` (PK), `kode_pelanggan` (UQ), `nama_pelanggan`, `nomor_telepon` |
| `rute` | `id_rute` (PK), `kode_rute` (UQ), `kota_asal`, `kota_tujuan`, `harga_tiket`, `aktif` |
| `kursi` | `id_kursi` (PK), `nomor_kursi` (UQ), `status_aktif` |
| `pemesanan` | `id_pemesanan` (PK), `kode_pemesanan` (UQ), FK pelanggan & rute, tanggal, jam, jumlah tiket, total |
| `detail_pemesanan` | `id_detail_pemesanan` (PK), FK pemesanan & kursi, `harga_saat_pemesanan` |

Catatan:

- ID teknis memakai `INTEGER AUTOINCREMENT`; kode bisnis (`P001`, `SY001`,
  `PSN001`, `K1`) unik dan dipakai untuk tampilan/pencarian.
- `detail_pemesanan.id_pemesanan` memakai `ON DELETE CASCADE` sehingga detail
  ikut terhapus saat pemesanan dibatalkan.
- Data contoh dibuat otomatis **satu kali** saat database pertama kali dibuat
  (3–5 pemesanan dengan tanggal relatif terhadap hari ini).

---

## 📁 Struktur proyek

```
berkelana travel/
├── app.py                  # Titik masuk Streamlit + navigasi
├── database.py             # Skema SQLite, koneksi, trigger, seed
├── services.py             # Aturan bisnis B01–B10 + query
├── requirements.txt
├── test_aturan_bisnis.py   # 35 pengujian aturan bisnis
├── jalankan.bat            # Peluncur Windows
├── .streamlit/config.toml  # Tema aplikasi
├── berkelana.db            # Dibuat otomatis saat pertama dijalankan
└── ui/
    ├── components.py       # CSS, komponen, nota
    ├── dashboard.py
    ├── pelanggan.py
    ├── rute.py
    ├── kursi.py
    ├── pemesanan.py
    ├── riwayat.py
    └── panduan.py
```

---

## 🧪 Pengujian

```bash
python -m unittest -v test_aturan_bisnis.py
```

Pengujian memakai database sementara di folder temp sehingga **tidak mengubah**
`berkelana.db`. Cakupan: B01–B10, validasi pelanggan/rute/kursi, snapshot harga,
pembatalan, pencarian, dan integritas penghapusan.

---

## 🖨️ Alur pemesanan

1. Buka **Pemesanan Tiket**.
2. Pilih pelanggan (atau tambah pelanggan baru).
3. Pilih rute aktif, tanggal, dan jam keberangkatan.
4. Pilih kursi pada denah. Kursi terisi/nonaktif tidak dapat diklik.
5. Periksa ringkasan total di panel kanan, lalu **Konfirmasi Pemesanan**.
6. Nota muncul dan dapat diunduh sebagai `.txt` atau `.html` untuk dicetak.
7. Riwayat tersedia di menu **Riwayat Pemesanan**, termasuk pembatalan.

---

## 🔐 Catatan penggunaan

- Tidak ada login/pembagian hak akses sesuai ruang lingkup. Jalankan hanya di
  komputer atau jaringan tepercaya.
- Pembayaran dan refund dilakukan **di luar sistem**.
- Cadangkan `berkelana.db` secara berkala. Hentikan aplikasi sebelum menyalin file.
- Ingin memulai dari nol? Hentikan aplikasi, hapus `berkelana.db` (beserta
  `-wal`/`-shm` bila ada), lalu jalankan ulang; data contoh akan dibuat kembali.

---

## 🛠️ Teknologi

- **Python** — logika aplikasi
- **Streamlit** — antarmuka web lokal berbahasa Indonesia
- **SQLite** — database relasional berbasis file
- **Pandas** — tabel dan ekspor CSV
- **Altair** — grafik dashboard
