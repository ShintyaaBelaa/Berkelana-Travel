"""Halaman dashboard ringkasan."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import components as ui
import database as db
from utils import tanggal_indo


def render() -> None:
    ui.hero(
        "Operasional travel dalam satu layar",
        "Pantau pelanggan, rute, pemesanan, keterisian kursi, dan pendapatan "
        "Berkelana Travel. Semua data tersimpan lokal di SQLite.",
        tanggal_indo(date.today()),
    )

    ringkasan = db.ringkasan_dashboard()

    kolom = st.columns(3)
    with kolom[0]:
        ui.metrik(
            "Pelanggan terdaftar",
            f"{ringkasan['total_pelanggan']:,}".replace(",", "."),
            "👥",
            "Data pelanggan unik (nama + telepon)",
        )
    with kolom[1]:
        ui.metrik(
            "Rute aktif",
            f"{ringkasan['rute_aktif']:,}".replace(",", "."),
            "🗺️",
            f"Dari total {ringkasan['total_rute']} rute terdaftar",
        )
    with kolom[2]:
        ui.metrik(
            "Pemesanan aktif",
            f"{ringkasan['total_pemesanan']:,}".replace(",", "."),
            "🎫",
            f"{ringkasan['total_tiket']} tiket terjual",
        )

    kolom2 = st.columns(3)
    with kolom2[0]:
        ui.metrik(
            "Total pendapatan",
            f"Rp{ringkasan['total_pendapatan']:,}".replace(",", "."),
            "💰",
            f"Rata-rata Rp{ringkasan['rata_rata_transaksi']:,} per transaksi".replace(
                ",", "."
            ),
            aksen=True,
        )
    with kolom2[1]:
        ui.metrik(
            "7 hari ke depan",
            f"{ringkasan['pemesanan_7_hari']:,}".replace(",", "."),
            "📅",
            f"{ringkasan['tiket_7_hari']} tiket · "
            f"{ringkasan['jadwal_mendatang']} jadwal aktif",
        )
    with kolom2[2]:
        ui.metrik(
            "Kursi siap dijual",
            f"{ringkasan['kursi_aktif']:,}".replace(",", "."),
            "💺",
            f"Dari total {ringkasan['total_kursi']} kursi",
        )

    ui.judul_bagian("Keberangkatan terdekat", "6 jadwal berikutnya")
    kiri, kanan = st.columns([1.16, 1])

    with kiri:
        jadwal = db.keberangkatan_mendatang(6)
        if not jadwal:
            ui.empty_state(
                "🗓️",
                "Belum ada jadwal mendatang",
                "Buat pemesanan baru agar jadwal keberangkatan muncul di sini.",
            )
        else:
            for item in jadwal:
                ui.kartu_jadwal(item, ringkasan["kursi_aktif"])

    with kanan:
        ui.judul_bagian("Rute terpopuler", "Berdasarkan tiket terjual")
        populer = db.rute_terpopuler(5)
        if not populer:
            ui.empty_state("📈", "Belum ada data rute", "Rute populer muncul setelah ada pemesanan.")
        else:
            df_populer = pd.DataFrame(populer).set_index("rute")[["jumlah_tiket"]]
            df_populer.columns = ["Tiket terjual"]
            st.bar_chart(df_populer, color="#0f766e", height=212)
            for item in populer[:3]:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;gap:1rem;"
                    f"font-size:.8rem;padding:.24rem 0;border-bottom:1px solid #eef2f4'>"
                    f"<span>{ui.esc(item['rute'])}</span>"
                    f"<b style='color:#0f766e'>{item['jumlah_tiket']} tiket</b></div>",
                    unsafe_allow_html=True,
                )

    ui.judul_bagian("Pemesanan terbaru", "Diurutkan dari transaksi yang paling baru dibuat")
    terbaru = db.pemesanan_terbaru(7)
    if not terbaru:
        ui.empty_state("🎟️", "Belum ada pemesanan", "Mulai dari menu Pemesanan Tiket.")
    else:
        df = pd.DataFrame(terbaru)
        tampil = pd.DataFrame(
            {
                "Kode": df["kode_pemesanan"],
                "Pelanggan": df["nama_pelanggan"],
                "Rute": df["kota_asal"] + " → " + df["kota_tujuan"],
                "Kode jadwal": df["kode_jadwal"].fillna("-"),
                "Keberangkatan": df["tanggal_keberangkatan"].map(tanggal_indo),
                "Jam": df["jam_keberangkatan"],
                "Kursi": df["nomor_kursi"],
                "Tiket": df["jumlah_pesan_tiket"],
                "Total": df["total_harga"].map(lambda x: f"Rp{int(x):,}".replace(",", ".")),
            }
        )
        st.dataframe(tampil, hide_index=True, width="stretch", height=302)

    bawah_kiri, bawah_kanan = st.columns([1, 1])
    with bawah_kiri:
        ui.judul_bagian("Jadwal paling padat", "Okupansi kursi aktif")
        padat = db.jadwal_padat(5)
        if not padat:
            st.caption("Belum ada jadwal mendatang.")
        else:
            for item in padat:
                label = (
                    f"{item.get('kode_jadwal') or item['kode_rute']} · "
                    f"{item['kota_asal']} → {item['kota_tujuan']} · "
                    f"{item['tanggal_keberangkatan']} {item['jam_keberangkatan']}"
                )
                st.progress(
                    min(int(item["persentase"]), 100) / 100,
                    text=f"{label} — {item['persentase']}% ({item['tiket']}/{item['kapasitas']} kursi)",
                )

    with bawah_kanan:
        ui.judul_bagian("Pendapatan per tanggal", "10 tanggal terakhir yang memiliki transaksi")
        pendapatan = db.pendapatan_per_tanggal(10)
        if not pendapatan:
            st.caption("Belum ada data pendapatan.")
        else:
            df_pendapatan = pd.DataFrame(pendapatan)
            df_pendapatan["tanggal"] = df_pendapatan["tanggal_keberangkatan"].map(
                lambda x: tanggal_indo(x).split(", ")[1]
            )
            df_pendapatan = df_pendapatan.set_index("tanggal")[["pendapatan"]]
            df_pendapatan.columns = ["Pendapatan (Rp)"]
            st.area_chart(df_pendapatan, color="#0d9488", height=235)

    st.markdown(
        """
        <div class="bk-note" style="margin-top:1.2rem">
            <b>Catatan operasional:</b> harga pada transaksi dikunci saat pemesanan dibuat,
            sehingga perubahan tarif rute tidak mengubah nota lama. Kursi yang sudah dipesan
            pada rute, tanggal, dan jam yang sama otomatis tidak dapat dipilih kembali.
        </div>
        """,
        unsafe_allow_html=True,
    )
