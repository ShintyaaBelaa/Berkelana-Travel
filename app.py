"""Aplikasi utama Sistem Administrasi Travel Berkelana.

Jalankan dari folder proyek:
    streamlit run app.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

LOGO_FAVICON = Path(__file__).resolve().parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="Berkelana Travel — Sistem Administrasi",
    page_icon=str(LOGO_FAVICON),
    layout="wide",
    initial_sidebar_state="expanded",
)

import components as ui
import database as db
from tampilan import dashboard, kursi, log, pelanggan, pemesanan, riwayat, rute
from utils import rupiah, tanggal_indo


@st.cache_resource(show_spinner="Menyiapkan database Berkelana Travel...")
def _siapkan_aplikasi() -> bool:
    db.init_db()
    return True


_siapkan_aplikasi()

ui.terapkan_css()

HALAMAN = {
    "Dashboard": dashboard.render,
    "Pelanggan": pelanggan.render,
    "Rute & Tarif": rute.render,
    "Data Kursi": kursi.render,
    "Pemesanan Tiket": pemesanan.render,
    "Riwayat Pemesanan": riwayat.render,
    "Log Aktivitas": log.render,
}

IKON_NAVIGASI = {
    "Dashboard": "📊  Dashboard",
    "Pelanggan": "👥  Pelanggan",
    "Rute & Tarif": "🗺️  Rute & Tarif",
    "Data Kursi": "💺  Data Kursi",
    "Pemesanan Tiket": "🎫  Pemesanan Tiket",
    "Riwayat Pemesanan": "🕘  Riwayat Pemesanan",
    "Log Aktivitas": "🧾  Log Aktivitas",
}

with st.sidebar:
    ui.sidebar_brand()
    halaman = st.radio(
        "Navigasi",
        options=list(HALAMAN),
        format_func=lambda nama: IKON_NAVIGASI[nama],
        label_visibility="collapsed",
        key="navigasi_utama",
    )

    try:
        ringkas = db.ringkasan_dashboard()
        ringkasan_sidebar = (
            f"<b>{ringkas['total_pemesanan']} pemesanan aktif</b><br>"
            f"{ringkas['total_tiket']} tiket · {ringkas['rute_aktif']} rute aktif<br>"
            f"Pendapatan {rupiah(ringkas['total_pendapatan'])}"
        )
    except Exception:
        ringkasan_sidebar = "Database sedang disiapkan."

    st.divider()
    ui.sidebar_note(
        f"📅 <b>{tanggal_indo(date.today())}</b><br><br>{ringkasan_sidebar}"
    )
    st.caption("Database lokal: berkelana.db")
    st.caption("Tanpa login · Sesuai ruang lingkup sistem")

ui.tampilkan_flash()
HALAMAN[halaman]()
