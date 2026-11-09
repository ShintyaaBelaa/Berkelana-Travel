"""
services.py
=================
Aturan bisnis Sistem Administrasi Travel Berkelana.

Semua validasi B01–B10, perhitungan harga, pengecekan kursi, pencarian
transaksi, dan pembatalan ditempatkan di file ini. Lapisan antarmuka hanya
memanggil fungsi di sini lalu menampilkan hasilnya.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from datetime import date, datetime

import database as db

# ---------------------------------------------------------------------------
# PENGECUALIAN & PEMBANTU
# ---------------------------------------------------------------------------

class AturanBisnisError(Exception):
    """Kesalahan yang dapat diperbaiki oleh petugas (ditampilkan ke UI)."""


class DataTidakDitemukanError(AturanBisnisError):
    """Data yang diminta tidak ada di database."""


NAMA_BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def format_tanggal_indo(tanggal: str | date | None) -> str:
    """'2026-10-20' -> 'Selasa, 20 Oktober 2026'."""
    if not tanggal:
        return "-"
    if isinstance(tanggal, str):
        try:
            tanggal = date.fromisoformat(tanggal)
        except ValueError:
            return tanggal
    return f"{NAMA_HARI[tanggal.weekday()]}, {tanggal.day} {NAMA_BULAN[tanggal.month - 1]} {tanggal.year}"


def format_tanggal_singkat(tanggal: str | date | None) -> str:
    """'2026-10-20' -> '20 Okt 2026'."""
    if not tanggal:
        return "-"
    if isinstance(tanggal, str):
        try:
            tanggal = date.fromisoformat(tanggal)
        except ValueError:
            return tanggal
    bulan = NAMA_BULAN[tanggal.month - 1][:3]
    return f"{tanggal.day} {bulan} {tanggal.year}"


def format_rupiah(nilai: float | None) -> str:
    """Format rupiah Indonesia: 75000 -> 'Rp75.000'."""
    try:
        angka = round(float(nilai or 0))
    except (TypeError, ValueError):
        angka = 0
    return f"Rp{angka:,}".replace(",", ".")


def format_jam(jam: str | None) -> str:
    if not jam:
        return "-"
    return jam[:5].replace(":", ".")


def _bersihkan_teks(nilai: str | None) -> str:
    return " ".join((nilai or "").strip().split())


def _validasi_data_pelanggan(nama: str, telepon: str) -> tuple[str, str]:
    """B01: nama wajib, telepon wajib dan hanya angka."""
    nama = _bersihkan_teks(nama)
    telepon = (telepon or "").strip()

    if not nama:
        raise AturanBisnisError("Nama pelanggan wajib diisi.")
    if len(nama) < 2:
        raise AturanBisnisError("Nama pelanggan minimal 2 karakter.")
    if len(nama) > 80:
        raise AturanBisnisError("Nama pelanggan maksimal 80 karakter.")
    if not telepon:
        raise AturanBisnisError("Nomor telepon wajib diisi.")
    if not telepon.isdigit():
        raise AturanBisnisError(
            "Nomor telepon hanya boleh berisi angka (tanpa huruf, spasi, atau tanda baca)."
        )
    if not 7 <= len(telepon) <= 15:
        raise AturanBisnisError("Nomor telepon harus terdiri dari 7–15 angka.")
    return nama, telepon


def _validasi_data_rute(asal: str, tujuan: str, harga: int | str | None) -> tuple[str, str, int]:
    """B03: asal ≠ tujuan dan tarif > 0."""
    asal = _bersihkan_teks(asal)
    tujuan = _bersihkan_teks(tujuan)

    if not asal or not tujuan:
        raise AturanBisnisError("Kota asal dan kota tujuan wajib diisi.")
    if asal.casefold() == tujuan.casefold():
        raise AturanBisnisError("Kota asal dan kota tujuan tidak boleh sama.")
    if len(asal) > 60 or len(tujuan) > 60:
        raise AturanBisnisError("Nama kota maksimal 60 karakter.")

    try:
        harga_int = int(harga)
    except (TypeError, ValueError):
        raise AturanBisnisError("Tarif tiket harus berupa angka.") from None
    if harga_int <= 0:
        raise AturanBisnisError("Tarif tiket harus lebih besar dari nol.")
    if harga_int > 1_000_000_000:
        raise AturanBisnisError("Tarif tiket tidak wajar (maksimal Rp1.000.000.000).")
    return asal, tujuan, harga_int


def _validasi_nomor_kursi(nomor: str) -> str:
    nomor = (nomor or "").strip().upper().replace(" ", "")
    if not re.fullmatch(r"K\d{1,3}", nomor):
        raise AturanBisnisError(
            "Nomor kursi harus berformat huruf K diikuti angka, contoh K1 atau K9."
        )
    return nomor


def validasi_jadwal(tanggal: str | date, jam: str) -> datetime:
    """B06: jadwal harus berada setelah waktu sekarang."""
    if isinstance(tanggal, date):
        tanggal_text = tanggal.isoformat()
    else:
        tanggal_text = str(tanggal)
    try:
        tanggal_obj = date.fromisoformat(tanggal_text)
    except ValueError:
        raise AturanBisnisError("Format tanggal keberangkatan tidak valid.") from None
    try:
        jam_obj = datetime.strptime(jam, "%H:%M").time()
    except (TypeError, ValueError):
        raise AturanBisnisError("Format jam keberangkatan tidak valid (contoh 08:00).") from None

    jadwal = datetime.combine(tanggal_obj, jam_obj)
    sekarang = datetime.now()
    if jadwal <= sekarang:
        raise AturanBisnisError(
            f"Jadwal {format_tanggal_singkat(tanggal_text)} pukul {format_jam(jam)} "
            f"sudah terlewati. Pilih jadwal setelah {sekarang.strftime('%d-%m-%Y %H:%M')}."
        )
    return jadwal


def _terjemahkan_integritas(exc: sqlite3.IntegrityError) -> AturanBisnisError:
    pesan = str(exc)
    if "Kursi sudah dipesan" in pesan:
        return AturanBisnisError(
            "Kursi yang dipilih sudah dipesan pada rute, tanggal, dan jam yang sama. "
            "Muat ulang denah kursi dan pilih kursi lain."
        )
    if "Kursi nonaktif" in pesan:
        return AturanBisnisError("Kursi nonaktif tidak dapat dipesan.")
    if "ux_pelanggan_nama_telepon" in pesan or "pelanggan.nama_pelanggan" in pesan:
        return AturanBisnisError(
            "Pelanggan dengan nama dan nomor telepon yang sama sudah terdaftar."
        )
    if "ux_rute_asal_tujuan" in pesan or "rute.kota_asal" in pesan:
        return AturanBisnisError("Rute dengan kota asal dan tujuan tersebut sudah terdaftar.")
    if "kursi.nomor_kursi" in pesan:
        return AturanBisnisError("Nomor kursi tersebut sudah terdaftar.")
    if "pelanggan.kode_pelanggan" in pesan:
        return AturanBisnisError("Kode pelanggan sudah digunakan. Silakan coba lagi.")
    if "rute.kode_rute" in pesan:
        return AturanBisnisError("Kode rute sudah digunakan. Silakan coba lagi.")
    if "pemesanan.kode_pemesanan" in pesan:
        return AturanBisnisError("Kode pemesanan sudah digunakan. Silakan coba lagi.")
    return AturanBisnisError(f"Data tidak dapat disimpan: {pesan}")


# ---------------------------------------------------------------------------
# PELANGGAN
# ---------------------------------------------------------------------------

def tambah_pelanggan(nama: str, telepon: str) -> dict:
    """B01 & B02: simpan pelanggan baru bila data valid dan belum ganda."""
    nama, telepon = _validasi_data_pelanggan(nama, telepon)

    try:
        with db.transaksi() as conn:
            duplikat = conn.execute(
                """
                SELECT kode_pelanggan FROM pelanggan
                WHERE nama_pelanggan = ? COLLATE NOCASE
                  AND nomor_telepon = ?
                """,
                (nama, telepon),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(
                    f"Pelanggan bernama '{nama}' dengan nomor telepon '{telepon}' "
                    f"sudah terdaftar dengan kode {duplikat['kode_pelanggan']}."
                )

            kode = db.kode_berikutnya(conn, "pelanggan", "kode_pelanggan", "P")
            cur = conn.execute(
                """
                INSERT INTO pelanggan (kode_pelanggan, nama_pelanggan, nomor_telepon)
                VALUES (?, ?, ?)
                """,
                (kode, nama, telepon),
            )
            id_pelanggan = cur.lastrowid
            return {
                "id_pelanggan": id_pelanggan,
                "kode_pelanggan": kode,
                "nama_pelanggan": nama,
                "nomor_telepon": telepon,
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def ubah_pelanggan(id_pelanggan: int, nama: str, telepon: str) -> dict:
    """Ubah data pelanggan dengan tetap menolak duplikasi B02."""
    nama, telepon = _validasi_data_pelanggan(nama, telepon)

    try:
        with db.transaksi() as conn:
            pelanggan = conn.execute(
                "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
            ).fetchone()
            if not pelanggan:
                raise DataTidakDitemukanError("Pelanggan tidak ditemukan.")

            duplikat = conn.execute(
                """
                SELECT kode_pelanggan FROM pelanggan
                WHERE nama_pelanggan = ? COLLATE NOCASE
                  AND nomor_telepon = ?
                  AND id_pelanggan <> ?
                """,
                (nama, telepon, id_pelanggan),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(
                    f"Data tersebut sudah dipakai pelanggan lain "
                    f"({duplikat['kode_pelanggan']})."
                )

            conn.execute(
                """
                UPDATE pelanggan
                SET nama_pelanggan = ?, nomor_telepon = ?
                WHERE id_pelanggan = ?
                """,
                (nama, telepon, id_pelanggan),
            )
            return {
                "id_pelanggan": id_pelanggan,
                "kode_pelanggan": pelanggan["kode_pelanggan"],
                "nama_pelanggan": nama,
                "nomor_telepon": telepon,
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def hapus_pelanggan(id_pelanggan: int) -> str:
    """Hapus pelanggan yang belum memiliki transaksi.

    Riwayat transaksi tidak boleh ikut terhapus, sehingga pelanggan yang
    sudah memiliki pemesanan ditolak penghapusannya.
    """
    with db.transaksi() as conn:
        pelanggan = conn.execute(
            "SELECT kode_pelanggan FROM pelanggan WHERE id_pelanggan = ?",
            (id_pelanggan,),
        ).fetchone()
        if not pelanggan:
            raise DataTidakDitemukanError("Pelanggan tidak ditemukan.")

        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM pemesanan WHERE id_pelanggan = ?",
            (id_pelanggan,),
        ).fetchone()["n"]
        if jumlah:
            raise AturanBisnisError(
                f"Pelanggan {pelanggan['kode_pelanggan']} memiliki {jumlah} pemesanan. "
                "Data pelanggan tidak dapat dihapus agar riwayat transaksi tetap utuh."
            )
        conn.execute("DELETE FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,))
        return pelanggan["kode_pelanggan"]


def daftar_pelanggan(cari: str = "") -> list[dict]:
    """Daftar pelanggan beserta ringkasan transaksi."""
    cari = (cari or "").strip()
    sql = """
        SELECT
            c.id_pelanggan,
            c.kode_pelanggan,
            c.nama_pelanggan,
            c.nomor_telepon,
            c.dibuat_pada,
            COUNT(p.id_pemesanan) AS jumlah_pemesanan,
            COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS total_tiket,
            COALESCE(SUM(p.total_harga), 0) AS total_belanja,
            MAX(p.dibuat_pada) AS terakhir_pemesanan
        FROM pelanggan c
        LEFT JOIN pemesanan p ON p.id_pelanggan = c.id_pelanggan
    """
    params: list = []
    if cari:
        sql += """
            WHERE c.kode_pelanggan LIKE ?
               OR c.nama_pelanggan LIKE ?
               OR c.nomor_telepon LIKE ?
        """
        pola = f"%{cari}%"
        params = [pola, pola, pola]
    sql += " GROUP BY c.id_pelanggan ORDER BY c.nama_pelanggan COLLATE NOCASE"
    conn = db.get_connection()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def ambil_pelanggan(id_pelanggan: int) -> dict | None:
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def cari_pelanggan_berdasarkan_telepon(telepon: str) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM pelanggan
            WHERE nomor_telepon LIKE ?
            ORDER BY nama_pelanggan COLLATE NOCASE
            """,
            (f"%{telepon.strip()}%",),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def riwayat_pelanggan(id_pelanggan: int) -> list[dict]:
    return cari_pemesanan(id_pelanggan=id_pelanggan, urutkan="terbaru")


# ---------------------------------------------------------------------------
# RUTE
# ---------------------------------------------------------------------------

def tambah_rute(asal: str, tujuan: str, harga: int | str) -> dict:
    asal, tujuan, harga_int = _validasi_data_rute(asal, tujuan, harga)
    try:
        with db.transaksi() as conn:
            duplikat = conn.execute(
                """
                SELECT kode_rute FROM rute
                WHERE kota_asal = ? COLLATE NOCASE
                  AND kota_tujuan = ? COLLATE NOCASE
                """,
                (asal, tujuan),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(
                    f"Rute {asal}–{tujuan} sudah terdaftar dengan kode "
                    f"{duplikat['kode_rute']}. Aktifkan kembali rute tersebut jika perlu."
                )

            kode = db.kode_berikutnya(conn, "rute", "kode_rute", "R")
            cur = conn.execute(
                """
                INSERT INTO rute (kode_rute, kota_asal, kota_tujuan, harga_tiket, aktif)
                VALUES (?, ?, ?, ?, 1)
                """,
                (kode, asal, tujuan, harga_int),
            )
            return {
                "id_rute": cur.lastrowid,
                "kode_rute": kode,
                "kota_asal": asal,
                "kota_tujuan": tujuan,
                "harga_tiket": harga_int,
                "aktif": 1,
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def ubah_rute(id_rute: int, asal: str, tujuan: str, harga: int | str) -> dict:
    """Mengubah rute/tarif. Tarif lama pada transaksi tetap memakai snapshot."""
    asal, tujuan, harga_int = _validasi_data_rute(asal, tujuan, harga)
    try:
        with db.transaksi() as conn:
            rute = conn.execute(
                "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
            ).fetchone()
            if not rute:
                raise DataTidakDitemukanError("Rute tidak ditemukan.")

            duplikat = conn.execute(
                """
                SELECT kode_rute FROM rute
                WHERE kota_asal = ? COLLATE NOCASE
                  AND kota_tujuan = ? COLLATE NOCASE
                  AND id_rute <> ?
                """,
                (asal, tujuan, id_rute),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(
                    f"Rute {asal}–{tujuan} sudah dipakai oleh {duplikat['kode_rute']}."
                )

            conn.execute(
                """
                UPDATE rute
                SET kota_asal = ?, kota_tujuan = ?, harga_tiket = ?
                WHERE id_rute = ?
                """,
                (asal, tujuan, harga_int, id_rute),
            )
            return {
                "id_rute": id_rute,
                "kode_rute": rute["kode_rute"],
                "kota_asal": asal,
                "kota_tujuan": tujuan,
                "harga_tiket": harga_int,
                "aktif": rute["aktif"],
                "harga_lama": rute["harga_tiket"],
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def atur_status_rute(id_rute: int, aktif: bool) -> dict:
    with db.transaksi() as conn:
        rute = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        if not rute:
            raise DataTidakDitemukanError("Rute tidak ditemukan.")
        conn.execute(
            "UPDATE rute SET aktif = ? WHERE id_rute = ?",
            (1 if aktif else 0, id_rute),
        )
        return {**dict(rute), "aktif": 1 if aktif else 0}


def hapus_rute(id_rute: int) -> str:
    """B04: rute yang sudah dipakai tidak boleh dihapus permanen."""
    with db.transaksi() as conn:
        rute = conn.execute(
            "SELECT kode_rute FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        if not rute:
            raise DataTidakDitemukanError("Rute tidak ditemukan.")

        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM pemesanan WHERE id_rute = ?", (id_rute,)
        ).fetchone()["n"]
        if jumlah:
            raise AturanBisnisError(
                f"Rute {rute['kode_rute']} sudah digunakan pada {jumlah} pemesanan sehingga "
                "tidak boleh dihapus. Nonaktifkan rute ini agar tidak dapat dipilih lagi."
            )
        conn.execute("DELETE FROM rute WHERE id_rute = ?", (id_rute,))
        return rute["kode_rute"]


def daftar_rute(cari: str = "", hanya_aktif: bool = False) -> list[dict]:
    cari = (cari or "").strip()
    sql = """
        SELECT
            r.id_rute,
            r.kode_rute,
            r.kota_asal,
            r.kota_tujuan,
            r.harga_tiket,
            r.aktif,
            r.dibuat_pada,
            COUNT(p.id_pemesanan) AS jumlah_pemesanan,
            COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS total_tiket,
            COALESCE(SUM(p.total_harga), 0) AS total_pendapatan,
            COUNT(DISTINCT CASE WHEN p.id_pemesanan IS NOT NULL
                  THEN p.tanggal_keberangkatan || ' ' || p.jam_keberangkatan END) AS jumlah_jadwal
        FROM rute r
        LEFT JOIN pemesanan p ON p.id_rute = r.id_rute
    """
    where: list[str] = []
    params: list = []
    if cari:
        where.append("(r.kode_rute LIKE ? OR r.kota_asal LIKE ? OR r.kota_tujuan LIKE ?)")
        pola = f"%{cari}%"
        params.extend([pola, pola, pola])
    if hanya_aktif:
        where.append("r.aktif = 1")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += """
        GROUP BY r.id_rute
        ORDER BY r.aktif DESC, r.kota_asal COLLATE NOCASE, r.kota_tujuan COLLATE NOCASE
    """
    conn = db.get_connection()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def ambil_rute(id_rute: int) -> dict | None:
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def jadwal_rute(id_rute: int, batas: int = 10) -> list[dict]:
    """Agregasi jadwal (rute + tanggal + jam) yang memiliki pemesanan."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                p.tanggal_keberangkatan,
                p.jam_keberangkatan,
                COUNT(DISTINCT p.id_pemesanan) AS jumlah_pemesanan,
                COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS jumlah_tiket,
                COALESCE(SUM(p.total_harga), 0) AS pendapatan,
                GROUP_CONCAT(DISTINCT k.nomor_kursi) AS kursi
            FROM pemesanan p
            LEFT JOIN detail_pemesanan d ON d.id_pemesanan = p.id_pemesanan
            LEFT JOIN kursi k ON k.id_kursi = d.id_kursi
            WHERE p.id_rute = ?
            GROUP BY p.tanggal_keberangkatan, p.jam_keberangkatan
            ORDER BY p.tanggal_keberangkatan DESC, p.jam_keberangkatan DESC
            LIMIT ?
            """,
            (id_rute, batas),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# KURSI
# ---------------------------------------------------------------------------

def daftar_kursi() -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                k.id_kursi,
                k.nomor_kursi,
                k.status_aktif,
                k.dibuat_pada,
                COUNT(d.id_detail_pemesanan) AS jumlah_dipakai,
                COALESCE(SUM(CASE WHEN datetime(
                        p.tanggal_keberangkatan || ' ' || p.jam_keberangkatan
                    ) >= datetime('now', 'localtime') THEN 1 ELSE 0 END), 0)
                    AS jadwal_mendatang
            FROM kursi k
            LEFT JOIN detail_pemesanan d ON d.id_kursi = k.id_kursi
            LEFT JOIN pemesanan p ON p.id_pemesanan = d.id_pemesanan
            GROUP BY k.id_kursi
            ORDER BY CAST(SUBSTR(k.nomor_kursi, 2) AS INTEGER), k.nomor_kursi
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ambil_kursi(id_kursi: int) -> dict | None:
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def tambah_kursi(nomor: str) -> dict:
    nomor = _validasi_nomor_kursi(nomor)
    try:
        with db.transaksi() as conn:
            duplikat = conn.execute(
                "SELECT id_kursi FROM kursi WHERE nomor_kursi = ? COLLATE NOCASE",
                (nomor,),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(f"Nomor kursi {nomor} sudah terdaftar.")
            cur = conn.execute(
                "INSERT INTO kursi (nomor_kursi, status_aktif) VALUES (?, 1)",
                (nomor,),
            )
            return {
                "id_kursi": cur.lastrowid,
                "nomor_kursi": nomor,
                "status_aktif": 1,
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def ubah_kursi(id_kursi: int, nomor: str, status_aktif: bool) -> dict:
    nomor = _validasi_nomor_kursi(nomor)
    try:
        with db.transaksi() as conn:
            kursi = conn.execute(
                "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
            ).fetchone()
            if not kursi:
                raise DataTidakDitemukanError("Kursi tidak ditemukan.")

            duplikat = conn.execute(
                """
                SELECT id_kursi FROM kursi
                WHERE nomor_kursi = ? COLLATE NOCASE AND id_kursi <> ?
                """,
                (nomor, id_kursi),
            ).fetchone()
            if duplikat:
                raise AturanBisnisError(f"Nomor kursi {nomor} sudah dipakai kursi lain.")

            conn.execute(
                "UPDATE kursi SET nomor_kursi = ?, status_aktif = ? WHERE id_kursi = ?",
                (nomor, 1 if status_aktif else 0, id_kursi),
            )
            return {
                "id_kursi": id_kursi,
                "nomor_kursi": nomor,
                "status_aktif": 1 if status_aktif else 0,
                "nomor_lama": kursi["nomor_kursi"],
            }
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def atur_status_kursi(id_kursi: int, aktif: bool) -> dict:
    with db.transaksi() as conn:
        kursi = conn.execute(
            "SELECT * FROM kursi WHERE id_kursi = ?", (id_kursi,)
        ).fetchone()
        if not kursi:
            raise DataTidakDitemukanError("Kursi tidak ditemukan.")
        conn.execute(
            "UPDATE kursi SET status_aktif = ? WHERE id_kursi = ?",
            (1 if aktif else 0, id_kursi),
        )
        return {**dict(kursi), "status_aktif": 1 if aktif else 0}


def hapus_kursi(id_kursi: int) -> str:
    with db.transaksi() as conn:
        kursi = conn.execute(
            "SELECT nomor_kursi FROM kursi WHERE id_kursi = ?", (id_kursi,)
        ).fetchone()
        if not kursi:
            raise DataTidakDitemukanError("Kursi tidak ditemukan.")
        jumlah = conn.execute(
            "SELECT COUNT(*) AS n FROM detail_pemesanan WHERE id_kursi = ?",
            (id_kursi,),
        ).fetchone()["n"]
        if jumlah:
            raise AturanBisnisError(
                f"Kursi {kursi['nomor_kursi']} sudah dipakai pada {jumlah} transaksi. "
                "Kursi tidak dapat dihapus; nonaktifkan saja agar tidak bisa dipilih."
            )
        conn.execute("DELETE FROM kursi WHERE id_kursi = ?", (id_kursi,))
        return kursi["nomor_kursi"]


# ---------------------------------------------------------------------------
# KETERSEDIAAN & PEMESANAN
# ---------------------------------------------------------------------------

def ambil_kursi_untuk_jadwal(id_rute: int, tanggal: str, jam: str) -> list[dict]:
    """Denah kursi untuk satu rute + tanggal + jam.

    Mengembalikan seluruh kursi beserta statusnya. ``terisi`` berarti kursi
    sudah dipakai pada jadwal tersebut, bukan pada jadwal lain.
    """
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                k.id_kursi,
                k.nomor_kursi,
                k.status_aktif,
                x.kode_pemesanan,
                x.nama_pelanggan,
                CASE WHEN x.id_kursi IS NULL THEN 0 ELSE 1 END AS terisi
            FROM kursi k
            LEFT JOIN (
                SELECT
                    d.id_kursi,
                    p.kode_pemesanan,
                    c.nama_pelanggan
                FROM detail_pemesanan d
                JOIN pemesanan p ON p.id_pemesanan = d.id_pemesanan
                JOIN pelanggan c ON c.id_pelanggan = p.id_pelanggan
                WHERE p.id_rute = ?
                  AND p.tanggal_keberangkatan = ?
                  AND p.jam_keberangkatan = ?
            ) x ON x.id_kursi = k.id_kursi
            ORDER BY CAST(SUBSTR(k.nomor_kursi, 2) AS INTEGER), k.nomor_kursi
            """,
            (id_rute, tanggal, jam),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ringkasan_jadwal(id_rute: int, tanggal: str, jam: str) -> dict:
    kursi = ambil_kursi_untuk_jadwal(id_rute, tanggal, jam)
    aktif = [k for k in kursi if k["status_aktif"] == 1]
    terisi = [k for k in aktif if k["terisi"] == 1]
    return {
        "total_kursi": len(kursi),
        "kursi_aktif": len(aktif),
        "terisi": len(terisi),
        "tersedia": len(aktif) - len(terisi),
        "nonaktif": len(kursi) - len(aktif),
        "persentase": round((len(terisi) / len(aktif)) * 100) if aktif else 0,
    }


def _ambil_nota_conn(conn: sqlite3.Connection, id_pemesanan: int) -> dict | None:
    header = conn.execute(
        "SELECT * FROM v_pemesanan_lengkap WHERE id_pemesanan = ?",
        (id_pemesanan,),
    ).fetchone()
    if not header:
        return None
    detail = conn.execute(
        """
        SELECT
            d.id_detail_pemesanan,
            d.harga_saat_pemesanan,
            k.id_kursi,
            k.nomor_kursi
        FROM detail_pemesanan d
        JOIN kursi k ON k.id_kursi = d.id_kursi
        WHERE d.id_pemesanan = ?
        ORDER BY CAST(SUBSTR(k.nomor_kursi, 2) AS INTEGER), k.nomor_kursi
        """,
        (id_pemesanan,),
    ).fetchall()
    nota = dict(header)
    nota["detail_kursi"] = [dict(row) for row in detail]
    nota["nomor_kursi"] = [row["nomor_kursi"] for row in detail]
    nota["harga_per_tiket"] = (
        detail[0]["harga_saat_pemesanan"] if detail else nota["total_harga"]
    )
    return nota


def buat_pemesanan(
    id_pelanggan: int,
    id_rute: int,
    tanggal: str,
    jam: str,
    id_kursi: Sequence[int],
) -> dict:
    """Membuat pemesanan lengkap dengan detail kursi (B05–B09).

    Seluruh pengecekan dan penyimpanan dilakukan dalam satu transaksi
    BEGIN IMMEDIATE sehingga kursi tidak mungkin terpakai dua kali.
    """
    validasi_jadwal(tanggal, jam)

    try:
        daftar_id = [int(x) for x in id_kursi]
    except (TypeError, ValueError):
        raise AturanBisnisError("Pilihan kursi tidak valid.") from None

    if not daftar_id:
        raise AturanBisnisError("Pilih minimal satu kursi untuk membuat pemesanan.")
    if len(set(daftar_id)) != len(daftar_id):
        raise AturanBisnisError("Kursi yang sama tidak boleh dipilih dua kali dalam satu pemesanan.")

    try:
        with db.transaksi() as conn:
            pelanggan = conn.execute(
                "SELECT * FROM pelanggan WHERE id_pelanggan = ?", (id_pelanggan,)
            ).fetchone()
            if not pelanggan:
                raise AturanBisnisError(
                    "Pelanggan belum terdaftar. Pilih pelanggan yang ada atau tambahkan dahulu."
                )

            rute = conn.execute(
                "SELECT * FROM rute WHERE id_rute = ?", (id_rute,)
            ).fetchone()
            if not rute:
                raise AturanBisnisError("Rute tidak ditemukan.")
            if not rute["aktif"]:
                raise AturanBisnisError(
                    f"Rute {rute['kode_rute']} sedang nonaktif sehingga tidak dapat dipesan."
                )

            placeholders = ",".join("?" for _ in daftar_id)
            kursi_rows = conn.execute(
                f"SELECT * FROM kursi WHERE id_kursi IN ({placeholders})",
                daftar_id,
            ).fetchall()
            kursi_map = {row["id_kursi"]: row for row in kursi_rows}
            if len(kursi_map) != len(daftar_id):
                raise AturanBisnisError("Sebagian kursi tidak ditemukan. Muat ulang halaman.")

            nonaktif = [row["nomor_kursi"] for row in kursi_rows if not row["status_aktif"]]
            if nonaktif:
                raise AturanBisnisError(
                    "Kursi berikut sedang nonaktif dan tidak dapat dipesan: "
                    + ", ".join(sorted(nonaktif))
                )

            bentrok = conn.execute(
                f"""
                SELECT k.nomor_kursi, p.kode_pemesanan, c.nama_pelanggan
                FROM detail_pemesanan d
                JOIN pemesanan p ON p.id_pemesanan = d.id_pemesanan
                JOIN pelanggan c ON c.id_pelanggan = p.id_pelanggan
                JOIN kursi k ON k.id_kursi = d.id_kursi
                WHERE p.id_rute = ?
                  AND p.tanggal_keberangkatan = ?
                  AND p.jam_keberangkatan = ?
                  AND d.id_kursi IN ({placeholders})
                """,
                (id_rute, tanggal, jam, *daftar_id),
            ).fetchall()
            if bentrok:
                rincian = "; ".join(
                    f"{row['nomor_kursi']} sudah dipakai {row['kode_pemesanan']} "
                    f"({row['nama_pelanggan']})"
                    for row in bentrok
                )
                raise AturanBisnisError(
                    "Kursi tidak tersedia pada jadwal ini: " + rincian + ". Pilih kursi lain."
                )

            # B09: harga disimpan per detail saat pemesanan, bukan mengikuti
            # perubahan tarif rute di masa depan.
            harga = int(rute["harga_tiket"])
            jumlah = len(daftar_id)
            total = harga * jumlah
            kode = db.kode_berikutnya(conn, "pemesanan", "kode_pemesanan", "PSN")

            cur = conn.execute(
                """
                INSERT INTO pemesanan
                    (kode_pemesanan, id_pelanggan, id_rute,
                     tanggal_keberangkatan, jam_keberangkatan,
                     jumlah_pesan_tiket, total_harga)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (kode, id_pelanggan, id_rute, tanggal, jam, jumlah, total),
            )
            id_pemesanan = cur.lastrowid

            conn.executemany(
                """
                INSERT INTO detail_pemesanan
                    (id_pemesanan, id_kursi, harga_saat_pemesanan)
                VALUES (?, ?, ?)
                """,
                [(id_pemesanan, kursi_id, harga) for kursi_id in daftar_id],
            )

            nota = _ambil_nota_conn(conn, id_pemesanan)
            if nota is None:
                raise AturanBisnisError("Pemesanan gagal dibaca kembali setelah disimpan.")
            return nota
    except sqlite3.IntegrityError as exc:
        raise _terjemahkan_integritas(exc) from exc


def batalkan_pemesanan(id_pemesanan: int) -> dict:
    """B10: hapus pemesanan + detail sehingga kursi kembali tersedia."""
    with db.transaksi() as conn:
        nota = _ambil_nota_conn(conn, id_pemesanan)
        if not nota:
            raise DataTidakDitemukanError(
                "Pemesanan tidak ditemukan. Mungkin sudah dibatalkan sebelumnya."
            )

        # detail_pemesanan memiliki ON DELETE CASCADE, tetapi penghapusan
        # eksplisit membuat maksud kode lebih jelas dan mudah diperiksa.
        conn.execute("DELETE FROM detail_pemesanan WHERE id_pemesanan = ?", (id_pemesanan,))
        conn.execute("DELETE FROM pemesanan WHERE id_pemesanan = ?", (id_pemesanan,))
        nota["dibatalkan_pada"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return nota


def cari_pemesanan(
    q: str = "",
    id_rute: int | None = None,
    id_pelanggan: int | None = None,
    dari: str | None = None,
    sampai: str | None = None,
    urutkan: str = "terbaru",
    limit: int | None = 100,
) -> list[dict]:
    """Pencarian transaksi berdasarkan kode/nama/telepon/rute dan rentang tanggal."""
    sql = "SELECT * FROM v_pemesanan_lengkap WHERE 1 = 1"
    params: list = []

    q = (q or "").strip()
    if q:
        pola = f"%{q}%"
        sql += """
            AND (
                kode_pemesanan LIKE ?
                OR nama_pelanggan LIKE ?
                OR nomor_telepon LIKE ?
                OR kode_pelanggan LIKE ?
                OR kode_rute LIKE ?
                OR kota_asal LIKE ?
                OR kota_tujuan LIKE ?
            )
        """
        params.extend([pola] * 7)
    if id_rute:
        sql += " AND id_rute = ?"
        params.append(id_rute)
    if id_pelanggan:
        sql += " AND id_pelanggan = ?"
        params.append(id_pelanggan)
    if dari:
        sql += " AND tanggal_keberangkatan >= ?"
        params.append(dari)
    if sampai:
        sql += " AND tanggal_keberangkatan <= ?"
        params.append(sampai)

    urutan = {
        "terbaru": "dibuat_pada DESC, id_pemesanan DESC",
        "keberangkatan": "tanggal_keberangkatan ASC, jam_keberangkatan ASC",
        "terlama": "dibuat_pada ASC, id_pemesanan ASC",
        "harga": "total_harga DESC, dibuat_pada DESC",
        "kode": "kode_pemesanan ASC",
    }.get(urutkan, "dibuat_pada DESC, id_pemesanan DESC")
    sql += f" ORDER BY {urutan}"

    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))

    conn = db.get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def ambil_nota(id_pemesanan: int) -> dict | None:
    conn = db.get_connection()
    try:
        return _ambil_nota_conn(conn, id_pemesanan)
    finally:
        conn.close()


def cari_nota_berdasarkan_kode(kode: str) -> dict | None:
    kode = (kode or "").strip().upper()
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT id_pemesanan FROM pemesanan WHERE kode_pemesanan = ?",
            (kode,),
        ).fetchone()
        return _ambil_nota_conn(conn, row["id_pemesanan"]) if row else None
    finally:
        conn.close()


def ringkasan_jadwal_terdekat(batas: int = 8) -> list[dict]:
    """Jadwal mendatang yang sudah memiliki pemesanan + okupansi kursi."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                p.id_rute,
                r.kode_rute,
                r.kota_asal,
                r.kota_tujuan,
                p.tanggal_keberangkatan,
                p.jam_keberangkatan,
                COUNT(DISTINCT p.id_pemesanan) AS jumlah_pemesanan,
                COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS jumlah_tiket,
                COALESCE(SUM(p.total_harga), 0) AS pendapatan
            FROM pemesanan p
            JOIN rute r ON r.id_rute = p.id_rute
            WHERE datetime(p.tanggal_keberangkatan || ' ' || p.jam_keberangkatan)
                  >= datetime('now', 'localtime')
            GROUP BY p.id_rute, p.tanggal_keberangkatan, p.jam_keberangkatan
            ORDER BY p.tanggal_keberangkatan ASC, p.jam_keberangkatan ASC
            LIMIT ?
            """,
            (batas,),
        ).fetchall()
        hasil = []
        kapasitas_row = conn.execute(
            "SELECT COUNT(*) AS n FROM kursi WHERE status_aktif = 1"
        ).fetchone()
        kapasitas = kapasitas_row["n"] if kapasitas_row else 0
        for row in rows:
            item = dict(row)
            item["kapasitas"] = kapasitas
            item["okupansi"] = (
                min(100, round((item["jumlah_tiket"] / kapasitas) * 100))
                if kapasitas
                else 0
            )
            hasil.append(item)
        return hasil
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DASHBOARD & LAPORAN RINGKAS
# ---------------------------------------------------------------------------

def ringkasan_dashboard() -> dict:
    conn = db.get_connection()
    try:
        pelanggan = conn.execute(
            "SELECT COUNT(*) AS n FROM pelanggan"
        ).fetchone()["n"]
        rute_aktif = conn.execute(
            "SELECT COUNT(*) AS n FROM rute WHERE aktif = 1"
        ).fetchone()["n"]
        rute_nonaktif = conn.execute(
            "SELECT COUNT(*) AS n FROM rute WHERE aktif = 0"
        ).fetchone()["n"]
        pemesanan = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(jumlah_pesan_tiket), 0) AS tiket, "
            "COALESCE(SUM(total_harga), 0) AS pendapatan FROM pemesanan"
        ).fetchone()
        bulan_ini = conn.execute(
            """
            SELECT COUNT(*) AS n, COALESCE(SUM(jumlah_pesan_tiket), 0) AS tiket,
                   COALESCE(SUM(total_harga), 0) AS pendapatan
            FROM pemesanan
            WHERE strftime('%Y-%m', dibuat_pada) = strftime('%Y-%m', 'now', 'localtime')
            """
        ).fetchone()
        pelanggan_baru = conn.execute(
            """
            SELECT COUNT(*) AS n FROM pelanggan
            WHERE strftime('%Y-%m', dibuat_pada) = strftime('%Y-%m', 'now', 'localtime')
            """
        ).fetchone()["n"]
        kursi_aktif = conn.execute(
            "SELECT COUNT(*) AS n FROM kursi WHERE status_aktif = 1"
        ).fetchone()["n"]
        jadwal_mendatang = conn.execute(
            """
            SELECT COUNT(DISTINCT tanggal_keberangkatan || ' ' || jam_keberangkatan) AS n
            FROM pemesanan
            WHERE datetime(tanggal_keberangkatan || ' ' || jam_keberangkatan)
                  >= datetime('now', 'localtime')
            """
        ).fetchone()["n"]
        return {
            "pelanggan": pelanggan,
            "rute_aktif": rute_aktif,
            "rute_nonaktif": rute_nonaktif,
            "pemesanan": pemesanan["n"],
            "tiket": pemesanan["tiket"],
            "pendapatan": pemesanan["pendapatan"],
            "pemesanan_bulan_ini": bulan_ini["n"],
            "tiket_bulan_ini": bulan_ini["tiket"],
            "pendapatan_bulan_ini": bulan_ini["pendapatan"],
            "pelanggan_baru_bulan_ini": pelanggan_baru,
            "kursi_aktif": kursi_aktif,
            "jadwal_mendatang": jadwal_mendatang,
        }
    finally:
        conn.close()


def pendapatan_per_rute(batas: int = 8) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                r.kode_rute,
                r.kota_asal,
                r.kota_tujuan,
                COUNT(p.id_pemesanan) AS jumlah_pemesanan,
                COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS jumlah_tiket,
                COALESCE(SUM(p.total_harga), 0) AS pendapatan
            FROM rute r
            LEFT JOIN pemesanan p ON p.id_rute = r.id_rute
            GROUP BY r.id_rute
            ORDER BY pendapatan DESC, jumlah_pemesanan DESC
            LIMIT ?
            """,
            (batas,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def pemesanan_per_tanggal(batas: int = 14) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                tanggal_keberangkatan,
                COUNT(*) AS jumlah_pemesanan,
                COALESCE(SUM(jumlah_pesan_tiket), 0) AS jumlah_tiket,
                COALESCE(SUM(total_harga), 0) AS pendapatan
            FROM pemesanan
            WHERE tanggal_keberangkatan >= date('now', 'localtime')
            GROUP BY tanggal_keberangkatan
            ORDER BY tanggal_keberangkatan ASC
            LIMIT ?
            """,
            (batas,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def pemesanan_terbaru(batas: int = 6) -> list[dict]:
    return cari_pemesanan(urutkan="terbaru", limit=batas)


def pelanggan_teratas(batas: int = 5) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                c.kode_pelanggan,
                c.nama_pelanggan,
                c.nomor_telepon,
                COUNT(p.id_pemesanan) AS jumlah_pemesanan,
                COALESCE(SUM(p.jumlah_pesan_tiket), 0) AS jumlah_tiket,
                COALESCE(SUM(p.total_harga), 0) AS total_belanja
            FROM pelanggan c
            JOIN pemesanan p ON p.id_pelanggan = c.id_pelanggan
            GROUP BY c.id_pelanggan
            ORDER BY total_belanja DESC, jumlah_pemesanan DESC
            LIMIT ?
            """,
            (batas,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def data_untuk_ekspor(
    q: str = "",
    id_rute: int | None = None,
    dari: str | None = None,
    sampai: str | None = None,
) -> list[dict]:
    """Data transaksi siap diekspor ke CSV dari halaman riwayat."""
    hasil = cari_pemesanan(q=q, id_rute=id_rute, dari=dari, sampai=sampai, limit=None)
    return [
        {
            "Kode Pemesanan": row["kode_pemesanan"],
            "Kode Pelanggan": row["kode_pelanggan"],
            "Nama Pelanggan": row["nama_pelanggan"],
            "Nomor Telepon": row["nomor_telepon"],
            "Kode Rute": row["kode_rute"],
            "Kota Asal": row["kota_asal"],
            "Kota Tujuan": row["kota_tujuan"],
            "Tanggal Keberangkatan": row["tanggal_keberangkatan"],
            "Jam Keberangkatan": row["jam_keberangkatan"],
            "Kursi": row["daftar_kursi"],
            "Jumlah Tiket": row["jumlah_pesan_tiket"],
            "Total Harga": row["total_harga"],
            "Dibuat Pada": row["dibuat_pada"],
        }
        for row in hasil
    ]


def hitung_total(harga: int, jumlah_kursi: int) -> int:
    """Pembantu tampilan agar perhitungan di UI sama dengan layanan."""
    return int(harga) * int(jumlah_kursi)


def info_ringkas_data() -> dict:
    """Jumlah baris untuk kartu informasi di sidebar."""
    conn = db.get_connection()
    try:
        return {
            "pelanggan": conn.execute("SELECT COUNT(*) AS n FROM pelanggan").fetchone()["n"],
            "rute": conn.execute("SELECT COUNT(*) AS n FROM rute").fetchone()["n"],
            "kursi": conn.execute("SELECT COUNT(*) AS n FROM kursi").fetchone()["n"],
            "pemesanan": conn.execute("SELECT COUNT(*) AS n FROM pemesanan").fetchone()["n"],
        }
    finally:
        conn.close()
