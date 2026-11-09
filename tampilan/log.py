"""Halaman log aktivitas sistem."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import database as db
from utils import waktu_lengkap


def render() -> None:
    ui.page_header(
        "🧾",
        "Log Aktivitas",
        "Jejak audit perubahan data dan transaksi yang tersimpan otomatis oleh sistem.",
    )

    semua = db.daftar_log(batas=1000)
    kolom = st.columns(4)
    with kolom[0]:
        ui.metrik("Total catatan", f"{len(semua)}", "🗂️", "Maksimal 1.000 catatan terbaru")
    with kolom[1]:
        ui.metrik(
            "Transaksi",
            f"{sum(1 for x in semua if x['entitas'] == 'PEMESANAN')}",
            "🎫",
            "Tambah & batal pemesanan",
        )
    with kolom[2]:
        ui.metrik(
            "Pelanggan",
            f"{sum(1 for x in semua if x['entitas'] == 'PELANGGAN')}",
            "👤",
            "Perubahan data pelanggan",
        )
    with kolom[3]:
        ui.metrik(
            "Rute & kursi",
            f"{sum(1 for x in semua if x['entitas'] in ('RUTE', 'KURSI'))}",
            "🗺️",
            "Perubahan master data",
        )

    with st.container(border=True):
        kiri, tengah, kanan = st.columns([1.6, 1, 1])
        cari = kiri.text_input(
            "🔍 Cari log",
            placeholder="Cari referensi, aksi, atau keterangan...",
            key="cari_log",
        )
        entitas = tengah.selectbox(
            "Entitas",
            options=[
                "Semua",
                "PELANGGAN",
                "RUTE",
                "KURSI",
                "PEMESANAN",
                "SISTEM",
            ],
            key="filter_entitas_log",
        )
        batas = kanan.selectbox(
            "Jumlah tampil",
            options=[50, 100, 200, 500, 1000],
            index=2,
            key="batas_log",
        )

    data = db.daftar_log(
        cari=cari,
        entitas=None if entitas == "Semua" else entitas,
        batas=int(batas),
    )

    if not data:
        ui.empty_state(
            "🗂️",
            "Log tidak ditemukan",
            "Ubah filter atau lakukan aktivitas terlebih dahulu.",
        )
        return

    df = pd.DataFrame(data)
    tabel = pd.DataFrame(
        {
            "Waktu": df["waktu"].map(waktu_lengkap),
            "Aksi": df["aksi"],
            "Entitas": df["entitas"],
            "Referensi": df["referensi"].fillna("-"),
            "Keterangan": df["keterangan"],
        }
    )
    st.dataframe(
        tabel,
        hide_index=True,
        width="stretch",
        height=min(580, 42 + len(tabel) * 35),
        column_config={
            "Keterangan": st.column_config.TextColumn(width="large"),
            "Waktu": st.column_config.TextColumn(width="medium"),
        },
    )
    st.download_button(
        "⬇️ Unduh log (.csv)",
        data=tabel.to_csv(index=False).encode("utf-8-sig"),
        file_name="log-aktivitas-berkelana.csv",
        mime="text/csv",
        key="unduh_log_csv",
    )
    st.caption(
        "Log dibuat otomatis setiap kali data pelanggan, rute, kursi, atau pemesanan "
        "ditambah, diubah, dihapus, atau dibatalkan."
    )
