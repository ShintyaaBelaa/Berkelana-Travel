"""Halaman dashboard ringkasan administrasi."""

from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import services
from ui import components as c


def _chart_gaya(chart: alt.Chart, tinggi: int = 260) -> alt.Chart:
    return (
        chart.properties(height=tinggi)
        .configure_view(strokeWidth=0)
        .configure_axis(
            gridColor="#eef3f9",
            domainColor="#dde7f2",
            tickColor="#dde7f2",
            labelColor="#5d7189",
            titleColor="#5d7189",
            labelFontSize=11,
        )
    )


def _chart_rute(data: list[dict]) -> None:
    if not data or not any(row["pendapatan"] for row in data):
        c.empty_state(
            "Belum ada pendapatan",
            "Pendapatan per rute akan tampil setelah ada pemesanan.",
            "📈",
        )
        return

    frame = pd.DataFrame(data)
    frame = frame[frame["pendapatan"] > 0].copy()
    frame["rute"] = frame["kota_asal"] + " → " + frame["kota_tujuan"]
    frame["pendapatan_rp"] = frame["pendapatan"].map(services.format_rupiah)

    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadius=5, color="#1f6fb8", size=18)
        .encode(
            y=alt.Y("rute:N", sort="-x", title=None),
            x=alt.X(
                "pendapatan:Q",
                title=None,
                axis=alt.Axis(format="~s", tickCount=4),
            ),
            tooltip=[
                alt.Tooltip("rute:N", title="Rute"),
                alt.Tooltip("jumlah_pemesanan:Q", title="Pemesanan"),
                alt.Tooltip("jumlah_tiket:Q", title="Tiket"),
                alt.Tooltip("pendapatan_rp:N", title="Pendapatan"),
            ],
        )
    )
    st.altair_chart(_chart_gaya(chart, 250), width="stretch")


def _chart_tanggal(data: list[dict]) -> None:
    if not data:
        c.empty_state(
            "Belum ada jadwal mendatang",
            "Grafik pemesanan per tanggal akan tampil di sini.",
            "🗓️",
        )
        return

    frame = pd.DataFrame(data)
    frame["label"] = frame["tanggal_keberangkatan"].map(services.format_tanggal_singkat)
    frame["pendapatan_rp"] = frame["pendapatan"].map(services.format_rupiah)

    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadius=4, color="#f2b544", size=24)
        .encode(
            x=alt.X("label:N", title=None, sort=None, axis=alt.Axis(labelAngle=-30)),
            y=alt.Y("jumlah_tiket:Q", title="Tiket", axis=alt.Axis(tickMinStep=1)),
            tooltip=[
                alt.Tooltip("label:N", title="Tanggal"),
                alt.Tooltip("jumlah_pemesanan:Q", title="Pemesanan"),
                alt.Tooltip("jumlah_tiket:Q", title="Tiket"),
                alt.Tooltip("pendapatan_rp:N", title="Pendapatan"),
            ],
        )
    )
    st.altair_chart(_chart_gaya(chart, 230), width="stretch")


def render() -> None:
    c.hero(
        "PUSAT ADMINISTRASI",
        "Selamat datang di Berkelana Travel",
        "Pantau pelanggan, rute, ketersediaan kursi, dan transaksi pemesanan "
        "dalam satu tempat. Data tersimpan otomatis di database SQLite lokal.",
        chips=[
            services.format_tanggal_indo(date.today()),
            "Tanpa login · akses petugas loket",
            "SQLite lokal",
        ],
    )

    # Aksi cepat
    kol1, kol2, kol3, _kol4 = st.columns([1.2, 1.2, 1.2, 2.4])
    with kol1:
        if st.button("🎫  Buat Pemesanan", type="primary", width="stretch"):
            c.go_to("Pemesanan Tiket")
    with kol2:
        if st.button("👥  Tambah Pelanggan", width="stretch"):
            c.go_to("Data Pelanggan")
    with kol3:
        if st.button("🧾  Riwayat", width="stretch"):
            c.go_to("Riwayat Pemesanan")

    ringkasan = services.ringkasan_dashboard()

    c.section_title("Ringkasan usaha", "Angka dihitung langsung dari database saat halaman dimuat.")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        c.metric_card(
            "Pelanggan",
            f"{ringkasan['pelanggan']:,}".replace(",", "."),
            f"+{ringkasan['pelanggan_baru_bulan_ini']} bulan ini",
            "👥",
            "teal",
        )
    with m2:
        c.metric_card(
            "Rute Aktif",
            f"{ringkasan['rute_aktif']}",
            f"{ringkasan['rute_nonaktif']} rute nonaktif",
            "🛣️",
            "navy",
        )
    with m3:
        c.metric_card(
            "Pemesanan",
            f"{ringkasan['pemesanan']:,}".replace(",", "."),
            f"{ringkasan['pemesanan_bulan_ini']} bulan ini",
            "🧾",
            "amber",
        )
    with m4:
        c.metric_card(
            "Tiket Terjual",
            f"{ringkasan['tiket']:,}".replace(",", "."),
            f"{ringkasan['tiket_bulan_ini']} tiket bulan ini",
            "🎟️",
            "teal",
        )
    with m5:
        c.metric_card(
            "Pendapatan",
            services.format_rupiah(ringkasan["pendapatan"]),
            f"{services.format_rupiah(ringkasan['pendapatan_bulan_ini'])} bulan ini",
            "💰",
            "rose",
        )

    kiri, kanan = st.columns([1.55, 1])
    with kiri:
        c.section_title("Pendapatan per rute", "Rute dengan kontribusi pendapatan terbesar.")
        _chart_rute(services.pendapatan_per_rute(8))
    with kanan:
        c.section_title("Pelanggan teratas", "Berdasarkan total nilai pemesanan.")
        teratas = services.pelanggan_teratas(5)
        if not teratas:
            c.empty_state("Belum ada pelanggan", "Data pelanggan akan tampil di sini.", "👤")
        else:
            for urutan, orang in enumerate(teratas, start=1):
                st.markdown(
                    f"""
                    <div class="summary-line">
                        <span><b style="color:#102a43">{urutan}. {c.esc(orang['nama_pelanggan'])}</b><br>
                        {c.esc(orang['kode_pelanggan'])} · {orang['jumlah_tiket']} tiket</span>
                        <b>{services.format_rupiah(orang['total_belanja'])}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    c.section_title(
        "Pemesanan per tanggal keberangkatan",
        "Jumlah tiket pada jadwal mendatang. Hanya tanggal mulai hari ini yang dihitung.",
    )
    _chart_tanggal(services.pemesanan_per_tanggal(14))

    c.section_title("Keberangkatan terdekat", "Tingkat keterisian dihitung dari kursi aktif.")
    jadwal = services.ringkasan_jadwal_terdekat(8)
    if not jadwal:
        c.empty_state(
            "Belum ada keberangkatan mendatang",
            "Buat pemesanan baru atau pilih jadwal setelah waktu sekarang.",
            "🚌",
        )
    else:
        frame = pd.DataFrame(
            [
                {
                    "Rute": f"{row['kota_asal']} → {row['kota_tujuan']}",
                    "Kode": row["kode_rute"],
                    "Keberangkatan": f"{services.format_tanggal_singkat(row['tanggal_keberangkatan'])} · {services.format_jam(row['jam_keberangkatan'])}",
                    "Pemesanan": row["jumlah_pemesanan"],
                    "Tiket": row["jumlah_tiket"],
                    "Okupansi (%)": row["okupansi"],
                    "Pendapatan": services.format_rupiah(row["pendapatan"]),
                }
                for row in jadwal
            ]
        )
        st.dataframe(
            frame,
            width="stretch",
            hide_index=True,
            column_config={
                "Okupansi (%)": st.column_config.ProgressColumn(
                    "Okupansi", min_value=0, max_value=100, format="%d%%"
                ),
                "Pemesanan": st.column_config.NumberColumn(width="small"),
                "Tiket": st.column_config.NumberColumn(width="small"),
            },
        )

    kiri2, kanan2 = st.columns([1.55, 1])
    with kiri2:
        c.section_title("Pemesanan terbaru", "Enam transaksi terakhir yang tersimpan.")
        terbaru = services.pemesanan_terbaru(6)
        if not terbaru:
            c.empty_state("Belum ada transaksi", "Transaksi baru akan muncul di sini.", "🧾")
        else:
            frame = pd.DataFrame(
                [
                    {
                        "Kode": row["kode_pemesanan"],
                        "Pelanggan": row["nama_pelanggan"],
                        "Rute": f"{row['kota_asal']} → {row['kota_tujuan']}",
                        "Kursi": row["daftar_kursi"],
                        "Total": services.format_rupiah(row["total_harga"]),
                    }
                    for row in terbaru
                ]
            )
            st.dataframe(frame, width="stretch", hide_index=True)
    with kanan2:
        c.section_title("Catatan operasional", "Hal yang perlu diperhatikan petugas.")
        if ringkasan["rute_nonaktif"]:
            st.warning(
                f"{ringkasan['rute_nonaktif']} rute sedang nonaktif dan tidak dapat dipilih "
                "pada pemesanan baru. Aktifkan kembali melalui menu Data Rute & Tarif."
            )
        st.info(
            f"Terdapat **{ringkasan['jadwal_mendatang']} jadwal mendatang** yang sudah memiliki "
            f"pemesanan, dengan total **{ringkasan['kursi_aktif']} kursi aktif** yang dapat dijual."
        )
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">Prinsip data</div>
                <div class="panel-note">
                    Harga tiket disimpan per transaksi, sehingga perubahan tarif rute
                    tidak mengubah nota lama. Kursi juga diperiksa ulang saat transaksi
                    disimpan agar tidak terjadi pemesanan ganda.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
