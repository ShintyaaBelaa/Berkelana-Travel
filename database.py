"""
Lapisan database & aturan bisnis Sistem Administrasi Travel Berkelana.

Seluruh akses SQLite dipusatkan di modul ini. Antarmuka Streamlit hanya
memanggil fungsi-fungsi publik di bawah dan tidak menulis SQL secara langsung.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

BASE_DIR = Path(__file__).resolve().parent
NAMA_FILE_DATABASE = "berkelana.db"

# Tiga jam keberangkatan tetap untuk setiap rute.
JAM_KEBERANGKATAN: tuple[time, ...] = (time(7, 0), time(12, 0), time(17, 0))


# ---------------------------------------------------------------------------
# Koneksi
# ---------------------------------------------------------------------------


class KesalahanBisnis(Exception):
    """Kesalahan yang berasal dari aturan bisnis dan aman ditampilkan ke pengguna."""


def lokasi_database() -> Path:
    """Lokasi file database. Dapat diubah lewat env BERKELANA_DB (untuk pengujian)."""
    return Path(os.environ.get("BERKELANA_DB", str(BASE_DIR / NAMA_FILE_DATABASE)))


@contextmanager
def koneksi():
    """Membuka koneksi SQLite dengan foreign key aktif dan transaksi otomatis."""
    path = lokasi_database()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Skema
# ---------------------------------------------------------------------------


SKEMA = """
CREATE TABLE IF NOT EXISTS pelanggan (
    id_pelanggan     INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pelanggan   TEXT NOT NULL UNIQUE,
    nama_pelanggan   TEXT NOT NULL COLLATE NOCASE
                     CHECK (length(trim(nama_pelanggan)) > 0),
    nomor_telepon    TEXT NOT NULL COLLATE NOCASE
                     CHECK (length(trim(nomor_telepon)) > 0),
    dibuat_pada      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (nama_pelanggan, nomor_telepon)
);

CREATE TABLE IF NOT EXISTS rute (
    id_rute          INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_rute        TEXT NOT NULL UNIQUE,
    kota_asal        TEXT NOT NULL COLLATE NOCASE
                     CHECK (length(trim(kota_asal)) > 0),
    kota_tujuan      TEXT NOT NULL COLLATE NOCASE
                     CHECK (length(trim(kota_tujuan)) > 0),
    harga_tiket      INTEGER NOT NULL CHECK (harga_tiket > 0),
    aktif            INTEGER NOT NULL DEFAULT 1 CHECK (aktif IN (0, 1)),
    dibuat_pada      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (lower(trim(kota_asal)) <> lower(trim(kota_tujuan)))
);

CREATE TABLE IF NOT EXISTS jadwal (
    id_jadwal            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_rute              INTEGER NOT NULL
                         REFERENCES rute (id_rute)
                         ON UPDATE CASCADE ON DELETE CASCADE,
    kode_jadwal          TEXT NOT NULL UNIQUE,
    jam_keberangkatan    TEXT NOT NULL
                         CHECK (jam_keberangkatan GLOB
                                '[0-9][0-9]:[0-9][0-9]'),
    urut_keberangkatan   INTEGER NOT NULL
                         CHECK (urut_keberangkatan BETWEEN 1 AND 3),
    aktif                INTEGER NOT NULL DEFAULT 1 CHECK (aktif IN (0, 1)),
    dibuat_pada          TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (id_rute, jam_keberangkatan),
    UNIQUE (id_rute, urut_keberangkatan)
);

CREATE TABLE IF NOT EXISTS kursi (
    id_kursi         INTEGER PRIMARY KEY AUTOINCREMENT,
    nomor_kursi      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    status_aktif     INTEGER NOT NULL DEFAULT 1 CHECK (status_aktif IN (0, 1)),
    dibuat_pada      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pemesanan (
    id_pemesanan           INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_pemesanan         TEXT NOT NULL UNIQUE,
    id_pelanggan           INTEGER NOT NULL
                           REFERENCES pelanggan (id_pelanggan)
                           ON UPDATE CASCADE ON DELETE RESTRICT,
    id_rute                INTEGER NOT NULL
                           REFERENCES rute (id_rute)
                           ON UPDATE CASCADE ON DELETE RESTRICT,
    tanggal_keberangkatan  TEXT NOT NULL
                           CHECK (tanggal_keberangkatan GLOB
                                  '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    jam_keberangkatan      TEXT NOT NULL
                           CHECK (jam_keberangkatan GLOB
                                  '[0-9][0-9]:[0-9][0-9]'),
    jumlah_pesan_tiket     INTEGER NOT NULL CHECK (jumlah_pesan_tiket > 0),
    harga_saat_pemesanan   INTEGER NOT NULL CHECK (harga_saat_pemesanan > 0),
    total_harga            INTEGER NOT NULL CHECK (total_harga > 0),
    dibuat_pada            TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (total_harga = jumlah_pesan_tiket * harga_saat_pemesanan)
);

CREATE TABLE IF NOT EXISTS detail_pemesanan (
    id_detail_pemesanan  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pemesanan         INTEGER NOT NULL
                         REFERENCES pemesanan (id_pemesanan)
                         ON UPDATE CASCADE ON DELETE CASCADE,
    id_kursi             INTEGER NOT NULL
                         REFERENCES kursi (id_kursi)
                         ON UPDATE CASCADE ON DELETE RESTRICT,
    harga_satuan         INTEGER NOT NULL CHECK (harga_satuan > 0),
    UNIQUE (id_pemesanan, id_kursi)
);

CREATE TABLE IF NOT EXISTS counter (
    nama   TEXT PRIMARY KEY,
    nilai  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS log_aktivitas (
    id_log      INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    aksi        TEXT NOT NULL,
    entitas     TEXT NOT NULL,
    referensi   TEXT,
    keterangan  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pelanggan_nama
    ON pelanggan (nama_pelanggan);
CREATE INDEX IF NOT EXISTS idx_pelanggan_telepon
    ON pelanggan (nomor_telepon);
CREATE INDEX IF NOT EXISTS idx_rute_status
    ON rute (aktif);
CREATE INDEX IF NOT EXISTS idx_jadwal_rute
    ON jadwal (id_rute, urut_keberangkatan);
CREATE INDEX IF NOT EXISTS idx_pemesanan_pelanggan
    ON pemesanan (id_pelanggan);
CREATE INDEX IF NOT EXISTS idx_pemesanan_rute
    ON pemesanan (id_rute);
CREATE INDEX IF NOT EXISTS idx_pemesanan_jadwal
    ON pemesanan (id_rute, tanggal_keberangkatan, jam_keberangkatan);
CREATE INDEX IF NOT EXISTS idx_detail_pemesanan
    ON detail_pemesanan (id_pemesanan);
CREATE INDEX IF NOT EXISTS idx_detail_kursi
    ON detail_pemesanan (id_kursi);
CREATE INDEX IF NOT EXISTS idx_log_waktu
    ON log_aktivitas (waktu);

-- Pengaman terakhir di level database: satu kursi hanya boleh muncul satu kali
-- pada kombinasi rute + tanggal + jam yang sama.
CREATE TRIGGER IF NOT EXISTS trg_cegah_kursi_ganda
BEFORE INSERT ON detail_pemesanan
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Kursi sudah dipesan pada rute, tanggal, dan jam yang sama.')
    WHERE EXISTS (
        SELECT 1
        FROM detail_pemesanan dp
        JOIN pemesanan lama ON lama.id_pemesanan = dp.id_pemesanan
        JOIN pemesanan baru ON baru.id_pemesanan = NEW.id_pemesanan
        WHERE dp.id_kursi = NEW.id_kursi
          AND lama.id_rute = baru.id_rute
          AND lama.tanggal_keberangkatan = baru.tanggal_keberangkatan
          AND lama.jam_keberangkatan = baru.jam_keberangkatan
          AND dp.id_pemesanan <> NEW.id_pemesanan
    );
END;
"""


# ---------------------------------------------------------------------------
# Inisialisasi & util internal
# ---------------------------------------------------------------------------


def _catat_log(
    conn: sqlite3.Connection,
    aksi: str,
    entitas: str,
    referensi: str | None,
    keterangan: str,
) -> None:
    conn.execute(
        "INSERT INTO log_aktivitas (aksi, entitas, referensi, keterangan) "
        "VALUES (?, ?, ?, ?)",
        (aksi, entitas, referensi, keterangan),
    )


def _pastikan_counter(conn: sqlite3.Connection) -> None:
    defaults = {"pelanggan": 0, "pemesanan": 0}
    for nama, nilai in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO counter (nama, nilai) VALUES (?, ?)",
            (nama, nilai),
        )


def _sinkron_counter(conn: sqlite3.Connection) -> None:
    """Menyelaraskan counter agar kode tidak bentrok dengan data lama."""
    pasangan = [
        ("pelanggan", "pelanggan", "kode_pelanggan", "P"),
        ("pemesanan", "pemesanan", "kode_pemesanan", "PSN"),
    ]
    for nama_counter, tabel, kolom, prefix in pasangan:
        row = conn.execute(
            f"SELECT MAX(CAST(SUBSTR({kolom}, ?) AS INTEGER)) AS maks FROM {tabel}",
            (len(prefix) + 1,),
        ).fetchone()
        maks = int(row["maks"] or 0)
        conn.execute(
            "INSERT INTO counter (nama, nilai) VALUES (?, ?) "
            "ON CONFLICT(nama) DO UPDATE SET nilai = MAX(nilai, excluded.nilai)",
            (nama_counter, maks),
        )


def _kode_berikutnya(
    conn: sqlite3.Connection, nama_counter: str, prefix: str, lebar: int = 3
) -> str:
    row = conn.execute(
        "SELECT nilai FROM counter WHERE nama = ?", (nama_counter,)
    ).fetchone()
    nilai = (int(row["nilai"]) if row else 0) + 1
    conn.execute(
        "INSERT INTO counter (nama, nilai) VALUES (?, ?) "
        "ON CONFLICT(nama) DO UPDATE SET nilai = excluded.nilai",
        (nama_counter, nilai),
    )
    return f"{prefix}{nilai:0{lebar}d}"


def _bersihkan_teks(nilai: str) -> str:
    return " ".join(str(nilai or "").split())


def _normalisasi_prefix_kode(nilai: str) -> str:
    return _bersihkan_teks(nilai).upper()


def _huruf_kota(nama: str) -> str:
    huruf = re.sub(r"[^A-Za-z]", "", _bersihkan_teks(nama)).upper()
    return huruf or "X"


def _kandidat_prefix(asal: str, tujuan: str) -> list[str]:
    """Kandidat kode rute: inisial asal + inisial tujuan, lalu variasi bila bentrok."""
    a = _huruf_kota(asal)
    t = _huruf_kota(tujuan)
    kandidat = [a[0] + t[0], a[0] + t[:2], a[:2] + t[0], a[:2] + t[:2]]
    hasil: list[str] = []
    for kode in kandidat:
        if kode and kode not in hasil:
            hasil.append(kode)
    return hasil


def _prefix_rute_unik(
    conn: sqlite3.Connection,
    asal: str,
    tujuan: str,
    exclude_id: int | None = None,
) -> str:
    """Mencari prefix kode rute yang belum dipakai rute/jadwal lain."""
    for dasar in _kandidat_prefix(asal, tujuan):
        query = "SELECT 1 FROM rute WHERE kode_rute = ?"
        params: list[Any] = [dasar]
        if exclude_id is not None:
            query += " AND id_rute <> ?"
            params.append(exclude_id)
        if conn.execute(query, params).fetchone():
            continue
        if conn.execute(
            "SELECT 1 FROM jadwal WHERE SUBSTR(kode_jadwal, 1, ?) = ?",
            (len(dasar), dasar),
        ).fetchone():
            continue
        return dasar

    dasar = _kandidat_prefix(asal, tujuan)[0]
    urutan = 2
    while True:
        kandidat = f"{dasar}{urutan}"
        if not conn.execute(
            "SELECT 1 FROM rute WHERE kode_rute = ?", (kandidat,)
        ).fetchone() and not conn.execute(
            "SELECT 1 FROM jadwal WHERE SUBSTR(kode_jadwal, 1, ?) = ?",
            (len(kandidat), kandidat),
        ).fetchone():
            return kandidat
        urutan += 1


def _buat_jadwal_internal(
    conn: sqlite3.Connection,
    id_rute: int,
    prefix: str,
    aktif: bool = True,
) -> list[dict[str, Any]]:
    """Membuat tiga jadwal tetap (07.00, 12.00, 17.00) dengan kode bisnis."""
    prefix = _normalisasi_prefix_kode(prefix)
    hasil: list[dict[str, Any]] = []
    for urut, jam in enumerate(JAM_KEBERANGKATAN, start=1):
        kode = f"{prefix}{urut:03d}"
        cur = conn.execute(
            "INSERT INTO jadwal (id_rute, kode_jadwal, jam_keberangkatan, "
            "urut_keberangkatan, aktif) VALUES (?, ?, ?, ?, ?)",
            (id_rute, kode, jam.strftime("%H:%M"), urut, 1 if aktif else 0),
        )
        hasil.append(
            dict(
                conn.execute(
                    "SELECT * FROM jadwal WHERE id_jadwal = ?", (cur.lastrowid,)
                ).fetchone()
            )
        )
    return hasil


def _pastikan_jadwal(conn: sqlite3.Connection) -> None:
    """Melengkapi jadwal untuk database lama yang belum memiliki tabel jadwal."""
    rute_rows = conn.execute(
        "SELECT id_rute, kode_rute, kota_asal, kota_tujuan, aktif FROM rute"
    ).fetchall()
    for rute in rute_rows:
        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM jadwal WHERE id_rute = ?",
            (rute["id_rute"],),
        ).fetchone()["n"]
        if jumlah:
            continue
        kode_lama = _normalisasi_prefix_kode(rute["kode_rute"] or "")
        if re.fullmatch(r"[A-Z]{2,3}", kode_lama):
            prefix = kode_lama
        else:
            prefix = _prefix_rute_unik(
                conn,
                rute["kota_asal"],
                rute["kota_tujuan"],
                rute["id_rute"],
            )
        _buat_jadwal_internal(conn, rute["id_rute"], prefix, True)


def init_db(seed: bool = True) -> None:
    """Membuat skema, kursi awal, dan (opsional) data contoh pada database baru."""
    database_baru = not lokasi_database().exists()
    with koneksi() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SKEMA)
        _pastikan_counter(conn)

        jumlah_kursi = conn.execute("SELECT COUNT(*) AS n FROM kursi").fetchone()["n"]
        if jumlah_kursi == 0:
            for i in range(1, 9):
                conn.execute(
                    "INSERT INTO kursi (nomor_kursi, status_aktif) VALUES (?, 1)",
                    (f"K{i}",),
                )

        jumlah_pelanggan = conn.execute(
            "SELECT COUNT(*) AS n FROM pelanggan"
        ).fetchone()["n"]
        if seed and database_baru and jumlah_pelanggan == 0:
            _isi_data_contoh(conn)

        _pastikan_jadwal(conn)
        _sinkron_counter(conn)


def _isi_data_contoh(conn: sqlite3.Connection) -> None:
    """Data contoh realistis. Tanggal dibuat relatif terhadap hari ini."""
    pelanggan_contoh = [
        ("Andi Pratama", "081234567890"),
        ("Siti Aminah", "081298765432"),
        ("Budi Santoso", "085712345678"),
        ("Rina Wulandari", "087812345678"),
        ("Dewi Lestari", "081377788899"),
        ("Agus Setiawan", "082112223333"),
    ]
    for nama, telepon in pelanggan_contoh:
        _buat_pelanggan_internal(conn, nama, telepon, catat_log=False)

    rute_contoh = [
        ("Semarang", "Yogyakarta", 85_000, 1),
        ("Semarang", "Solo", 75_000, 1),
        ("Semarang", "Jepara", 75_000, 1),
        ("Semarang", "Kudus", 80_000, 1),
        ("Semarang", "Pati", 90_000, 1),
    ]
    for asal, tujuan, harga, aktif in rute_contoh:
        _buat_rute_internal(conn, asal, tujuan, harga, aktif, catat_log=False)

    pelanggan = {
        row["kode_pelanggan"]: row["id_pelanggan"]
        for row in conn.execute("SELECT id_pelanggan, kode_pelanggan FROM pelanggan")
    }
    jadwal = {
        row["kode_jadwal"]: dict(row)
        for row in conn.execute("SELECT * FROM jadwal")
    }
    kursi = {
        row["nomor_kursi"]: row["id_kursi"]
        for row in conn.execute("SELECT id_kursi, nomor_kursi FROM kursi")
    }

    hari_ini = date.today()

    contoh_pemesanan = [
        ("P001", "SY001", -18, ["K1", "K2"]),
        ("P002", "SS002", -11, ["K4"]),
        ("P003", "SJ001", -6, ["K3"]),
        ("P004", "SK003", -3, ["K1", "K2", "K3"]),
        ("P001", "SY001", 1, ["K1", "K2"]),
        ("P002", "SY001", 1, ["K3"]),
        ("P003", "SS003", 2, ["K1", "K4", "K5"]),
        ("P004", "SJ002", 3, ["K2"]),
        ("P005", "SK001", 5, ["K1", "K2", "K3", "K4"]),
        ("P006", "SP002", 7, ["K6", "K7"]),
        ("P005", "SY003", 2, ["K5"]),
        ("P002", "SS001", 10, ["K2"]),
        ("P003", "SP001", 14, ["K5", "K6"]),
        ("P006", "SJ003", 4, ["K4"]),
    ]
    for kode_pelanggan, kode_jadwal, offset, daftar_kursi in contoh_pemesanan:
        jadwal_item = jadwal[kode_jadwal]
        _buat_pemesanan_internal(
            conn,
            id_pelanggan=pelanggan[kode_pelanggan],
            id_rute=jadwal_item["id_rute"],
            tanggal=hari_ini + timedelta(days=offset),
            jam=datetime.strptime(jadwal_item["jam_keberangkatan"], "%H:%M").time(),
            id_kursi=[kursi[nomor] for nomor in daftar_kursi],
            validasi_waktu=False,
            catat_log=False,
        )

    _catat_log(
        conn,
        "INISIALISASI",
        "SISTEM",
        None,
        "Database dibuat dan diisi data contoh Travel Berkelana.",
    )


# ---------------------------------------------------------------------------
# Pelanggan
# ---------------------------------------------------------------------------


def _validasi_pelanggan(
    conn: sqlite3.Connection,
    nama: str,
    telepon: str,
    exclude_id: int | None = None,
) -> tuple[str, str]:
    nama_bersih = _bersihkan_teks(nama)
    telepon_bersih = _bersihkan_teks(telepon)

    if not nama_bersih:
        raise KesalahanBisnis("Nama pelanggan wajib diisi.")
    if not telepon_bersih:
        raise KesalahanBisnis("Nomor telepon wajib diisi.")
    if not re.fullmatch(r"[0-9]+", telepon_bersih):
        raise KesalahanBisnis(
            "Nomor telepon hanya boleh berisi angka, tanpa spasi, tanda hubung, atau huruf."
        )

    query = (
        "SELECT kode_pelanggan FROM pelanggan "
        "WHERE nama_pelanggan = ? COLLATE NOCASE AND nomor_telepon = ?"
    )
    params: list[Any] = [nama_bersih, telepon_bersih]
    if exclude_id is not None:
        query += " AND id_pelanggan <> ?"
        params.append(exclude_id)
    duplikat = conn.execute(query, params).fetchone()
    if duplikat:
        raise KesalahanBisnis(
            "Pelanggan dengan nama dan nomor telepon yang sama sudah terdaftar "
            f"({duplikat['kode_pelanggan']}). Data ganda tidak diizinkan."
        )
    return nama_bersih, telepon_bersih


def _buat_pelanggan_internal(
    conn: sqlite3.Connection,
    nama: str,
    telepon: str,
    catat_log: bool = True,
) -> dict[str, Any]:
    nama, telepon = _validasi_pelanggan(conn, nama, telepon)
    kode = _kode_berikutnya(conn, "pelanggan", "P")
    cur = conn.execute(
        "INSERT INTO pelanggan (kode_pelanggan, nama_pelanggan, nomor_telepon) "
        "VALUES (?, ?, ?)",
        (kode, nama, telepon),
    )
    if catat_log:
        _catat_log(
            conn,
            "TAMBAH",
            "PELANGGAN",
            kode,
            f"Menambahkan pelanggan {nama} ({telepon}).",
        )
    row = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (cur.lastrowid,)
    ).fetchone()
    return dict(row)


def tambah_pelanggan(nama: str, telepon: str) -> dict[str, Any]:
    with koneksi() as conn:
        return _buat_pelanggan_internal(conn, nama, telepon)


def ubah_pelanggan(id_pelanggan: int, nama: str, telepon: str) -> dict[str, Any]:
    with koneksi() as conn:
        lama = conn.execute(
            "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
        ).fetchone()
        if not lama:
            raise KesalahanBisnis("Pelanggan tidak ditemukan.")
        nama, telepon = _validasi_pelanggan(conn, nama, telepon, id_pelanggan)
        conn.execute(
            "UPDATE pelanggan SET nama_pelanggan = ?, nomor_telepon = ? "
            "WHERE id_pelanggan = ?",
            (nama, telepon, id_pelanggan),
        )
        _catat_log(
            conn,
            "UBAH",
            "PELANGGAN",
            lama["kode_pelanggan"],
            f"Mengubah data pelanggan {lama['nama_pelanggan']} menjadi {nama} ({telepon}).",
        )
        row = conn.execute(
            "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
        ).fetchone()
        return dict(row)


def hapus_pelanggan(id_pelanggan: int) -> None:
    with koneksi() as conn:
        row = conn.execute(
            "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
        ).fetchone()
        if not row:
            raise KesalahanBisnis("Pelanggan tidak ditemukan.")
        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM pemesanan WHERE id_pelanggan = ?",
            (id_pelanggan,),
        ).fetchone()["n"]
        if jumlah:
            raise KesalahanBisnis(
                f"Pelanggan {row['kode_pelanggan']} tidak dapat dihapus karena masih "
                f"memiliki {jumlah} pemesanan. Batalkan pemesanannya terlebih dahulu."
            )
        conn.execute(
            "DELETE FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
        )
        _catat_log(
            conn,
            "HAPUS",
            "PELANGGAN",
            row["kode_pelanggan"],
            f"Menghapus pelanggan {row['nama_pelanggan']} ({row['nomor_telepon']}).",
        )


def daftar_pelanggan(cari: str = "") -> list[dict[str, Any]]:
    with koneksi() as conn:
        where = ""
        params: list[Any] = []
        if cari.strip():
            where = (
                "WHERE pl.kode_pelanggan LIKE ? OR pl.nama_pelanggan LIKE ? "
                "OR pl.nomor_telepon LIKE ?"
            )
            pola = f"%{cari.strip()}%"
            params = [pola, pola, pola]
        rows = conn.execute(
            f"""
            SELECT pl.*,
                   COUNT(p.id_pemesanan) AS jumlah_pemesanan,
                   COALESCE(SUM(p.total_harga), 0) AS total_belanja,
                   COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS total_tiket,
                   MAX(p.tanggal_keberangkatan) AS perjalanan_terakhir
            FROM pelanggan pl
            LEFT JOIN pemesanan p ON p.id_pelanggan = pl.id_pelanggan
            {where}
            GROUP BY pl.id_pelanggan
            ORDER BY pl.nama_pelanggan COLLATE NOCASE
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def ambil_pelanggan(id_pelanggan: int) -> dict[str, Any] | None:
    with koneksi() as conn:
        return _dict(
            conn.execute(
                "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
            ).fetchone()
        )


# ---------------------------------------------------------------------------
# Rute
# ---------------------------------------------------------------------------


def _validasi_rute(
    conn: sqlite3.Connection,
    asal: str,
    tujuan: str,
    harga: int | str,
) -> tuple[str, str, int]:
    asal_bersih = _bersihkan_teks(asal)
    tujuan_bersih = _bersihkan_teks(tujuan)
    if not asal_bersih:
        raise KesalahanBisnis("Kota asal wajib diisi.")
    if not tujuan_bersih:
        raise KesalahanBisnis("Kota tujuan wajib diisi.")
    if asal_bersih.casefold() == tujuan_bersih.casefold():
        raise KesalahanBisnis("Kota asal dan kota tujuan tidak boleh sama.")
    try:
        harga_int = int(harga)
    except (TypeError, ValueError):
        raise KesalahanBisnis("Tarif tiket harus berupa angka.") from None
    if harga_int <= 0:
        raise KesalahanBisnis("Tarif tiket harus lebih besar dari nol.")
    return asal_bersih, tujuan_bersih, harga_int


def _buat_rute_internal(
    conn: sqlite3.Connection,
    asal: str,
    tujuan: str,
    harga: int | str,
    aktif: bool | int = True,
    catat_log: bool = True,
) -> dict[str, Any]:
    asal, tujuan, harga_int = _validasi_rute(conn, asal, tujuan, harga)
    duplikat = conn.execute(
        "SELECT kode_rute FROM rute WHERE kota_asal = ? COLLATE NOCASE "
        "AND kota_tujuan = ? COLLATE NOCASE",
        (asal, tujuan),
    ).fetchone()
    if duplikat:
        raise KesalahanBisnis(
            f"Rute {asal} - {tujuan} sudah terdaftar ({duplikat['kode_rute']}). "
            "Satu rute sudah mencakup tiga jadwal keberangkatan sekaligus."
        )
    kode = _prefix_rute_unik(conn, asal, tujuan)
    cur = conn.execute(
        "INSERT INTO rute (kode_rute, kota_asal, kota_tujuan, harga_tiket, aktif) "
        "VALUES (?, ?, ?, ?, ?)",
        (kode, asal, tujuan, harga_int, 1 if aktif else 0),
    )
    id_rute = int(cur.lastrowid)
    _buat_jadwal_internal(conn, id_rute, kode, True)
    if catat_log:
        _catat_log(
            conn,
            "TAMBAH",
            "RUTE",
            kode,
            f"Menambahkan rute {asal} - {tujuan} dengan tarif Rp{harga_int:,} "
            "dan tiga jadwal (07:00, 12:00, 17:00).".replace(",", "."),
        )
    row = conn.execute(
        "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
    ).fetchone()
    return dict(row)


def tambah_rute(
    asal: str, tujuan: str, harga: int | str, aktif: bool = True
) -> dict[str, Any]:
    with koneksi() as conn:
        return _buat_rute_internal(conn, asal, tujuan, harga, aktif)


def ubah_rute(
    id_rute: int,
    asal: str,
    tujuan: str,
    harga: int | str,
    aktif: bool,
) -> dict[str, Any]:
    with koneksi() as conn:
        lama = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        if not lama:
            raise KesalahanBisnis("Rute tidak ditemukan.")
        asal, tujuan, harga_int = _validasi_rute(conn, asal, tujuan, harga)
        duplikat = conn.execute(
            "SELECT kode_rute FROM rute WHERE kota_asal = ? COLLATE NOCASE "
            "AND kota_tujuan = ? COLLATE NOCASE AND id_rute <> ?",
            (asal, tujuan, id_rute),
        ).fetchone()
        if duplikat:
            raise KesalahanBisnis(
                f"Rute {asal} - {tujuan} sudah terdaftar ({duplikat['kode_rute']})."
            )
        conn.execute(
            "UPDATE rute SET kota_asal = ?, kota_tujuan = ?, harga_tiket = ?, "
            "aktif = ? WHERE id_rute = ?",
            (asal, tujuan, harga_int, 1 if aktif else 0, id_rute),
        )
        _catat_log(
            conn,
            "UBAH",
            "RUTE",
            lama["kode_rute"],
            f"Mengubah rute {lama['kota_asal']} - {lama['kota_tujuan']} menjadi "
            f"{asal} - {tujuan}, tarif Rp{harga_int:,}, status "
            f"{'aktif' if aktif else 'nonaktif'}.".replace(",", "."),
        )
        row = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        return dict(row)


def atur_status_rute(id_rute: int, aktif: bool) -> None:
    with koneksi() as conn:
        lama = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        if not lama:
            raise KesalahanBisnis("Rute tidak ditemukan.")
        conn.execute(
            "UPDATE rute SET aktif = ? WHERE id_rute = ?",
            (1 if aktif else 0, id_rute),
        )
        _catat_log(
            conn,
            "UBAH STATUS",
            "RUTE",
            lama["kode_rute"],
            f"Rute {lama['kota_asal']} - {lama['kota_tujuan']} di"
            f"{'aktifkan' if aktif else 'nonaktifkan'}.",
        )


def hapus_rute(id_rute: int) -> None:
    with koneksi() as conn:
        row = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        if not row:
            raise KesalahanBisnis("Rute tidak ditemukan.")
        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM pemesanan WHERE id_rute = ?", (id_rute,)
        ).fetchone()["n"]
        if jumlah:
            raise KesalahanBisnis(
                f"Rute {row['kode_rute']} sudah dipakai pada {jumlah} pemesanan sehingga "
                "tidak boleh dihapus permanen. Nonaktifkan rute ini agar tidak dapat "
                "dipilih pada pemesanan baru."
            )
        conn.execute("DELETE FROM rute WHERE id_rute = ?", (id_rute,))
        _catat_log(
            conn,
            "HAPUS",
            "RUTE",
            row["kode_rute"],
            f"Menghapus rute {row['kota_asal']} - {row['kota_tujuan']}.",
        )


def daftar_rute(cari: str = "", hanya_aktif: bool = False) -> list[dict[str, Any]]:
    with koneksi() as conn:
        kondisi: list[str] = []
        params: list[Any] = []
        if hanya_aktif:
            kondisi.append("r.aktif = 1")
        if cari.strip():
            kondisi.append(
                "(r.kode_rute LIKE ? OR r.kota_asal LIKE ? OR r.kota_tujuan LIKE ? "
                "OR EXISTS (SELECT 1 FROM jadwal jx WHERE jx.id_rute = r.id_rute "
                "AND jx.kode_jadwal LIKE ?))"
            )
            pola = f"%{cari.strip()}%"
            params.extend([pola, pola, pola, pola])
        where = f"WHERE {' AND '.join(kondisi)}" if kondisi else ""
        rows = conn.execute(
            f"""
            SELECT r.*,
                   COUNT(p.id_pemesanan) AS jumlah_pemesanan,
                   COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS total_tiket_terjual,
                   COALESCE(SUM(p.total_harga), 0) AS total_pendapatan,
                   (SELECT COUNT(*) FROM jadwal j
                    WHERE j.id_rute = r.id_rute) AS jumlah_jadwal,
                   (SELECT GROUP_CONCAT(j.kode_jadwal, ', ') FROM jadwal j
                    WHERE j.id_rute = r.id_rute) AS kode_jadwal_semua
            FROM rute r
            LEFT JOIN pemesanan p ON p.id_rute = r.id_rute
            {where}
            GROUP BY r.id_rute
            ORDER BY r.aktif DESC, r.id_rute
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def ambil_rute(id_rute: int) -> dict[str, Any] | None:
    with koneksi() as conn:
        return _dict(
            conn.execute(
                "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
            ).fetchone()
        )


# ---------------------------------------------------------------------------
# Jadwal keberangkatan & kode bisnis
# ---------------------------------------------------------------------------


def daftar_jadwal(
    id_rute: int | None = None,
    hanya_aktif: bool = False,
    cari: str = "",
) -> list[dict[str, Any]]:
    """Daftar jadwal beserta kode bisnis, jam, dan data rutenya."""
    kondisi: list[str] = []
    params: list[Any] = []
    if id_rute is not None:
        kondisi.append("j.id_rute = ?")
        params.append(id_rute)
    if hanya_aktif:
        kondisi.append("j.aktif = 1 AND r.aktif = 1")
    if cari.strip():
        pola = f"%{cari.strip()}%"
        kondisi.append(
            "(j.kode_jadwal LIKE ? OR r.kode_rute LIKE ? OR r.kota_asal LIKE ? "
            "OR r.kota_tujuan LIKE ?)"
        )
        params.extend([pola, pola, pola, pola])
    where = f"WHERE {' AND '.join(kondisi)}" if kondisi else ""
    with koneksi() as conn:
        rows = conn.execute(
            f"""
            SELECT j.*, r.kode_rute, r.kota_asal, r.kota_tujuan,
                   r.harga_tiket, r.aktif AS rute_aktif
            FROM jadwal j
            JOIN rute r ON r.id_rute = j.id_rute
            {where}
            ORDER BY r.id_rute, j.urut_keberangkatan
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def ambil_jadwal(id_jadwal: int) -> dict[str, Any] | None:
    with koneksi() as conn:
        return _dict(
            conn.execute(
                """
                SELECT j.*, r.kode_rute, r.kota_asal, r.kota_tujuan,
                       r.harga_tiket, r.aktif AS rute_aktif
                FROM jadwal j
                JOIN rute r ON r.id_rute = j.id_rute
                WHERE j.id_jadwal = ?
                """,
                (id_jadwal,),
            ).fetchone()
        )


def atur_status_jadwal(id_jadwal: int, aktif: bool) -> dict[str, Any]:
    """Mengaktifkan/menonaktifkan satu jam keberangkatan tanpa mengubah rute lain."""
    with koneksi() as conn:
        row = conn.execute(
            """
            SELECT j.*, r.kode_rute, r.kota_asal, r.kota_tujuan,
                   r.aktif AS rute_aktif
            FROM jadwal j
            JOIN rute r ON r.id_rute = j.id_rute
            WHERE j.id_jadwal = ?
            """,
            (id_jadwal,),
        ).fetchone()
        if not row:
            raise KesalahanBisnis("Jadwal tidak ditemukan.")
        if aktif and not row["rute_aktif"]:
            raise KesalahanBisnis(
                f"Rute {row['kota_asal']} - {row['kota_tujuan']} sedang nonaktif. "
                "Aktifkan rutenya terlebih dahulu sebelum mengaktifkan jadwal ini."
            )
        conn.execute(
            "UPDATE jadwal SET aktif = ? WHERE id_jadwal = ?",
            (1 if aktif else 0, id_jadwal),
        )
        _catat_log(
            conn,
            "UBAH STATUS",
            "JADWAL",
            row["kode_jadwal"],
            f"Jadwal {row['kode_jadwal']} ({row['kota_asal']} - "
            f"{row['kota_tujuan']} pukul {row['jam_keberangkatan']} WIB) "
            f"di{'aktifkan' if aktif else 'nonaktifkan'}.",
        )
        hasil = conn.execute(
            """
            SELECT j.*, r.kode_rute, r.kota_asal, r.kota_tujuan,
                   r.harga_tiket, r.aktif AS rute_aktif
            FROM jadwal j
            JOIN rute r ON r.id_rute = j.id_rute
            WHERE j.id_jadwal = ?
            """,
            (id_jadwal,),
        ).fetchone()
        return dict(hasil)


# ---------------------------------------------------------------------------
# Kursi
# ---------------------------------------------------------------------------


def _validasi_nomor_kursi(nomor: str, exclude_id: int | None = None) -> str:
    nomor_bersih = _bersihkan_teks(nomor).upper()
    if not nomor_bersih:
        raise KesalahanBisnis("Nomor kursi wajib diisi.")
    if not re.fullmatch(r"K[0-9]{1,3}", nomor_bersih):
        raise KesalahanBisnis(
            "Nomor kursi harus diawali huruf K diikuti angka, contoh K1, K9, atau K10."
        )
    return nomor_bersih


def _cek_nomor_kursi_unik(
    conn: sqlite3.Connection, nomor: str, exclude_id: int | None = None
) -> None:
    query = "SELECT nomor_kursi FROM kursi WHERE nomor_kursi = ? COLLATE NOCASE"
    params: list[Any] = [nomor]
    if exclude_id is not None:
        query += " AND id_kursi <> ?"
        params.append(exclude_id)
    if conn.execute(query, params).fetchone():
        raise KesalahanBisnis(f"Kursi {nomor} sudah terdaftar. Nomor kursi tidak boleh ganda.")


def _buat_kursi_internal(
    conn: sqlite3.Connection, nomor: str, aktif: bool = True
) -> dict[str, Any]:
    nomor = _validasi_nomor_kursi(nomor)
    _cek_nomor_kursi_unik(conn, nomor)
    cur = conn.execute(
        "INSERT INTO kursi (nomor_kursi, status_aktif) VALUES (?, ?)",
        (nomor, 1 if aktif else 0),
    )
    _catat_log(
        conn,
        "TAMBAH",
        "KURSI",
        nomor,
        f"Menambahkan kursi {nomor} dengan status {'aktif' if aktif else 'nonaktif'}.",
    )
    return dict(
        conn.execute(
            "SELECT * FROM kursi WHERE id_kursi = ?", (cur.lastrowid,)
        ).fetchone()
    )


def tambah_kursi(nomor: str, aktif: bool = True) -> dict[str, Any]:
    with koneksi() as conn:
        return _buat_kursi_internal(conn, nomor, aktif)


def ubah_kursi(id_kursi: int, nomor: str, aktif: bool) -> dict[str, Any]:
    with koneksi() as conn:
        lama = conn.execute(
            "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
        ).fetchone()
        if not lama:
            raise KesalahanBisnis("Kursi tidak ditemukan.")

        nomor_baru = _validasi_nomor_kursi(nomor, id_kursi)
        _cek_nomor_kursi_unik(conn, nomor_baru, id_kursi)

        if nomor_baru != lama["nomor_kursi"]:
            dipakai = conn.execute(
                "SELECT COUNT(*) AS n FROM detail_pemesanan WHERE id_kursi = ?",
                (id_kursi,),
            ).fetchone()["n"]
            if dipakai:
                raise KesalahanBisnis(
                    f"Nomor kursi {lama['nomor_kursi']} tidak dapat diubah karena sudah "
                    f"dipakai pada {dipakai} detail pemesanan. Nonaktifkan kursi ini "
                    "apabila tidak ingin dipakai lagi."
                )

        conn.execute(
            "UPDATE kursi SET nomor_kursi = ?, status_aktif = ? WHERE id_kursi = ?",
            (nomor_baru, 1 if aktif else 0, id_kursi),
        )
        _catat_log(
            conn,
            "UBAH",
            "KURSI",
            nomor_baru,
            f"Mengubah kursi {lama['nomor_kursi']} menjadi {nomor_baru} dengan status "
            f"{'aktif' if aktif else 'nonaktif'}.",
        )
        return dict(
            conn.execute(
                "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
            ).fetchone()
        )


def hapus_kursi(id_kursi: int) -> None:
    with koneksi() as conn:
        row = conn.execute(
            "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
        ).fetchone()
        if not row:
            raise KesalahanBisnis("Kursi tidak ditemukan.")
        dipakai = conn.execute(
            "SELECT COUNT(*) AS n FROM detail_pemesanan WHERE id_kursi = ?",
            (id_kursi,),
        ).fetchone()["n"]
        if dipakai:
            raise KesalahanBisnis(
                f"Kursi {row['nomor_kursi']} sudah dipakai pada {dipakai} detail "
                "pemesanan sehingga tidak dapat dihapus. Nonaktifkan kursi saja."
            )
        conn.execute("DELETE FROM kursi WHERE id_kursi = ?", (id_kursi,))
        _catat_log(
            conn,
            "HAPUS",
            "KURSI",
            row["nomor_kursi"],
            f"Menghapus kursi {row['nomor_kursi']}.",
        )


def _kunci_urut_kursi(nomor: str) -> tuple[int, str]:
    angka = re.search(r"([0-9]+)$", nomor or "")
    return (int(angka.group(1)) if angka else 9999, (nomor or "").upper())


def daftar_kursi(hanya_aktif: bool = False) -> list[dict[str, Any]]:
    with koneksi() as conn:
        where = "WHERE k.status_aktif = 1" if hanya_aktif else ""
        rows = conn.execute(
            f"""
            SELECT k.*,
                   COUNT(dp.id_detail_pemesanan) AS total_pemakaian,
                   COUNT(CASE WHEN p.tanggal_keberangkatan >= date('now', 'localtime')
                              THEN 1 END) AS pemakaian_mendatang
            FROM kursi k
            LEFT JOIN detail_pemesanan dp ON dp.id_kursi = k.id_kursi
            LEFT JOIN pemesanan p ON p.id_pemesanan = dp.id_pemesanan
            {where}
            GROUP BY k.id_kursi
            """
        ).fetchall()
        data = [dict(r) for r in rows]
        return sorted(data, key=lambda x: _kunci_urut_kursi(x["nomor_kursi"]))


def kursi_terpakai(
    id_rute: int, tanggal: date | str, jam: time | str
) -> list[dict[str, Any]]:
    tanggal_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)
    jam_str = jam.strftime("%H:%M") if isinstance(jam, time) else str(jam)
    with koneksi() as conn:
        rows = conn.execute(
            """
            SELECT k.id_kursi, k.nomor_kursi, p.kode_pemesanan, pl.nama_pelanggan
            FROM detail_pemesanan dp
            JOIN pemesanan p ON p.id_pemesanan = dp.id_pemesanan
            JOIN kursi k ON k.id_kursi = dp.id_kursi
            JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
            WHERE p.id_rute = ? AND p.tanggal_keberangkatan = ?
              AND p.jam_keberangkatan = ?
            """,
            (id_rute, tanggal_str, jam_str),
        ).fetchall()
        return sorted([dict(r) for r in rows], key=lambda x: _kunci_urut_kursi(x["nomor_kursi"]))


def kursi_tersedia(
    id_rute: int, tanggal: date | str, jam: time | str
) -> list[dict[str, Any]]:
    semua = daftar_kursi(hanya_aktif=True)
    terpakai = {k["id_kursi"] for k in kursi_terpakai(id_rute, tanggal, jam)}
    return [k for k in semua if k["id_kursi"] not in terpakai]


# ---------------------------------------------------------------------------
# Pemesanan
# ---------------------------------------------------------------------------


def _parse_tanggal(nilai: date | datetime | str) -> date:
    if isinstance(nilai, datetime):
        return nilai.date()
    if isinstance(nilai, date):
        return nilai
    try:
        return datetime.strptime(str(nilai), "%Y-%m-%d").date()
    except ValueError:
        raise KesalahanBisnis("Format tanggal keberangkatan tidak valid.") from None


def _parse_jam(nilai: time | datetime | str) -> time:
    if isinstance(nilai, datetime):
        return nilai.time().replace(second=0, microsecond=0)
    if isinstance(nilai, time):
        return nilai.replace(second=0, microsecond=0)
    try:
        return datetime.strptime(str(nilai), "%H:%M").time()
    except ValueError:
        raise KesalahanBisnis("Format jam keberangkatan tidak valid.") from None


def _buat_pemesanan_internal(
    conn: sqlite3.Connection,
    id_pelanggan: int,
    id_rute: int,
    tanggal: date | str,
    jam: time | str,
    id_kursi: Sequence[int],
    validasi_waktu: bool = True,
    catat_log: bool = True,
) -> dict[str, Any]:
    tanggal_date = _parse_tanggal(tanggal)
    jam_time = _parse_jam(jam)
    daftar_id = [int(x) for x in id_kursi]

    if not daftar_id:
        raise KesalahanBisnis("Pilih minimal satu kursi untuk pemesanan.")
    if len(set(daftar_id)) != len(daftar_id):
        raise KesalahanBisnis("Kursi yang dipilih tidak boleh sama dalam satu pemesanan.")

    pelanggan = conn.execute(
        "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
    ).fetchone()
    if not pelanggan:
        raise KesalahanBisnis("Pelanggan belum terdaftar. Pilih atau tambahkan pelanggan dulu.")

    rute = conn.execute(
        "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
    ).fetchone()
    if not rute:
        raise KesalahanBisnis("Rute tidak ditemukan.")
    if not rute["aktif"]:
        raise KesalahanBisnis(
            f"Rute {rute['kode_rute']} sedang nonaktif sehingga tidak dapat dipesan."
        )

    jadwal = conn.execute(
        "SELECT * FROM jadwal WHERE id_rute = ? AND jam_keberangkatan = ? "
        "AND aktif = 1",
        (id_rute, jam_time.strftime("%H:%M")),
    ).fetchone()
    if not jadwal:
        tersedia = conn.execute(
            "SELECT jam_keberangkatan FROM jadwal WHERE id_rute = ? AND aktif = 1 "
            "ORDER BY urut_keberangkatan",
            (id_rute,),
        ).fetchall()
        daftar_jam = ", ".join(f"{r['jam_keberangkatan']} WIB" for r in tersedia)
        raise KesalahanBisnis(
            f"Jadwal pukul {jam_time.strftime('%H:%M')} WIB tidak tersedia untuk rute "
            f"{rute['kota_asal']} - {rute['kota_tujuan']}. "
            + (f"Pilih salah satu jadwal: {daftar_jam}." if daftar_jam else "")
        )

    keberangkatan = datetime.combine(tanggal_date, jam_time)
    if validasi_waktu and keberangkatan <= datetime.now():
        raise KesalahanBisnis(
            f"Jadwal {keberangkatan.strftime('%d-%m-%Y %H:%M')} sudah terlewati. "
            "Pilih tanggal dan jam keberangkatan yang akan datang."
        )

    placeholders = ",".join("?" for _ in daftar_id)
    kursi_rows = conn.execute(
        f"SELECT * FROM kursi WHERE id_kursi IN ({placeholders})", daftar_id
    ).fetchall()
    if len(kursi_rows) != len(daftar_id):
        raise KesalahanBisnis("Ada kursi yang tidak ditemukan di database.")
    nonaktif = [r["nomor_kursi"] for r in kursi_rows if not r["status_aktif"]]
    if nonaktif:
        raise KesalahanBisnis(
            "Kursi berikut sedang nonaktif dan tidak dapat dipilih: "
            + ", ".join(sorted(nonaktif, key=_kunci_urut_kursi))
            + "."
        )

    terpakai = conn.execute(
        f"""
        SELECT k.nomor_kursi
        FROM detail_pemesanan dp
        JOIN pemesanan p ON p.id_pemesanan = dp.id_pemesanan
        JOIN kursi k ON k.id_kursi = dp.id_kursi
        WHERE p.id_rute = ? AND p.tanggal_keberangkatan = ?
          AND p.jam_keberangkatan = ? AND dp.id_kursi IN ({placeholders})
        """,
        [id_rute, tanggal_date.isoformat(), jam_time.strftime("%H:%M"), *daftar_id],
    ).fetchall()
    if terpakai:
        nomor = ", ".join(sorted((r["nomor_kursi"] for r in terpakai), key=_kunci_urut_kursi))
        raise KesalahanBisnis(
            f"Kursi {nomor} sudah dipesan pada rute, tanggal, dan jam tersebut. "
            "Silakan pilih kursi lain."
        )

    harga = int(rute["harga_tiket"])
    jumlah = len(daftar_id)
    total = harga * jumlah
    kode = _kode_berikutnya(conn, "pemesanan", "PSN")

    cur = conn.execute(
        """
        INSERT INTO pemesanan
            (kode_pemesanan, id_pelanggan, id_rute, tanggal_keberangkatan,
             jam_keberangkatan, jumlah_pesan_tiket, harga_saat_pemesanan, total_harga)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kode,
            id_pelanggan,
            id_rute,
            tanggal_date.isoformat(),
            jam_time.strftime("%H:%M"),
            jumlah,
            harga,
            total,
        ),
    )
    id_pemesanan = int(cur.lastrowid)

    for kid in daftar_id:
        conn.execute(
            "INSERT INTO detail_pemesanan (id_pemesanan, id_kursi, harga_satuan) "
            "VALUES (?, ?, ?)",
            (id_pemesanan, kid, harga),
        )

    if catat_log:
        _catat_log(
            conn,
            "TAMBAH",
            "PEMESANAN",
            kode,
            f"Pemesanan {kode} untuk {pelanggan['nama_pelanggan']} rute "
            f"{rute['kota_asal']} - {rute['kota_tujuan']} "
            f"({jadwal['kode_jadwal']}) tanggal "
            f"{tanggal_date.strftime('%d-%m-%Y')} pukul {jam_time.strftime('%H:%M')} "
            f"sebanyak {jumlah} tiket.",
        )

    return _ambil_detail_pemesanan(conn, id_pemesanan)


def buat_pemesanan(
    id_pelanggan: int,
    id_rute: int,
    tanggal: date | str,
    jam: time | str,
    id_kursi: Sequence[int],
) -> dict[str, Any]:
    with koneksi() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return _buat_pemesanan_internal(
            conn, id_pelanggan, id_rute, tanggal, jam, id_kursi
        )


def _ambil_detail_pemesanan(
    conn: sqlite3.Connection, id_pemesanan: int
) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT p.*,
               pl.kode_pelanggan, pl.nama_pelanggan, pl.nomor_telepon,
               r.kode_rute, r.kota_asal, r.kota_tujuan,
               r.harga_tiket AS harga_tiket_saat_ini, r.aktif AS rute_aktif,
               j.kode_jadwal, j.urut_keberangkatan
        FROM pemesanan p
        JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
        JOIN rute r ON r.id_rute = p.id_rute
        LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                           AND j.jam_keberangkatan = p.jam_keberangkatan
        WHERE p.id_pemesanan = ?
        """,
        (id_pemesanan,),
    ).fetchone()
    if not row:
        raise KesalahanBisnis("Pemesanan tidak ditemukan.")
    data = dict(row)
    kursi_rows = conn.execute(
        """
        SELECT k.id_kursi, k.nomor_kursi, dp.harga_satuan
        FROM detail_pemesanan dp
        JOIN kursi k ON k.id_kursi = dp.id_kursi
        WHERE dp.id_pemesanan = ?
        """,
        (id_pemesanan,),
    ).fetchall()
    data["kursi"] = sorted([dict(r) for r in kursi_rows], key=lambda x: _kunci_urut_kursi(x["nomor_kursi"]))
    data["nomor_kursi"] = ", ".join(k["nomor_kursi"] for k in data["kursi"])
    return data


def ambil_pemesanan(id_pemesanan: int) -> dict[str, Any]:
    with koneksi() as conn:
        return _ambil_detail_pemesanan(conn, id_pemesanan)


def daftar_pemesanan(
    cari: str = "",
    id_rute: int | None = None,
    tanggal_dari: date | str | None = None,
    tanggal_sampai: date | str | None = None,
    batas: int | None = None,
) -> list[dict[str, Any]]:
    kondisi: list[str] = []
    params: list[Any] = []

    if cari.strip():
        pola = f"%{cari.strip()}%"
        kondisi.append(
            """(
                p.kode_pemesanan LIKE ? OR pl.kode_pelanggan LIKE ?
                OR pl.nama_pelanggan LIKE ? OR pl.nomor_telepon LIKE ?
                OR r.kode_rute LIKE ? OR r.kota_asal LIKE ? OR r.kota_tujuan LIKE ?
                OR j.kode_jadwal LIKE ?
                OR EXISTS (
                    SELECT 1 FROM detail_pemesanan dx
                    JOIN kursi kx ON kx.id_kursi = dx.id_kursi
                    WHERE dx.id_pemesanan = p.id_pemesanan
                      AND kx.nomor_kursi LIKE ?
                )
            )"""
        )
        params.extend([pola] * 9)
    if id_rute is not None:
        kondisi.append("p.id_rute = ?")
        params.append(id_rute)
    if tanggal_dari:
        kondisi.append("p.tanggal_keberangkatan >= ?")
        params.append(
            tanggal_dari.isoformat() if isinstance(tanggal_dari, date) else str(tanggal_dari)
        )
    if tanggal_sampai:
        kondisi.append("p.tanggal_keberangkatan <= ?")
        params.append(
            tanggal_sampai.isoformat() if isinstance(tanggal_sampai, date) else str(tanggal_sampai)
        )

    where = f"WHERE {' AND '.join(kondisi)}" if kondisi else ""
    limit = f"LIMIT {int(batas)}" if batas else ""

    with koneksi() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, pl.kode_pelanggan, pl.nama_pelanggan, pl.nomor_telepon,
                   r.kode_rute, r.kota_asal, r.kota_tujuan,
                   j.kode_jadwal, j.urut_keberangkatan
            FROM pemesanan p
            JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
            JOIN rute r ON r.id_rute = p.id_rute
            LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                               AND j.jam_keberangkatan = p.jam_keberangkatan
            {where}
            ORDER BY p.tanggal_keberangkatan ASC, p.jam_keberangkatan ASC,
                     p.id_pemesanan DESC
            {limit}
            """,
            params,
        ).fetchall()
        data: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            kursi_rows = conn.execute(
                """
                SELECT k.nomor_kursi
                FROM detail_pemesanan dp
                JOIN kursi k ON k.id_kursi = dp.id_kursi
                WHERE dp.id_pemesanan = ?
                """,
                (item["id_pemesanan"],),
            ).fetchall()
            nomor = sorted((r["nomor_kursi"] for r in kursi_rows), key=_kunci_urut_kursi)
            item["nomor_kursi"] = ", ".join(nomor)
            data.append(item)
        return data


def batalkan_pemesanan(id_pemesanan: int) -> dict[str, Any]:
    with koneksi() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT p.*, pl.nama_pelanggan, r.kota_asal, r.kota_tujuan,
                   j.kode_jadwal
            FROM pemesanan p
            JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
            JOIN rute r ON r.id_rute = p.id_rute
            LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                               AND j.jam_keberangkatan = p.jam_keberangkatan
            WHERE p.id_pemesanan = ?
            """,
            (id_pemesanan,),
        ).fetchone()
        if not row:
            raise KesalahanBisnis(
                "Pemesanan tidak ditemukan. Mungkin sudah dibatalkan sebelumnya."
            )
        kursi_rows = conn.execute(
            """
            SELECT k.nomor_kursi FROM detail_pemesanan dp
            JOIN kursi k ON k.id_kursi = dp.id_kursi
            WHERE dp.id_pemesanan = ?
            """,
            (id_pemesanan,),
        ).fetchall()
        nomor = sorted((r["nomor_kursi"] for r in kursi_rows), key=_kunci_urut_kursi)
        data = dict(row)
        data["nomor_kursi"] = ", ".join(nomor)

        # ON DELETE CASCADE menghapus detail_pemesanan; kursi otomatis tersedia lagi.
        conn.execute("DELETE FROM pemesanan WHERE id_pemesanan = ?", (id_pemesanan,))
        _catat_log(
            conn,
            "BATAL",
            "PEMESANAN",
            row["kode_pemesanan"],
            f"Membatalkan pemesanan {row['kode_pemesanan']} milik "
            f"{row['nama_pelanggan']} rute {row['kota_asal']} - {row['kota_tujuan']} "
            f"({row['kode_jadwal'] or '-'}) "
            f"tanggal {row['tanggal_keberangkatan']} pukul {row['jam_keberangkatan']} "
            f"kursi {data['nomor_kursi']}. Kursi dikembalikan ke status tersedia. "
            "Pengembalian dana dilakukan di luar sistem.",
        )
        return data


# ---------------------------------------------------------------------------
# Ringkasan dashboard & log
# ---------------------------------------------------------------------------


def ringkasan_dashboard() -> dict[str, Any]:
    with koneksi() as conn:
        def scalar(query: str, params: Iterable[Any] = ()) -> int:
            row = conn.execute(query, tuple(params)).fetchone()
            return int(row[0] or 0)

        hari_ini = date.today().isoformat()
        tujuh_hari = (date.today() + timedelta(days=7)).isoformat()

        total_pelanggan = scalar("SELECT COUNT(*) FROM pelanggan")
        total_rute = scalar("SELECT COUNT(*) FROM rute")
        rute_aktif = scalar("SELECT COUNT(*) FROM rute WHERE aktif = 1")
        total_jadwal = scalar("SELECT COUNT(*) FROM jadwal")
        jadwal_aktif = scalar("SELECT COUNT(*) FROM jadwal WHERE aktif = 1")
        total_kursi = scalar("SELECT COUNT(*) FROM kursi")
        kursi_aktif = scalar("SELECT COUNT(*) FROM kursi WHERE status_aktif = 1")
        total_pemesanan = scalar("SELECT COUNT(*) FROM pemesanan")
        total_tiket = scalar("SELECT COALESCE(SUM(jumlah_pesan_tiket), 0) FROM pemesanan")
        total_pendapatan = scalar("SELECT COALESCE(SUM(total_harga), 0) FROM pemesanan")
        pemesanan_hari_ini = scalar(
            "SELECT COUNT(*) FROM pemesanan WHERE tanggal_keberangkatan = ?", (hari_ini,)
        )
        tiket_hari_ini = scalar(
            "SELECT COALESCE(SUM(jumlah_pesan_tiket), 0) FROM pemesanan "
            "WHERE tanggal_keberangkatan = ?",
            (hari_ini,),
        )
        pemesanan_7_hari = scalar(
            "SELECT COUNT(*) FROM pemesanan WHERE tanggal_keberangkatan BETWEEN ? AND ?",
            (hari_ini, tujuh_hari),
        )
        tiket_7_hari = scalar(
            "SELECT COALESCE(SUM(jumlah_pesan_tiket), 0) FROM pemesanan "
            "WHERE tanggal_keberangkatan BETWEEN ? AND ?",
            (hari_ini, tujuh_hari),
        )
        jadwal_mendatang = scalar(
            "SELECT COUNT(*) FROM (SELECT DISTINCT id_rute, tanggal_keberangkatan, "
            "jam_keberangkatan FROM pemesanan WHERE tanggal_keberangkatan >= ?)",
            (hari_ini,),
        )

        rata_rata = int(total_pendapatan / total_pemesanan) if total_pemesanan else 0
        return {
            "total_pelanggan": total_pelanggan,
            "total_rute": total_rute,
            "rute_aktif": rute_aktif,
            "total_jadwal": total_jadwal,
            "jadwal_aktif": jadwal_aktif,
            "total_kursi": total_kursi,
            "kursi_aktif": kursi_aktif,
            "total_pemesanan": total_pemesanan,
            "total_tiket": total_tiket,
            "total_pendapatan": total_pendapatan,
            "pemesanan_hari_ini": pemesanan_hari_ini,
            "tiket_hari_ini": tiket_hari_ini,
            "pemesanan_7_hari": pemesanan_7_hari,
            "tiket_7_hari": tiket_7_hari,
            "jadwal_mendatang": jadwal_mendatang,
            "rata_rata_transaksi": rata_rata,
        }


def rute_terpopuler(limit: int = 5) -> list[dict[str, Any]]:
    with koneksi() as conn:
        rows = conn.execute(
            """
            SELECT r.kode_rute, r.kota_asal || ' - ' || r.kota_tujuan AS rute,
                   COUNT(p.id_pemesanan) AS jumlah_pemesanan,
                   COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS jumlah_tiket,
                   COALESCE(SUM(p.total_harga), 0) AS pendapatan
            FROM rute r
            JOIN pemesanan p ON p.id_rute = r.id_rute
            GROUP BY r.id_rute
            ORDER BY jumlah_tiket DESC, pendapatan DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def keberangkatan_mendatang(limit: int = 6) -> list[dict[str, Any]]:
    with koneksi() as conn:
        rows = conn.execute(
            """
            SELECT p.id_rute, p.tanggal_keberangkatan, p.jam_keberangkatan,
                   r.kode_rute, r.kota_asal, r.kota_tujuan, r.harga_tiket,
                   j.kode_jadwal, j.urut_keberangkatan,
                   COUNT(DISTINCT p.id_pemesanan) AS jumlah_pemesanan,
                   SUM(p.jumlah_pesan_tiket) AS tiket_terjual
            FROM pemesanan p
            JOIN rute r ON r.id_rute = p.id_rute
            LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                               AND j.jam_keberangkatan = p.jam_keberangkatan
            WHERE p.tanggal_keberangkatan >= date('now', 'localtime')
            GROUP BY p.id_rute, p.tanggal_keberangkatan, p.jam_keberangkatan
            ORDER BY p.tanggal_keberangkatan ASC, p.jam_keberangkatan ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def pemesanan_terbaru(limit: int = 6) -> list[dict[str, Any]]:
    with koneksi() as conn:
        rows = conn.execute(
            """
            SELECT p.*, pl.kode_pelanggan, pl.nama_pelanggan, pl.nomor_telepon,
                   r.kode_rute, r.kota_asal, r.kota_tujuan,
                   j.kode_jadwal
            FROM pemesanan p
            JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
            JOIN rute r ON r.id_rute = p.id_rute
            LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                               AND j.jam_keberangkatan = p.jam_keberangkatan
            ORDER BY p.dibuat_pada DESC, p.id_pemesanan DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        data: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            kursi_rows = conn.execute(
                """
                SELECT k.nomor_kursi
                FROM detail_pemesanan dp
                JOIN kursi k ON k.id_kursi = dp.id_kursi
                WHERE dp.id_pemesanan = ?
                """,
                (item["id_pemesanan"],),
            ).fetchall()
            nomor = sorted((r["nomor_kursi"] for r in kursi_rows), key=_kunci_urut_kursi)
            item["nomor_kursi"] = ", ".join(nomor)
            data.append(item)
        return data


def pendapatan_per_tanggal(limit: int = 10) -> list[dict[str, Any]]:
    with koneksi() as conn:
        rows = conn.execute(
            """
            SELECT tanggal_keberangkatan,
                   COALESCE(SUM(total_harga), 0) AS pendapatan,
                   COALESCE(SUM(jumlah_pesan_tiket), 0) AS tiket
            FROM pemesanan
            GROUP BY tanggal_keberangkatan
            ORDER BY tanggal_keberangkatan DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def jadwal_padat(limit: int = 5) -> list[dict[str, Any]]:
    """Jadwal dengan okupansi kursi tertinggi (kursi aktif dipakai sebagai basis)."""
    with koneksi() as conn:
        kapasitas = conn.execute(
            "SELECT COUNT(*) AS n FROM kursi WHERE status_aktif = 1"
        ).fetchone()["n"]
        rows = conn.execute(
            """
            SELECT p.id_rute, p.tanggal_keberangkatan, p.jam_keberangkatan,
                   r.kode_rute, r.kota_asal, r.kota_tujuan,
                   j.kode_jadwal, j.urut_keberangkatan,
                   SUM(p.jumlah_pesan_tiket) AS tiket
            FROM pemesanan p
            JOIN rute r ON r.id_rute = p.id_rute
            LEFT JOIN jadwal j ON j.id_rute = p.id_rute
                               AND j.jam_keberangkatan = p.jam_keberangkatan
            WHERE p.tanggal_keberangkatan >= date('now', 'localtime')
            GROUP BY p.id_rute, p.tanggal_keberangkatan, p.jam_keberangkatan
            ORDER BY tiket DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        hasil = []
        for row in rows:
            item = dict(row)
            item["kapasitas"] = kapasitas
            item["persentase"] = (
                min(100, round(item["tiket"] / kapasitas * 100)) if kapasitas else 0
            )
            hasil.append(item)
        return hasil


def daftar_log(
    cari: str = "", entitas: str | None = None, batas: int = 200
) -> list[dict[str, Any]]:
    kondisi: list[str] = []
    params: list[Any] = []
    if cari.strip():
        pola = f"%{cari.strip()}%"
        kondisi.append(
            "(referensi LIKE ? OR keterangan LIKE ? OR aksi LIKE ? OR entitas LIKE ?)"
        )
        params.extend([pola, pola, pola, pola])
    if entitas:
        kondisi.append("entitas = ?")
        params.append(entitas)
    where = f"WHERE {' AND '.join(kondisi)}" if kondisi else ""
    with koneksi() as conn:
        rows = conn.execute(
            f"SELECT * FROM log_aktivitas {where} ORDER BY id_log DESC LIMIT ?",
            [*params, int(batas)],
        ).fetchall()
        return [dict(r) for r in rows]
