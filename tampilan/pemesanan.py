"""Halaman pembuatan pemesanan tiket."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

import components as ui
import database as db
from utils import (
    jam_indo,
    jadwal_sudah_lewat,
    label_sisa_waktu,
    rupiah,
    tanggal_indo,
)


def _urut_kursi(nomor: str) -> tuple[int, str]:
    angka = "".join(ch for ch in nomor if ch.isdigit())
    return (int(angka) if angka else 9999, nomor.upper())


def _tampilkan_nota_terakhir() -> None:
    nota = st.session_state.get("nota_terakhir")
    if not nota:
        return
    kiri, kanan = st.columns([5, 1])
    with kiri:
        st.success(
            f"Pemesanan {nota['kode_pemesanan']} berhasil disimpan. "
            "Nota dapat diunduh di bawah ini."
        )
    with kanan:
        if st.button("Tutup nota", key="tutup_nota_terakhir", width="stretch"):
            st.session_state.pop("nota_terakhir", None)
            st.rerun()
    ui.nota(nota, "nota_pemesanan_terakhir")
    st.divider()


def render() -> None:
    ui.page_header(
        "🎫",
        "Pemesanan Tiket",
        "Pilih pelanggan, rute, jadwal, dan kursi. Sistem menghitung total secara otomatis.",
    )
    _tampilkan_nota_terakhir()

    # ------------------------------------------------------------------
    # Pelanggan
    # ------------------------------------------------------------------
    ui.judul_bagian("1 · Pelanggan", "Pilih pelanggan terdaftar atau tambahkan baru")
    with st.expander("➕ Pelanggan baru belum terdaftar?"):
        with st.form("form_pelanggan_cepat", clear_on_submit=True):
            kiri, kanan = st.columns(2)
            nama_baru = kiri.text_input(
                "Nama pelanggan *",
                placeholder="Contoh: Andi Pratama",
                key="cepat_nama",
            )
            telepon_baru = kanan.text_input(
                "Nomor telepon *",
                placeholder="Contoh: 081234567890",
                key="cepat_telepon",
            )
            tambah = st.form_submit_button("Tambah & pilih pelanggan", type="primary")
        if tambah:
            try:
                baru = db.tambah_pelanggan(nama_baru, telepon_baru)
            except db.KesalahanBisnis as exc:
                st.error(str(exc))
            else:
                st.session_state["pilih_pelanggan_pemesanan"] = baru["id_pelanggan"]
                ui.set_flash(
                    "success",
                    f"Pelanggan {baru['kode_pelanggan']} — {baru['nama_pelanggan']} "
                    "berhasil ditambahkan dan otomatis dipilih.",
                )
                st.rerun()

    pelanggan_list = db.daftar_pelanggan()
    if not pelanggan_list:
        st.warning(
            "Belum ada pelanggan. Tambahkan pelanggan terlebih dahulu melalui panel di atas."
        )
        return

    peta_pelanggan = {p["id_pelanggan"]: p for p in pelanggan_list}
    id_pelanggan = st.selectbox(
        "Pelanggan *",
        options=list(peta_pelanggan),
        index=None,
        placeholder="Ketik untuk mencari nama, kode, atau nomor telepon...",
        format_func=lambda pid: (
            f"{peta_pelanggan[pid]['kode_pelanggan']} · "
            f"{peta_pelanggan[pid]['nama_pelanggan']} · "
            f"{peta_pelanggan[pid]['nomor_telepon']}"
        ),
        key="pilih_pelanggan_pemesanan",
    )
    if id_pelanggan:
        p = peta_pelanggan[id_pelanggan]
        st.caption(
            f"📱 {p['nomor_telepon']} · {p['jumlah_pemesanan']} pemesanan sebelumnya · "
            f"total belanja {rupiah(p['total_belanja'])}"
        )
    else:
        st.caption("Pelanggan wajib dipilih sebelum pemesanan dapat disimpan.")

    # ------------------------------------------------------------------
    # Rute dan jadwal
    # ------------------------------------------------------------------
    ui.judul_bagian(
        "2 · Rute & Jadwal",
        "Pilih rute, tanggal, lalu kode jadwal keberangkatan",
    )
    rute_list = db.daftar_rute(hanya_aktif=True)
    if not rute_list:
        st.warning(
            "Belum ada rute aktif. Aktifkan atau tambahkan rute terlebih dahulu pada menu Rute & Tarif."
        )
        return

    peta_rute = {r["id_rute"]: r for r in rute_list}
    kolom = st.columns([1.5, 1, 1])
    id_rute = kolom[0].selectbox(
        "Rute *",
        options=list(peta_rute),
        index=None,
        placeholder="Pilih rute keberangkatan...",
        format_func=lambda rid: (
            f"{peta_rute[rid]['kota_asal']} → {peta_rute[rid]['kota_tujuan']} · "
            f"{rupiah(peta_rute[rid]['harga_tiket'])}"
        ),
        key="pilih_rute_pemesanan",
    )

    jadwal_list = db.daftar_jadwal(id_rute=id_rute, hanya_aktif=True) if id_rute else []
    peta_jadwal = {j["id_jadwal"]: j for j in jadwal_list}
    id_jadwal = None
    jam = None

    def _waktu(jam_teks: str) -> datetime:
        return datetime.strptime(jam_teks, "%H:%M")

    sekarang = datetime.now()
    tanggal_awal = sekarang.date()
    if jadwal_list and not any(
        datetime.combine(tanggal_awal, _waktu(j["jam_keberangkatan"]).time()) > sekarang
        for j in jadwal_list
    ):
        tanggal_awal = tanggal_awal + timedelta(days=1)

    tanggal = kolom[1].date_input(
        "Tanggal *",
        value=tanggal_awal,
        min_value=date.today(),
        format="DD/MM/YYYY",
        key="tanggal_pemesanan",
    )

    if not id_rute:
        kolom[2].selectbox(
            "Kode jadwal *",
            options=[],
            placeholder="Pilih rute dulu",
            disabled=True,
            key="jadwal_pemesanan_kosong",
        )
    elif not jadwal_list:
        kolom[2].warning("Rute ini belum memiliki jadwal aktif.")
    else:
        opsi_jadwal = [
            j
            for j in jadwal_list
            if datetime.combine(tanggal, _waktu(j["jam_keberangkatan"]).time())
            > sekarang
        ]
        if not opsi_jadwal:
            opsi_jadwal = jadwal_list
        id_jadwal = kolom[2].selectbox(
            "Kode jadwal *",
            options=[j["id_jadwal"] for j in opsi_jadwal],
            index=0,
            format_func=lambda jid: (
                f"{peta_jadwal[jid]['kode_jadwal']} · "
                f"{peta_jadwal[jid]['jam_keberangkatan']} WIB"
            ),
            key=f"jadwal_pemesanan_{id_rute}_{tanggal.isoformat()}",
        )
        if id_jadwal:
            jam = peta_jadwal[id_jadwal]["jam_keberangkatan"]

    rute = peta_rute.get(id_rute) if id_rute else None
    jadwal_terpilih = peta_jadwal.get(id_jadwal) if id_jadwal else None
    if rute and jadwal_terpilih:
        jadwal_lewat = jadwal_sudah_lewat(tanggal, jam)
        info1, info2, info3 = st.columns(3)
        with info1:
            st.metric("Rute", f"{rute['kota_asal']} → {rute['kota_tujuan']}")
        with info2:
            st.metric(
                "Kode jadwal",
                f"{jadwal_terpilih['kode_jadwal']} · {jam_indo(jam)}",
                help=(
                    f"Keberangkatan ke-{jadwal_terpilih['urut_keberangkatan']} · "
                    f"{label_sisa_waktu(tanggal, jam)}"
                ),
            )
        with info3:
            st.metric("Harga per tiket", rupiah(rute["harga_tiket"]))
        st.caption(
            f"Jadwal: {tanggal_indo(tanggal)} pukul {jam_indo(jam)} · "
            f"kode bisnis {jadwal_terpilih['kode_jadwal']}"
        )
        if jadwal_lewat:
            st.error(
                "Jadwal ini sudah terlewati. Pilih tanggal atau kode jadwal yang "
                "akan datang (aturan B06)."
            )
    elif rute and not jadwal_list:
        st.warning(
            "Rute ini belum memiliki jadwal aktif. Lengkapi jadwal pada menu Rute & Tarif."
        )

    # ------------------------------------------------------------------
    # Kursi
    # ------------------------------------------------------------------
    ui.judul_bagian("3 · Pilih Kursi", "Kursi abu-abu sudah dipesan pada jadwal tersebut")
    terpakai_list: list[dict] = []
    tersedia: list[dict] = []
    semua_kursi = db.daftar_kursi()

    if id_rute and jam:
        terpakai_list = db.kursi_terpakai(id_rute, tanggal, jam)
        id_terpakai = {k["id_kursi"] for k in terpakai_list}
        tersedia = [
            k
            for k in semua_kursi
            if k["status_aktif"] and k["id_kursi"] not in id_terpakai
        ]
        kapasitas = len([k for k in semua_kursi if k["status_aktif"]])
        terpakai_map = {k["id_kursi"]: k["nomor_kursi"] for k in terpakai_list}
        ui.denah_kursi(semua_kursi, terpakai=terpakai_map, label_depan="Depan kendaraan")

        kiri, kanan = st.columns([2, 1])
        with kiri:
            if tersedia:
                opsi = [k["id_kursi"] for k in tersedia]
                peta_nomor = {k["id_kursi"]: k["nomor_kursi"] for k in tersedia}
                kunci_kursi = (
                    f"kursi_pemesanan_{id_rute}_{tanggal.isoformat()}_{id_jadwal}"
                )
                id_kursi = st.multiselect(
                    "Kursi yang dipilih *",
                    options=opsi,
                    format_func=lambda kid: peta_nomor[kid],
                    placeholder="Pilih satu atau beberapa kursi tersedia...",
                    key=kunci_kursi,
                    help="Minimal satu kursi. Kursi yang sama tidak dapat dipilih dua kali.",
                )
            else:
                id_kursi = []
                st.error(
                    "Semua kursi aktif pada jadwal ini sudah dipesan. Pilih jadwal lain."
                )
        with kanan:
            st.markdown(
                f"""
                <div class="bk-price-box">
                    <div class="row"><span>Kapasitas aktif</span><span>{kapasitas} kursi</span></div>
                    <div class="row"><span>Sudah dipesan</span><span>{len(terpakai_list)} kursi</span></div>
                    <div class="row total"><span>Tersedia</span><b>{len(tersedia)}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        id_kursi = []
        ui.denah_kursi(semua_kursi, label_depan="Pilih rute dan jadwal untuk melihat ketersediaan")
        st.caption(
            "Pilih rute, tanggal, dan kode jadwal untuk memeriksa kursi yang tersedia."
        )

    # ------------------------------------------------------------------
    # Ringkasan & simpan
    # ------------------------------------------------------------------
    ui.judul_bagian("4 · Ringkasan & Konfirmasi", "Periksa kembali sebelum menyimpan")
    rute_terpilih = peta_rute.get(id_rute) if id_rute else None
    nomor_terpilih: list[str] = []
    if id_kursi:
        peta_semua_nomor = {k["id_kursi"]: k["nomor_kursi"] for k in semua_kursi}
        nomor_terpilih = sorted(
            (peta_semua_nomor[kid] for kid in id_kursi), key=_urut_kursi
        )

    jumlah = len(nomor_terpilih)
    harga = int(rute_terpilih["harga_tiket"]) if rute_terpilih else 0
    total = harga * jumlah
    kiri, kanan = st.columns([1, 1])
    with kiri:
        if rute_terpilih:
            ui.kotak_harga(harga, jumlah, total, ", ".join(nomor_terpilih))
            if id_pelanggan:
                p = peta_pelanggan[id_pelanggan]
                jadwal_teks = (
                    f"{jadwal_terpilih['kode_jadwal']} · {jam_indo(jam)}"
                    if jadwal_terpilih and jam
                    else "jadwal belum dipilih"
                )
                st.caption(
                    f"Pelanggan: **{p['nama_pelanggan']}** ({p['kode_pelanggan']}) · "
                    f"{tanggal_indo(tanggal)} · {jadwal_teks}"
                )
        else:
            st.caption("Ringkasan harga muncul setelah rute dan jadwal dipilih.")
    with kanan:
        st.markdown(
            """
            <div class="bk-note">
                <b>Yang dikunci saat pemesanan:</b> harga tiket, rute, tanggal, jam, dan
                kursi. Perubahan tarif setelahnya tidak mengubah total transaksi ini
                (aturan B09). Kursi yang sudah tersimpan tidak dapat dipesan pada jadwal
                yang sama (aturan B08).
            </div>
            """,
            unsafe_allow_html=True,
        )
        alasan = []
        if not id_pelanggan:
            alasan.append("pelanggan belum dipilih")
        if not id_rute:
            alasan.append("rute belum dipilih")
        if id_rute and not jadwal_terpilih:
            alasan.append("jadwal belum dipilih")
        if rute_terpilih and jadwal_terpilih and jam and jadwal_sudah_lewat(tanggal, jam):
            alasan.append("jadwal sudah lewat")
        if id_rute and jadwal_terpilih and not nomor_terpilih:
            alasan.append("kursi belum dipilih")

        tombol = st.button(
            "✅ Konfirmasi & simpan pemesanan",
            type="primary",
            disabled=bool(alasan),
            width="stretch",
            key="simpan_pemesanan",
        )
        if alasan:
            st.caption("Lengkapi dulu: " + ", ".join(alasan) + ".")
        if tombol:
            try:
                detail = db.buat_pemesanan(
                    id_pelanggan=id_pelanggan,
                    id_rute=id_rute,
                    tanggal=tanggal,
                    jam=jam,
                    id_kursi=id_kursi,
                )
            except db.KesalahanBisnis as exc:
                st.error(str(exc))
            except sqlite3.IntegrityError:
                st.error(
                    "Kursi yang dipilih baru saja dipesan oleh transaksi lain. "
                    "Muat ulang halaman dan pilih kursi lain."
                )
            else:
                st.session_state["nota_terakhir"] = detail
                ui.set_flash(
                    "success",
                    f"Pemesanan {detail['kode_pemesanan']} berhasil dibuat untuk "
                    f"{detail['nama_pelanggan']}.",
                )
                st.rerun()
