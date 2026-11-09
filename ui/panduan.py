"""Halaman panduan penggunaan, aturan bisnis, dan dokumentasi teknis."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import database
from ui import components as c

ATURAN = [
    (
        "B01",
        "Data pelanggan wajib diisi",
        ("Nama dan nomor telepon wajib diisi. Nomor telepon hanya boleh berisi angka. "
        "Jika kosong atau mengandung huruf, penyimpanan ditolak."),
    ),
    (
        "B02",
        "Pelanggan tidak boleh ganda",
        ("Pasangan nama + nomor telepon yang sama dengan pelanggan terdaftar ditolak. "
        "Nama yang sama tetap boleh jika nomor teleponnya berbeda."),
    ),
    (
        "B03",
        "Rute harus benar",
        ("Kota asal dan tujuan harus berbeda dan tarif harus lebih besar dari nol. "
        "Rute dengan asal = tujuan atau tarif nol ditolak."),
    ),
    (
        "B04",
        "Rute tidak dihapus jika sudah dipakai",
        ("Rute yang sudah digunakan pada pemesanan tidak boleh dihapus permanen. "
        "Admin dapat menonaktifkannya agar tidak muncul pada pemesanan baru."),
    ),
    (
        "B05",
        "Data harus terdaftar",
        "Pemesanan hanya diterima jika pelanggan terdaftar dan rute berstatus aktif.",
    ),
    (
        "B06",
        "Jam keberangkatan belum terlewati",
        ("Sistem hanya mengizinkan pemesanan untuk jadwal setelah waktu sekarang. "
        "Jadwal yang sudah lewat ditolak."),
    ),
    (
        "B07",
        "Minimal satu kursi",
        ("Setiap pemesanan harus memilih minimal satu kursi. Kursi yang sama tidak "
        "boleh dipilih dua kali dalam satu pemesanan."),
    ),
    (
        "B08",
        "Kursi tidak boleh sama pada jadwal yang sama",
        ("Kursi yang sudah dipesan pada rute + tanggal + jam tertentu tidak bisa "
        "dipakai lagi pada kombinasi jadwal tersebut. Kursi tetap bisa dipakai pada "
        "rute, tanggal, atau jam yang berbeda."),
    ),
    (
        "B09",
        "Harga saat pemesanan",
        ("Jumlah tiket = jumlah kursi yang dipilih. Total = jumlah tiket × harga per "
        "tiket saat pemesanan. Perubahan tarif rute tidak mengubah transaksi lama."),
    ),
    (
        "B10",
        "Pembatalan",
        ("Pembatalan menghapus pemesanan dan detail kursi sehingga kursi kembali "
        "tersedia. Jika pemesanan tidak ditemukan, pembatalan ditolak. Refund di luar sistem."),
    ),
]

FUNGSI = [
    ("F01", "Mengelola data pelanggan", "Tambah, lihat, ubah, hapus (jika belum bertransaksi), dan cari pelanggan."),
    ("F02", "Mencegah pelanggan ganda", "Nama + nomor telepon yang sama ditolak sebagai pelanggan baru."),
    ("F03", "Mengelola rute dan tarif", "Tambah, ubah tarif, aktifkan/nonaktifkan, dan hapus rute yang belum dipakai."),
    ("F04", "Mengelola data kursi", "Tambah, ubah nomor/status, hapus kursi yang belum dipakai, dan cegah nomor ganda."),
    ("F05", "Membuat pemesanan tiket", "Pilih pelanggan, rute, tanggal, jam, dan kursi; simpan serta tampilkan rincian."),
    ("F06", "Memeriksa ketersediaan kursi", "Kursi terisi ditandai dan tidak dapat dipilih pada jadwal yang sama."),
    ("F07", "Menghitung total harga", "Total dihitung otomatis dari jumlah kursi × harga saat pemesanan."),
    ("F08", "Menyimpan transaksi dan detail kursi", "Pemesanan dan detail kursi disimpan, kode PSN tampil pada nota."),
    ("F09", "Mencari, melihat, membatalkan transaksi", "Pencarian multi-filter, detail nota, dan pembatalan."),
    ("F10", "Menampilkan dashboard", "Ringkasan pelanggan, rute, pemesanan, tiket, pendapatan, dan okupansi."),
]

TABEL = [
    (
        "pelanggan",
        "id_pelanggan (PK), kode_pelanggan (UQ), nama_pelanggan, nomor_telepon, dibuat_pada",
        "Nama + nomor telepon unik. Nomor telepon hanya angka. Kode P001, P002, …",
    ),
    (
        "rute",
        "id_rute (PK), kode_rute (UQ), kota_asal, kota_tujuan, harga_tiket, aktif, dibuat_pada",
        "Asal ≠ tujuan, tarif > 0. Kode contoh SY001, SY002, …",
    ),
    (
        "kursi",
        "id_kursi (PK), nomor_kursi (UQ), status_aktif, dibuat_pada",
        "Nomor unik K1–K8 (dapat ditambah K9 dan seterusnya).",
    ),
    (
        "pemesanan",
        "id_pemesanan (PK), kode_pemesanan (UQ), id_pelanggan (FK), id_rute (FK), tanggal_keberangkatan, jam_keberangkatan, jumlah_pesan_tiket, total_harga, dibuat_pada",
        "Header transaksi. Kode PSN001, PSN002, …",
    ),
    (
        "detail_pemesanan",
        "id_detail_pemesanan (PK), id_pemesanan (FK), id_kursi (FK), harga_saat_pemesanan",
        "Satu baris per kursi. Unik per pemesanan + kursi. Harga disalin saat pemesanan.",
    ),
]


def render() -> None:
    c.hero(
        "DOKUMENTASI",
        "Panduan Sistem",
        "Pelajari alur kerja, aturan bisnis, kebutuhan fungsional, dan struktur data "
        "Sistem Administrasi Travel Berkelana.",
        chips=["Bahasa Indonesia", "Streamlit + SQLite", "Tanpa login", "Dijalankan lokal"],
    )

    tab_pakai, tab_aturan, tab_fungsi, tab_data, tab_teknis = st.tabs(
        ["🚀 Cara Pakai", "📜 Aturan Bisnis", "✅ Kebutuhan", "🗄️ Struktur Data", "🛠️ Teknis"]
    )

    with tab_pakai:
        c.section_title("Alur kerja petugas loket", "Enam langkah dari permintaan pelanggan sampai nota.")
        langkah = [
            ("1", "Pilih atau tambah pelanggan", "Buka menu Pemesanan Tiket. Pilih pelanggan yang sudah terdaftar, atau tambahkan pelanggan baru melalui formulir singkat. Nama + nomor telepon ganda akan ditolak."),
            ("2", "Pilih rute dan jadwal", "Pilih rute aktif, tanggal keberangkatan, lalu jam. Sistem menolak jadwal yang sudah terlewati."),
            ("3", "Cek dan pilih kursi", "Denah menampilkan kursi tersedia, terisi, dan nonaktif. Kursi terisi pada rute + tanggal + jam yang sama tidak dapat dipilih."),
            ("4", "Periksa total", "Panel ringkasan menghitung jumlah tiket × harga per tiket secara otomatis. Harga dikunci saat pemesanan disimpan."),
            ("5", "Konfirmasi dan serahkan nota", "Tekan Konfirmasi Pemesanan. Nota dapat diunduh sebagai teks atau HTML cetak."),
            ("6", "Cari atau batalkan", "Menu Riwayat Pemesanan menyediakan pencarian, detail nota, ekspor CSV, dan pembatalan."),
        ]
        for nomor, judul, isi in langkah:
            st.markdown(
                f"""
                <div class="panel" style="margin-bottom:.55rem">
                    <div class="panel-title">{nomor}. {c.esc(judul)}</div>
                    <div class="panel-note">{c.esc(isi)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        c.section_title("Tips penggunaan", "Kebiasaan yang membantu menjaga data tetap rapi.")
        st.markdown(
            """
            - Gunakan pencarian pada menu Data Pelanggan sebelum menambah pelanggan baru.
            - Jangan menonaktifkan rute atau kursi yang masih akan dijual tanpa memastikan jadwalnya.
            - Perubahan tarif rute hanya berlaku untuk transaksi baru; nota lama tidak berubah.
            - Pembatalan menghapus transaksi. Ekspor CSV terlebih dahulu jika data masih dibutuhkan untuk arsip.
            - Database tersimpan di file `berkelana.db` pada folder proyek. Cadangkan file tersebut secara berkala.
            """
        )

    with tab_aturan:
        c.section_title("Aturan bisnis B01–B10", "Diterapkan di lapisan layanan dan sebagian di level database.")
        for kode, judul, isi in ATURAN:
            st.markdown(
                f"""
                <div class="panel" style="margin-bottom:.55rem">
                    <div class="panel-title">{c.badge(kode, 'teal')} &nbsp; {c.esc(judul)}</div>
                    <div class="panel-note">{c.esc(isi)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        c.section_title("Contoh aturan kursi", "Ilustrasi dari dokumen perancangan.")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Pemesanan": "PSN001", "Rute": "SY001", "Tanggal": "20-10-2026", "Jam": "08.00", "Kursi": "K1", "Keterangan": "Diterima"},
                    {"Pemesanan": "PSN002", "Rute": "SY001", "Tanggal": "21-10-2026", "Jam": "08.00", "Kursi": "K1", "Keterangan": "Diterima"},
                    {"Pemesanan": "PSN003", "Rute": "SY001", "Tanggal": "20-10-2026", "Jam": "08.00", "Kursi": "K1", "Keterangan": "Ditolak — kursi sudah dipesan pada jadwal yang sama"},
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    with tab_fungsi:
        c.section_title("Kebutuhan fungsional F01–F10", "Seluruh kebutuhan telah diterapkan pada aplikasi.")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Kode": kode, "Kebutuhan": judul, "Penerapan": isi}
                    for kode, judul, isi in FUNGSI
                ]
            ),
            width="stretch",
            hide_index=True,
        )

        c.section_title("Kebutuhan nonfungsional", "Batasan lingkungan dan kualitas aplikasi.")
        st.markdown(
            """
            - Dijalankan lokal melalui terminal/VS Code dengan perintah `streamlit run app.py`.
            - Antarmuka, pesan kesalahan, dan nota menggunakan bahasa Indonesia.
            - Data disimpan pada SQLite (`berkelana.db`) di folder proyek.
            - Form menggunakan pilihan pelanggan, rute, tanggal, jam, dan kursi.
            - Kesalahan input yang dapat diperkirakan ditampilkan dengan pesan yang mudah dipahami.
            - Kode dipisahkan antara antarmuka (`ui/`), aturan bisnis (`services.py`), dan database (`database.py`).
            - Dependensi dicatat di `requirements.txt` dan pengujian aturan tersedia di `test_aturan_bisnis.py`.
            """
        )

        c.section_title("Ruang lingkup", "Fitur yang tersedia dan yang sengaja tidak dibuat.")
        kol1, kol2 = st.columns(2)
        with kol1:
            st.success(
                "**Tersedia**\n\n"
                "- Dashboard ringkasan\n"
                "- Pengelolaan pelanggan & anti-duplikasi\n"
                "- Pengelolaan rute, tarif, status\n"
                "- Pengelolaan kursi\n"
                "- Pemesanan + denah kursi + total otomatis\n"
                "- Riwayat, pencarian, detail, pembatalan\n"
                "- Penyimpanan SQLite"
            )
        with kol2:
            st.info(
                "**Di luar sistem**\n\n"
                "- Pemesanan mandiri oleh pelanggan\n"
                "- Login dan hak akses\n"
                "- Pembayaran digital / rekening bank\n"
                "- Refund lewat sistem\n"
                "- Tiket otomatis via WhatsApp/email\n"
                "- Laporan pendapatan bulanan lengkap\n"
                "- Pengelolaan armada menyeluruh"
            )

    with tab_data:
        c.section_title("Lima entitas utama", "ERD dinormalisasi sampai 3NF.")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Tabel": tabel, "Kolom": kolom, "Catatan": catatan}
                    for tabel, kolom, catatan in TABEL
                ]
            ),
            width="stretch",
            hide_index=True,
        )

        c.section_title("Relasi", "Arah foreign key dan perilaku penghapusan.")
        st.markdown(
            """
            - `pelanggan (1) ── (N) pemesanan` — pelanggan yang memiliki transaksi tidak dapat dihapus.
            - `rute (1) ── (N) pemesanan` — rute yang sudah dipakai tidak dapat dihapus, hanya dinonaktifkan.
            - `pemesanan (1) ── (N) detail_pemesanan` — detail terhapus otomatis saat pemesanan dibatalkan.
            - `kursi (1) ── (N) detail_pemesanan` — kursi yang sudah dipakai tidak dapat dihapus.
            - Ketersediaan kursi = kursi aktif yang tidak memiliki detail pada rute + tanggal + jam terpilih.
            """
        )

        c.section_title("Skema SQL inti", "Ringkasan DDL yang dijalankan otomatis saat aplikasi mulai.")
        with st.expander("Lihat potongan skema SQL"):
            st.code(
                """
CREATE TABLE pelanggan (
    id_pelanggan    INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pelanggan  TEXT NOT NULL UNIQUE,
    nama_pelanggan  TEXT NOT NULL,
    nomor_telepon   TEXT NOT NULL,
    dibuat_pada     TEXT NOT NULL
);
CREATE UNIQUE INDEX ux_pelanggan_nama_telepon
    ON pelanggan (nama_pelanggan COLLATE NOCASE, nomor_telepon);

CREATE TABLE rute (
    id_rute      INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_rute    TEXT NOT NULL UNIQUE,
    kota_asal    TEXT NOT NULL,
    kota_tujuan  TEXT NOT NULL,
    harga_tiket  INTEGER NOT NULL CHECK (harga_tiket > 0),
    aktif        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE kursi (
    id_kursi      INTEGER PRIMARY KEY AUTOINCREMENT,
    nomor_kursi   TEXT NOT NULL UNIQUE,
    status_aktif  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE pemesanan (
    id_pemesanan           INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pemesanan         TEXT NOT NULL UNIQUE,
    id_pelanggan           INTEGER NOT NULL REFERENCES pelanggan(id_pelanggan),
    id_rute                INTEGER NOT NULL REFERENCES rute(id_rute),
    tanggal_keberangkatan  TEXT NOT NULL,
    jam_keberangkatan      TEXT NOT NULL,
    jumlah_pesan_tiket     INTEGER NOT NULL CHECK (jumlah_pesan_tiket > 0),
    total_harga            INTEGER NOT NULL,
    dibuat_pada            TEXT NOT NULL
);

CREATE TABLE detail_pemesanan (
    id_detail_pemesanan   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pemesanan          INTEGER NOT NULL REFERENCES pemesanan(id_pemesanan)
                              ON DELETE CASCADE,
    id_kursi              INTEGER NOT NULL REFERENCES kursi(id_kursi),
    harga_saat_pemesanan  INTEGER NOT NULL,
    UNIQUE (id_pemesanan, id_kursi)
);

-- Trigger tambahan mencegah kursi ganda pada rute + tanggal + jam yang sama.
                """,
                language="sql",
            )

        info = database.info_database()
        st.caption(
            f"Database aktif: `{info['path']}` · ukuran {info['ukuran_kb']} KB. "
            "Data contoh dibuat otomatis satu kali saat database pertama kali dibuat."
        )

    with tab_teknis:
        c.section_title("Teknologi", "Seluruh komponen berjalan lokal tanpa server database terpisah.")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Komponen": "Python", "Keterangan": "Bahasa pemrograman aplikasi."},
                    {"Komponen": "Streamlit", "Keterangan": "Antarmuka web lokal berbahasa Indonesia."},
                    {"Komponen": "SQLite", "Keterangan": "Database relasional berbasis file `berkelana.db`."},
                    {"Komponen": "Pandas", "Keterangan": "Pengolahan tabel dan ekspor CSV."},
                    {"Komponen": "Altair", "Keterangan": "Grafik dashboard."},
                    {"Komponen": "VS Code / terminal", "Keterangan": "Cara menjalankan aplikasi secara lokal."},
                ]
            ),
            width="stretch",
            hide_index=True,
        )

        c.section_title("Struktur file proyek", "Pemisahan antarmuka, aturan bisnis, dan database.")
        st.code(
            """
berkelana travel/
├── app.py                  # Titik masuk Streamlit + navigasi
├── database.py             # Skema SQLite, koneksi, trigger, data contoh
├── services.py             # Aturan bisnis B01–B10 dan query
├── requirements.txt        # Dependensi
├── test_aturan_bisnis.py   # Pengujian otomatis aturan bisnis
├── berkelana.db            # Database (dibuat otomatis)
├── .streamlit/
│   └── config.toml         # Tema aplikasi
└── ui/
    ├── components.py       # CSS, komponen, nota
    ├── dashboard.py        # Halaman dashboard
    ├── pelanggan.py        # Halaman pelanggan
    ├── rute.py             # Halaman rute
    ├── kursi.py            # Halaman kursi
    ├── pemesanan.py        # Halaman pemesanan + denah kursi
    ├── riwayat.py          # Halaman riwayat & pembatalan
    └── panduan.py          # Halaman dokumentasi ini
            """,
            language="text",
        )

        c.section_title("Menjalankan aplikasi", "Dari terminal di folder proyek.")
        st.code(
            """
python -m pip install -r requirements.txt
streamlit run app.py
            """,
            language="bash",
        )
        st.caption(
            "Opsional: buat virtual environment terlebih dahulu dengan "
            "`python -m venv .venv`, lalu aktifkan sebelum memasang dependensi."
        )

        c.section_title("Pengujian aturan bisnis", "Memakai database sementara, tidak mengubah data asli.")
        st.code("python -m unittest -v test_aturan_bisnis.py", language="bash")

        c.section_title("Catatan keamanan & data", "Aplikasi ini dirancang untuk satu komputer loket.")
        st.markdown(
            """
            - Tidak ada login sesuai ruang lingkup; siapa pun yang membuka aplikasi dapat mengelola data.
            - Jalankan hanya di komputer/jaringan tepercaya.
            - Cadangkan `berkelana.db` secara berkala. Hentikan aplikasi sebelum menyalin file database.
            - Untuk memulai data dari nol, hentikan aplikasi lalu hapus `berkelana.db`; data contoh akan dibuat ulang saat aplikasi dijalankan kembali.
            """
        )

        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">Status aplikasi</div>
                <div class="panel-note">
                    Versi 1.0.0 · {c.badge('SQLite', 'teal')} {c.badge('Streamlit', 'green')} {c.badge('Tanpa login', 'amber')}<br>
                    File database: {c.esc(database.info_database()['path'])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
