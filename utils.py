"""Utilitas format tampilan dan pembuatan teks nota."""

from __future__ import annotations

import html
from datetime import date, datetime, time
from typing import Any

NAMA_HARI = [
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
    "Minggu",
]
NAMA_BULAN = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]
NAMA_BULAN_SINGKAT = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
]


def rupiah(nilai: int | float | None) -> str:
    try:
        angka = int(round(float(nilai or 0)))
    except (TypeError, ValueError):
        angka = 0
    return f"Rp{angka:,}".replace(",", ".")


def ke_tanggal(nilai: date | datetime | str) -> date:
    if isinstance(nilai, datetime):
        return nilai.date()
    if isinstance(nilai, date):
        return nilai
    return datetime.strptime(str(nilai), "%Y-%m-%d").date()


def ke_waktu(nilai: time | datetime | str) -> time:
    if isinstance(nilai, datetime):
        return nilai.time()
    if isinstance(nilai, time):
        return nilai
    return datetime.strptime(str(nilai), "%H:%M").time()


def tanggal_indo(nilai: date | datetime | str) -> str:
    """Contoh: Jumat, 20 November 2026."""
    tgl = ke_tanggal(nilai)
    return f"{NAMA_HARI[tgl.weekday()]}, {tgl.day} {NAMA_BULAN[tgl.month - 1]} {tgl.year}"


def tanggal_singkat(nilai: date | datetime | str) -> str:
    """Contoh: 20 Nov 2026."""
    tgl = ke_tanggal(nilai)
    return f"{tgl.day:02d} {NAMA_BULAN_SINGKAT[tgl.month - 1]} {tgl.year}"


def tanggal_input(nilai: date | datetime | str) -> str:
    """Contoh: 20-11-2026 (untuk tabel)."""
    tgl = ke_tanggal(nilai)
    return tgl.strftime("%d-%m-%Y")


def jam_indo(nilai: time | datetime | str) -> str:
    return f"{ke_waktu(nilai).strftime('%H:%M')} WIB"


def waktu_lengkap(nilai: datetime | str | None) -> str:
    if not nilai:
        return "-"
    if isinstance(nilai, str):
        try:
            nilai = datetime.strptime(nilai, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return nilai
    return f"{tanggal_singkat(nilai)} {nilai.strftime('%H:%M')}"


def tanggal_waktu_keberangkatan(tanggal: date | str, jam: time | str) -> datetime:
    return datetime.combine(ke_tanggal(tanggal), ke_waktu(jam))


def jadwal_sudah_lewat(tanggal: date | str, jam: time | str) -> bool:
    return tanggal_waktu_keberangkatan(tanggal, jam) <= datetime.now()


def label_sisa_waktu(tanggal: date | str, jam: time | str) -> str:
    selisih = tanggal_waktu_keberangkatan(tanggal, jam) - datetime.now()
    if selisih.total_seconds() <= 0:
        return "Sudah lewat"
    hari = selisih.days
    if hari >= 1:
        return f"{hari} hari lagi"
    jam_ke = int(selisih.total_seconds() // 3600)
    menit = int((selisih.total_seconds() % 3600) // 60)
    if jam_ke:
        return f"{jam_ke} jam {menit} menit lagi"
    return f"{max(menit, 1)} menit lagi"


def esc(nilai: Any) -> str:
    return html.escape(str(nilai if nilai is not None else ""))


def potong(nilai: str, panjang: int = 34) -> str:
    teks = str(nilai or "")
    return teks if len(teks) <= panjang else teks[: panjang - 1] + "…"


def buat_teks_nota(data: dict[str, Any]) -> str:
    """Nota teks siap unduh / tampil pada blok monospace."""
    garis = "=" * 48
    tipis = "-" * 48
    kursi = data.get("nomor_kursi") or ", ".join(
        k.get("nomor_kursi", "") for k in data.get("kursi", [])
    )
    lines = [
        garis,
        "            BERKELANA TRAVEL",
        "      Sistem Administrasi Perjalanan",
        garis,
        f"Kode Pemesanan : {data.get('kode_pemesanan', '-')}",
        f"Dibuat         : {waktu_lengkap(data.get('dibuat_pada'))}",
        f"Status         : AKTIF",
        tipis,
        "PELANGGAN",
        f"Nama           : {data.get('nama_pelanggan', '-')}",
        f"Kode           : {data.get('kode_pelanggan', '-')}",
        f"Telepon        : {data.get('nomor_telepon', '-')}",
        tipis,
        "PERJALANAN",
        f"Rute           : {data.get('kota_asal', '-')} -> {data.get('kota_tujuan', '-')}",
        f"Kode Jadwal    : {data.get('kode_jadwal') or data.get('kode_rute', '-')}",
        f"Kode Rute      : {data.get('kode_rute', '-')}",
        f"Tanggal        : {tanggal_indo(data.get('tanggal_keberangkatan', date.today()))}",
        f"Jam            : {jam_indo(data.get('jam_keberangkatan', '00:00'))}",
        f"Kursi          : {kursi or '-'}",
        tipis,
        "RINCIAN BIAYA",
        f"Harga per tiket: {rupiah(data.get('harga_saat_pemesanan'))}",
        f"Jumlah tiket   : {data.get('jumlah_pesan_tiket', 0)} tiket",
        f"Total bayar    : {rupiah(data.get('total_harga'))}",
        garis,
        "Pembayaran dilakukan di loket.",
        "Simpan nota ini sebagai bukti pemesanan.",
        "Pembatalan dapat dilakukan melalui petugas.",
        "",
        "Terima kasih telah memilih Berkelana Travel.",
        garis,
    ]
    return "\n".join(lines)


def nama_file_nota(data: dict[str, Any]) -> str:
    kode = data.get("kode_pemesanan", "nota")
    return f"nota-{kode}.txt"
