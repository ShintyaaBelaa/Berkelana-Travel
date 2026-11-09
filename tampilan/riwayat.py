"""Halaman riwayat, detail, nota, dan pembatalan pemesanan."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import components as ui
import database as db
from utils import (
    jadwal_sudah_lewat,
    jam_indo,
    rupiah,
    tanggal_indo,
    tanggal_singkat,
    waktu_lengkap,
)


def render() -> None:
    ui.page_header(
        "🕘",
        "Riwayat Pemesanan",
        "Cari transaksi, buka detail dan nota, lalu batalkan bila diperlukan.",
    )

    rute_list = db.daftar_rute()
    peta_rute = {r["id_rute"]: r for r in rute_list}

    with st.container(border=True):
        baris1 = st.columns([1.7, 1, 1])
        cari = baris1[0].text_input(
            "🔍 Cari transaksi",
            placeholder="Kode pemesanan, pelanggan, telepon, rute, atau kursi...",
            key="cari_riwayat",
        )
        id_rute = baris1[1].selectbox(
            "Rute",
            options=[None, *peta_rute],
            format_func=lambda rid: (
                "Semua rute"
                if rid is None
                else f"{peta_rute[rid]['kode_rute']} · "
                f"{peta_rute[rid]['kota_asal']} → {peta_rute[rid]['kota_tujuan']}"
            ),
            key="filter_rute_riwayat",
        )
        pakai_tanggal = baris1[2].checkbox(
            "Filter tanggal keberangkatan",
            value=False,
            key="pakai_filter_tanggal_riwayat",
        )
        tanggal_dari = tanggal_sampai = None
        if pakai_tanggal:
            rentang = st.date_input(
                "Rentang tanggal keberangkatan",
                value=(
                    date.today() - timedelta(days=30),
                    date.today() + timedelta(days=90),
                ),
                format="DD/MM/YYYY",
                key="rentang_riwayat",
            )
            if isinstance(rentang, (tuple, list)) and len(rentang) == 2:
                tanggal_dari, tanggal_sampai = rentang

    data = db.daftar_pemesanan(
        cari=cari,
        id_rute=id_rute,
        tanggal_dari=tanggal_dari,
        tanggal_sampai=tanggal_sampai,
    )

    total_tiket = sum(int(d["jumlah_pesan_tiket"]) for d in data)
    total_pendapatan = sum(int(d["total_harga"]) for d in data)
    mendatang = sum(
        1
        for d in data
        if not jadwal_sudah_lewat(d["tanggal_keberangkatan"], d["jam_keberangkatan"])
    )

    kolom = st.columns(4)
    with kolom[0]:
        ui.metrik("Transaksi", f"{len(data)}", "🎫", "Sesuai filter aktif")
    with kolom[1]:
        ui.metrik("Tiket", f"{total_tiket}", "🎟️", "Total tiket pada hasil filter")
    with kolom[2]:
        ui.metrik("Nilai transaksi", rupiah(total_pendapatan), "💰", "Akumulasi total harga")
    with kolom[3]:
        ui.metrik("Masih mendatang", f"{mendatang}", "📅", "Jadwal yang belum terlewati")

    if not data:
        ui.empty_state(
            "🔎",
            "Tidak ada pemesanan",
            "Ubah filter pencarian atau buat pemesanan baru terlebih dahulu.",
        )
        return

    df = pd.DataFrame(data)
    tabel = pd.DataFrame(
        {
            "Kode": df["kode_pemesanan"],
            "Pelanggan": df["nama_pelanggan"],
            "Telepon": df["nomor_telepon"],
            "Rute": df["kota_asal"] + " → " + df["kota_tujuan"],
            "Kode jadwal": df["kode_jadwal"].fillna("-"),
            "Tanggal": df["tanggal_keberangkatan"].map(tanggal_singkat),
            "Jam": df["jam_keberangkatan"],
            "Kursi": df["nomor_kursi"],
            "Tiket": df["jumlah_pesan_tiket"],
            "Total": df["total_harga"].map(rupiah),
            "Dibuat": df["dibuat_pada"].map(waktu_lengkap),
        }
    )
    st.dataframe(
        tabel,
        hide_index=True,
        width="stretch",
        height=min(430, 42 + len(tabel) * 35),
    )
    st.download_button(
        "⬇️ Unduh hasil filter (.csv)",
        data=tabel.to_csv(index=False).encode("utf-8-sig"),
        file_name="riwayat-pemesanan-berkelana.csv",
        mime="text/csv",
        key="unduh_riwayat_csv",
    )

    st.divider()
    ui.judul_bagian("Detail transaksi", "Pilih kode pemesanan")
    pilihan = st.selectbox(
        "Pemesanan",
        options=[d["id_pemesanan"] for d in data],
        format_func=lambda pid: next(
            f"{d['kode_pemesanan']} · {d['nama_pelanggan']} · "
            f"{d.get('kode_jadwal') or d['kode_rute']} · "
            f"{d['kota_asal']} → {d['kota_tujuan']} · "
            f"{tanggal_singkat(d['tanggal_keberangkatan'])} {d['jam_keberangkatan']}"
            for d in data
            if d["id_pemesanan"] == pid
        ),
        key="pilih_pemesanan_riwayat",
    )
    detail = db.ambil_pemesanan(pilihan)

    ui.kartu_perjalanan(detail)

    kiri, kanan = st.columns([1, 1])
    with kiri:
        st.markdown("##### 👤 Data pelanggan")
        st.markdown(
            f"""
            <div class="bk-profile" style="margin-bottom:.8rem">
                <div>{ui.badge(detail['kode_pelanggan'], 'teal')}</div>
                <div class="bk-profile-name">{ui.esc(detail['nama_pelanggan'])}</div>
                <div class="bk-profile-sub">📱 {ui.esc(detail['nomor_telepon'])}</div>
                <div class="bk-profile-stats">
                    <div class="bk-profile-stat"><span>Transaksi</span><b>{ui.esc(detail['kode_pemesanan'])}</b></div>
                    <div class="bk-profile-stat"><span>Dibuat</span><b style="font-size:.76rem">{ui.esc(waktu_lengkap(detail['dibuat_pada']))}</b></div>
                    <div class="bk-profile-stat"><span>Status</span><b>Aktif</b></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Keberangkatan: {tanggal_indo(detail['tanggal_keberangkatan'])} pukul "
            f"{jam_indo(detail['jam_keberangkatan'])}."
        )
        if jadwal_sudah_lewat(detail["tanggal_keberangkatan"], detail["jam_keberangkatan"]):
            st.info("Jadwal keberangkatan transaksi ini sudah terlewati.")

    with kanan:
        st.markdown("##### 💳 Rincian biaya")
        st.markdown(
            f"""
            <div class="bk-price-box">
                <div class="row"><span>Kode jadwal</span><span>{ui.esc(detail.get('kode_jadwal') or '-')}</span></div>
                <div class="row"><span>Kode rute</span><span>{ui.esc(detail['kode_rute'])}</span></div>
                <div class="row"><span>Harga saat pemesanan</span><span>{ui.esc(rupiah(detail['harga_saat_pemesanan']))}</span></div>
                <div class="row"><span>Jumlah tiket</span><span>{detail['jumlah_pesan_tiket']} tiket</span></div>
                <div class="row"><span>Kursi</span><span>{ui.esc(detail['nomor_kursi'])}</span></div>
                <div class="row total"><span>Total harga</span><b>{ui.esc(rupiah(detail['total_harga']))}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if int(detail["harga_tiket_saat_ini"]) != int(detail["harga_saat_pemesanan"]):
            st.warning(
                "Tarif rute saat ini berbeda dengan harga saat pemesanan. "
                "Transaksi tetap memakai harga yang tersimpan pada nota "
                f"({rupiah(detail['harga_saat_pemesanan'])})."
            )
        else:
            st.caption("Harga transaksi sama dengan tarif rute saat ini.")

    with st.expander("🧾 Lihat & unduh nota"):
        ui.nota(detail, f"nota_riwayat_{detail['kode_pemesanan']}")

    with st.expander("⚠️ Batalkan pemesanan"):
        st.markdown(
            "Pembatalan menghapus pemesanan beserta detail kursinya. Kursi akan "
            "tersedia kembali untuk jadwal tersebut. Pengembalian dana dilakukan "
            "di luar sistem."
        )
        kunci_konfirmasi = f"konfirmasi_batal_{detail['id_pemesanan']}"
        if st.button(
            "Batalkan pemesanan ini",
            key=f"tombol_batal_{detail['id_pemesanan']}",
            type="secondary",
        ):
            st.session_state[kunci_konfirmasi] = True

        if st.session_state.get(kunci_konfirmasi):
            st.error(
                f"Pemesanan **{detail['kode_pemesanan']}** atas nama "
                f"**{detail['nama_pelanggan']}** akan dibatalkan permanen. "
                f"Rute {detail['kota_asal']} → {detail['kota_tujuan']}, "
                f"jadwal {detail.get('kode_jadwal') or '-'}, "
                f"{tanggal_indo(detail['tanggal_keberangkatan'])} pukul "
                f"{jam_indo(detail['jam_keberangkatan'])}, kursi "
                f"{detail['nomor_kursi']} ({detail['jumlah_pesan_tiket']} tiket), "
                f"total {rupiah(detail['total_harga'])}."
            )
            kiri, kanan = st.columns(2)
            if kiri.button(
                "Ya, batalkan pemesanan",
                type="primary",
                key=f"ya_batal_{detail['id_pemesanan']}",
            ):
                try:
                    db.batalkan_pemesanan(detail["id_pemesanan"])
                except db.KesalahanBisnis as exc:
                    st.error(str(exc))
                else:
                    nota = st.session_state.get("nota_terakhir")
                    if nota and nota.get("kode_pemesanan") == detail["kode_pemesanan"]:
                        st.session_state.pop("nota_terakhir", None)
                    st.session_state.pop(kunci_konfirmasi, None)
                    ui.set_flash(
                        "success",
                        f"Pemesanan {detail['kode_pemesanan']} berhasil dibatalkan. "
                        f"Kursi {detail['nomor_kursi']} kembali tersedia.",
                    )
                    st.rerun()
            if kanan.button(
                "Tidak, kembali",
                key=f"tidak_batal_{detail['id_pemesanan']}",
            ):
                st.session_state.pop(kunci_konfirmasi, None)
                st.rerun()
