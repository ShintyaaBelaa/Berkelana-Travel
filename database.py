"""
database.py
=================
Lapisan database untuk Sistem Administrasi Travel Berkelana.

Seluruh akses SQLite (pembuatan skema, koneksi, transaksi, data contoh,
dan pembuatan kode bisnis) berada di file ini. File antarmuka tidak menulis
SQL secara langsung.

Database disimpan sebagai file ``berkelana.db`` di folder proyek.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH: Path = BASE_DIR / "berkelana.db"

# ---------------------------------------------------------------------------
# SKEMA
# ---------------------------------------------------------------------------
# Nama tabel dan kolom mengikuti ERD pada dokumen perancangan:
#   pelanggan, rute, kursi, pemesanan, detail_pemesanan
# ID teknis berupa INTEGER PRIMARY KEY AUTOINCREMENT, sedangkan kode bisnis
# (P001, SY001, PSN001, K1) disimpan pada kolom tersendiri yang UNIQUE.
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pelanggan (
    id_pelanggan    INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pelanggan  TEXT    NOT NULL UNIQUE,
    nama_pelanggan  TEXT    NOT NULL CHECK (length(trim(nama_pelanggan)) > 0),
    nomor_telepon   TEXT    NOT NULL CHECK (
                        length(nomor_telepon) > 0
                        AND nomor_telepon NOT GLOB '*[^0-9]*'
                    ),
    dibuat_pada     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pelanggan_nama_telepon
    ON pelanggan (nama_pelanggan COLLATE NOCASE, nomor_telepon);

CREATE TABLE IF NOT EXISTS rute (
    id_rute         INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_rute       TEXT    NOT NULL UNIQUE,
    kota_asal       TEXT    NOT NULL CHECK (length(trim(kota_asal)) > 0),
    kota_tujuan     TEXT    NOT NULL CHECK (length(trim(kota_tujuan)) > 0),
    harga_tiket     INTEGER NOT NULL CHECK (harga_tiket > 0),
    aktif           INTEGER NOT NULL DEFAULT 1 CHECK (aktif IN (0, 1)),
    dibuat_pada     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (lower(trim(kota_asal)) <> lower(trim(kota_tujuan)))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_rute_asal_tujuan
    ON rute (kota_asal COLLATE NOCASE, kota_tujuan COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS kursi (
    id_kursi        INTEGER PRIMARY KEY AUTOINCREMENT,
    nomor_kursi     TEXT    NOT NULL UNIQUE CHECK (length(trim(nomor_kursi)) > 0),
    status_aktif    INTEGER NOT NULL DEFAULT 1 CHECK (status_aktif IN (0, 1)),
    dibuat_pada     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pemesanan (
    id_pemesanan            INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pemesanan          TEXT    NOT NULL UNIQUE,
    id_pelanggan            INTEGER NOT NULL,
    id_rute                 INTEGER NOT NULL,
    tanggal_keberangkatan   TEXT    NOT NULL CHECK (length(tanggal_keberangkatan) = 10),
    jam_keberangkatan       TEXT    NOT NULL CHECK (length(jam_keberangkatan) = 5),
    jumlah_pesan_tiket      INTEGER NOT NULL CHECK (jumlah_pesan_tiket > 0),
    total_harga             INTEGER NOT NULL CHECK (total_harga >= 0),
    dibuat_pada             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (id_pelanggan) REFERENCES pelanggan (id_pelanggan)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_rute) REFERENCES rute (id_rute)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_pemesanan_pelanggan
    ON pemesanan (id_pelanggan);
CREATE INDEX IF NOT EXISTS ix_pemesanan_jadwal
    ON pemesanan (id_rute, tanggal_keberangkatan, jam_keberangkatan);

CREATE TABLE IF NOT EXISTS detail_pemesanan (
    id_detail_pemesanan     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pemesanan            INTEGER NOT NULL,
    id_kursi                INTEGER NOT NULL,
    harga_saat_pemesanan    INTEGER NOT NULL CHECK (harga_saat_pemesanan > 0),
    FOREIGN KEY (id_pemesanan) REFERENCES pemesanan (id_pemesanan)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_kursi) REFERENCES kursi (id_kursi)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (id_pemesanan, id_kursi)
);

CREATE INDEX IF NOT EXISTS ix_detail_pemesanan
    ON detail_pemesanan (id_pemesanan);
CREATE INDEX IF NOT EXISTS ix_detail_kursi
    ON detail_pemesanan (id_kursi);

-- Pengaturan internal (penanda data contoh sudah dibuat, versi aplikasi, dll.)
CREATE TABLE IF NOT EXISTS pengaturan (
    kunci   TEXT PRIMARY KEY,
    nilai   TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- PENGAMAN TAMBAHAN DI LEVEL DATABASE
-- ---------------------------------------------------------------------------

-- B08: satu kursi tidak boleh dipakai dua kali pada rute + tanggal + jam yang
-- sama. Trigger ini melengkapi pengecekan di lapisan layanan sehingga tetap
-- aman walaupun ada dua proses yang menyimpan bersamaan.
CREATE TRIGGER IF NOT EXISTS trg_cegah_kursi_ganda
BEFORE INSERT ON detail_pemesanan
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM detail_pemesanan d
    JOIN pemesanan lama ON lama.id_pemesanan = d.id_pemesanan
    JOIN pemesanan baru ON baru.id_pemesanan = NEW.id_pemesanan
    WHERE d.id_kursi = NEW.id_kursi
      AND lama.id_rute = baru.id_rute
      AND lama.tanggal_keberangkatan = baru.tanggal_keberangkatan
      AND lama.jam_keberangkatan = baru.jam_keberangkatan
)
BEGIN
    SELECT RAISE(ABORT, 'Kursi sudah dipesan pada rute, tanggal, dan jam yang sama.');
END;

-- Kursi nonaktif tidak boleh dipilih pada pemesanan baru.
CREATE TRIGGER IF NOT EXISTS trg_tolak_kursi_nonaktif
BEFORE INSERT ON detail_pemesanan
FOR EACH ROW
WHEN (SELECT status_aktif FROM kursi WHERE id_kursi = NEW.id_kursi) = 0
BEGIN
    SELECT RAISE(ABORT, 'Kursi nonaktif tidak dapat dipesan.');
END;

-- ---------------------------------------------------------------------------
-- VIEW BANTU (hanya untuk kemudahan pembacaan, bukan duplikasi data)
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_pemesanan_lengkap AS
SELECT
    p.id_pemesanan,
    p.kode_pemesanan,
    p.id_pelanggan,
    c.kode_pelanggan,
    c.nama_pelanggan,
    c.nomor_telepon,
    p.id_rute,
    r.kode_rute,
    r.kota_asal,
    r.kota_tujuan,
    r.harga_tiket AS harga_tiket_saat_ini,
    p.tanggal_keberangkatan,
    p.jam_keberangkatan,
    p.jumlah_pesan_tiket,
    p.total_harga,
    p.dibuat_pada,
    (
        SELECT GROUP_CONCAT(nomor_kursi, ', ')
        FROM (
            SELECT k.nomor_kursi
            FROM detail_pemesanan d
            JOIN kursi k ON k.id_kursi = d.id_kursi
            WHERE d.id_pemesanan = p.id_pemesanan
            ORDER BY CAST(SUBSTR(k.nomor_kursi, 2) AS INTEGER), k.nomor_kursi
        )
    ) AS daftar_kursi
FROM pemesanan p
JOIN pelanggan c ON c.id_pelanggan = p.id_pelanggan
JOIN rute r      ON r.id_rute = p.id_rute;
"""


# ---------------------------------------------------------------------------
# KONEKSI & TRANSAKSI
# ---------------------------------------------------------------------------

def get_connection(path: Path | str | None = None) -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan foreign key aktif dan row factory."""
    target = Path(path) if path is not None else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


@contextmanager
def transaksi() -> Iterator[sqlite3.Connection]:
    """Context manager transaksi tulis (BEGIN IMMEDIATE -> commit/rollback).

    BEGIN IMMEDIATE mengunci database untuk penulisan sejak awal transaksi,
    sehingga pengecekan kursi dan penyimpanan pemesanan berjalan atomik.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: Path | str | None = None, seed: bool = True) -> None:
    """Membuat database, tabel, trigger, dan (opsional) data contoh."""
    global DB_PATH
    if path is not None:
        DB_PATH = Path(path)

    conn = get_connection()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_SQL)
        if seed:
            _seed_once(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# KODE BISNIS
# ---------------------------------------------------------------------------

def kode_berikutnya(
    conn: sqlite3.Connection,
    tabel: str,
    kolom: str,
    prefix: str,
    lebar: int = 3,
) -> str:
    """Menghasilkan kode berurutan, misalnya P001, R003, atau PSN012.

    ``tabel`` dan ``kolom`` hanya diisi dengan konstanta internal, bukan input
    pengguna, sehingga aman untuk dimasukkan ke dalam query.
    """
    if (tabel, kolom) not in {
        ("pelanggan", "kode_pelanggan"),
        ("rute", "kode_rute"),
        ("pemesanan", "kode_pemesanan"),
    }:
        raise ValueError("Tabel/kolom kode tidak dikenali.")

    rows = conn.execute(
        f"SELECT {kolom} FROM {tabel} WHERE {kolom} LIKE ?",
        (f"{prefix}%",),
    ).fetchall()

    terbesar = 0
    for row in rows:
        suffix = str(row[0])[len(prefix):]
        if suffix.isdigit():
            terbesar = max(terbesar, int(suffix))
    return f"{prefix}{terbesar + 1:0{lebar}d}"


def ambil_pengaturan(conn: sqlite3.Connection, kunci: str) -> str | None:
    row = conn.execute(
        "SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,)
    ).fetchone()
    return row["nilai"] if row else None


def simpan_pengaturan(conn: sqlite3.Connection, kunci: str, nilai: str) -> None:
    conn.execute(
        """
        INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?)
        ON CONFLICT(kunci) DO UPDATE SET nilai = excluded.nilai
        """,
        (kunci, nilai),
    )


# ---------------------------------------------------------------------------
# DATA CONTOH
# ---------------------------------------------------------------------------

def _seed_once(conn: sqlite3.Connection) -> None:
    """Mengisi data contoh satu kali saja.

    Penanda di tabel ``pengaturan`` mencegah data contoh muncul kembali
    setelah petugas menghapus seluruh data.
    """
    if ambil_pengaturan(conn, "seed_demo") == "selesai":
        return

    now = datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")

    pelanggan = [
        ("P001", "Andi Pratama", "081234567890", now_text),
        ("P002", "Budi Santoso", "081298765432", now_text),
        ("P003", "Citra Dewi", "085712345678", now_text),
        ("P004", "Dewi Lestari", "087812345678", now_text),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO pelanggan
            (kode_pelanggan, nama_pelanggan, nomor_telepon, dibuat_pada)
        VALUES (?, ?, ?, ?)
        """,
        pelanggan,
    )

    rute = [
        ("SY001", "Semarang", "Solo", 75_000, 1, now_text),
        ("SY002", "Semarang", "Yogyakarta", 90_000, 1, now_text),
        ("SL001", "Solo", "Semarang", 75_000, 1, now_text),
        ("KD001", "Semarang", "Kudus", 55_000, 1, now_text),
        ("MG001", "Semarang", "Magelang", 65_000, 0, now_text),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO rute
            (kode_rute, kota_asal, kota_tujuan, harga_tiket, aktif, dibuat_pada)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rute,
    )

    conn.executemany(
        """
        INSERT OR IGNORE INTO kursi (nomor_kursi, status_aktif, dibuat_pada)
        VALUES (?, 1, ?)
        """,
        [(f"K{i}", now_text) for i in range(1, 9)],
    )

    # Pemesanan contoh memakai tanggal relatif terhadap hari ini supaya
    # jadwalnya selalu berada di masa depan saat aplikasi pertama dijalankan.
    def id_pelanggan(kode: str) -> int:
        return conn.execute(
            "SELECT id_pelanggan FROM pelanggan WHERE kode_pelanggan = ?", (kode,)
        ).fetchone()["id_pelanggan"]

    def id_rute(kode: str) -> int:
        return conn.execute(
            "SELECT id_rute FROM rute WHERE kode_rute = ?", (kode,)
        ).fetchone()["id_rute"]

    contoh = [
        # kode, kode pelanggan, kode rute, selisih hari, jam, kursi, harga
        ("PSN001", "P001", "SY001", 1, "08:00", ["K1", "K2"], 75_000),
        ("PSN002", "P002", "SY001", 2, "08:00", ["K1"], 75_000),
        ("PSN003", "P003", "SY002", 1, "10:00", ["K3", "K4", "K5"], 90_000),
        ("PSN004", "P004", "SL001", 3, "13:00", ["K2"], 75_000),
        ("PSN005", "P001", "KD001", 2, "15:00", ["K6"], 55_000),
    ]

    for kode, kode_cust, kode_route, beda_hari, jam, kursi, harga in contoh:
        tanggal = (date.today() + timedelta(days=beda_hari)).isoformat()
        total = harga * len(kursi)
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO pemesanan
                (kode_pemesanan, id_pelanggan, id_rute, tanggal_keberangkatan,
                 jam_keberangkatan, jumlah_pesan_tiket, total_harga, dibuat_pada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kode,
                id_pelanggan(kode_cust),
                id_rute(kode_route),
                tanggal,
                jam,
                len(kursi),
                total,
                now_text,
            ),
        )
        if cur.rowcount == 0:
            continue
        id_pemesanan = cur.lastrowid
        for nomor in kursi:
            id_kursi = conn.execute(
                "SELECT id_kursi FROM kursi WHERE nomor_kursi = ?", (nomor,)
            ).fetchone()["id_kursi"]
            conn.execute(
                """
                INSERT INTO detail_pemesanan
                    (id_pemesanan, id_kursi, harga_saat_pemesanan)
                VALUES (?, ?, ?)
                """,
                (id_pemesanan, id_kursi, harga),
            )

    simpan_pengaturan(conn, "seed_demo", "selesai")
    simpan_pengaturan(conn, "versi_aplikasi", "1.0.0")


def info_database() -> dict:
    """Ringkasan lokasi dan ukuran file database untuk ditampilkan di UI."""
    ukuran = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "path": str(DB_PATH),
        "ukuran_kb": round(ukuran / 1024, 1),
        "nama_file": DB_PATH.name,
    }


def format_waktu_lokal(moment: datetime | None = None) -> str:
    """Format waktu lokal untuk nota dan metadata."""
    moment = moment or datetime.now()
    return moment.strftime("%d-%m-%Y %H:%M:%S")


def gabung_jadwal(tanggal: str, jam: str) -> datetime:
    """Mengubah pasangan tanggal (YYYY-MM-DD) dan jam (HH:MM) ke datetime."""
    return datetime.combine(date.fromisoformat(tanggal), time.fromisoformat(jam))
