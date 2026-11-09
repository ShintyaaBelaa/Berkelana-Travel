"""Halaman pengelolaan rute dan tarif."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import database as db
from utils import rupiah


def _tabel_rute(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    return pd.DataFrame(
        {
            "Kode": df["kode_rute"],
            "Kota asal": df["kota_asal"],
            "Kota tujuan": df["kota_tujuan"],
            "Tarif": df["harga_tiket"].map(rupiah),
            "Kode jadwal": df["kode_jadwal_semua"],
            "Status": df["aktif"].map(lambda x: "Aktif" if x else "Nonaktif"),
            "Pemesanan": df["jumlah_pemesanan"],
            "Tiket terjual": df["total_tiket_terjual"],
            "Pendapatan": df["total_pendapatan"].map(rupiah),
        }
    )


def _tabel_jadwal(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    return pd.DataFrame(
        {
            "Kode bisnis": df["kode_jadwal"],
            "Keberangkatan": df["urut_keberangkatan"],
            "Jam": df["jam_keberangkatan"].map(lambda x: f"{x} WIB"),
            "Rute": df["kota_asal"] + " → " + df["kota_tujuan"],
            "Kode rute": df["kode_rute"],
            "Status": df.apply(
                lambda r: "Aktif" if r["aktif"] and r["rute_aktif"] else "Nonaktif",
                axis=1,
            ),
        }
    )


def render() -> None:
    ui.page_header(
        "🗺️",
        "Rute & Tarif",
        "Atur perjalanan yang dijual, tarif, status rute, serta tiga kode jadwal "
        "keberangkatan tetap pada setiap rute.",
    )

    semua = db.daftar_rute()
    aktif = [r for r in semua if r["aktif"]]
    semua_jadwal = db.daftar_jadwal()
    rata = int(sum(r["harga_tiket"] for r in aktif) / len(aktif)) if aktif else 0
    pendapatan = sum(r["total_pendapatan"] for r in semua)

    kolom = st.columns(4)
    with kolom[0]:
        ui.metrik(
            "Total rute",
            f"{len(semua)}",
            "🗺️",
            f"{len(aktif)} rute aktif · {len(semua_jadwal)} kode jadwal",
        )
    with kolom[1]:
        ui.metrik("Tarif rata-rata", rupiah(rata), "🎟️", "Dihitung dari rute aktif")
    with kolom[2]:
        ui.metrik(
            "Tiket terjual",
            f"{sum(r['total_tiket_terjual'] for r in semua)}",
            "🎫",
            "Seluruh rute",
        )
    with kolom[3]:
        ui.metrik("Pendapatan rute", rupiah(pendapatan), "💰", "Akumulasi transaksi aktif")

    tab_daftar, tab_jadwal, tab_tambah = st.tabs(
        ["📋 Daftar Rute", "🕘 Jadwal & Kode", "➕ Tambah Rute"]
    )

    with tab_tambah:
        st.markdown(
            """
            <div class="bk-note">
                <b>Aturan B03:</b> kota asal dan tujuan harus berbeda, serta tarif harus
                lebih besar dari nol. Kode rute (contoh <b>SY</b>) dan tiga kode bisnis
                jadwal (contoh <b>SY001</b>, <b>SY002</b>, <b>SY003</b>) dibuat otomatis
                untuk jam 07:00, 12:00, dan 17:00 WIB. Tarif baru hanya berlaku untuk
                pemesanan berikutnya; nota lama tetap memakai harga saat pemesanan.
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("form_tambah_rute", clear_on_submit=True):
            kiri, tengah, kanan = st.columns([1, 1, 1])
            asal = kiri.text_input("Kota asal *", placeholder="Contoh: Semarang")
            tujuan = tengah.text_input("Kota tujuan *", placeholder="Contoh: Solo")
            harga = kanan.number_input(
                "Tarif tiket (Rp) *",
                min_value=1,
                max_value=100_000_000,
                value=75_000,
                step=5_000,
                format="%d",
            )
            status = st.checkbox("Rute langsung aktif dan dapat dipesan", value=True)
            st.caption("* Wajib diisi. Tarif disimpan sebagai bilangan bulat rupiah.")
            simpan = st.form_submit_button("Simpan rute", type="primary")
        if simpan:
            try:
                baru = db.tambah_rute(asal, tujuan, int(harga), status)
            except db.KesalahanBisnis as exc:
                st.error(str(exc))
            else:
                ui.set_flash(
                    "success",
                    f"Rute {baru['kode_rute']} — {baru['kota_asal']} → "
                    f"{baru['kota_tujuan']} berhasil ditambahkan.",
                )
                st.rerun()

    with tab_jadwal:
        st.markdown(
            """
            <div class="bk-note">
                Setiap rute memiliki <b>tiga jadwal tetap</b> pada pukul 07:00, 12:00,
                dan 17:00 WIB. Kode bisnis memakai prefix rute ditambah nomor
                keberangkatan tiga digit, sehingga <b>SY001</b> berarti rute SY
                keberangkatan ke-1. Kode ini dipakai pada pemesanan, riwayat, dan nota.
            </div>
            """,
            unsafe_allow_html=True,
        )
        filter_jadwal = st.selectbox(
            "Tampilkan jadwal untuk rute",
            options=[None] + [r["id_rute"] for r in semua],
            format_func=lambda rid: "Semua rute"
            if rid is None
            else next(
                f"{r['kode_rute']} · {r['kota_asal']} → {r['kota_tujuan']}"
                for r in semua
                if r["id_rute"] == rid
            ),
            key="filter_jadwal_rute",
        )
        data_jadwal = db.daftar_jadwal(id_rute=filter_jadwal)
        if not data_jadwal:
            ui.empty_state(
                "🕘",
                "Belum ada jadwal",
                "Tambahkan rute baru untuk membuat tiga jadwal keberangkatan otomatis.",
            )
        else:
            st.dataframe(
                _tabel_jadwal(data_jadwal),
                hide_index=True,
                width="stretch",
                height=min(420, 42 + len(data_jadwal) * 35),
            )
            st.caption(
                "Kode jadwal mengikuti prefix rute dan tidak berubah saat tarif atau "
                "nama kota diperbarui, sehingga riwayat transaksi tetap konsisten."
            )

            st.divider()
            ui.judul_bagian(
                "Atur status per jadwal",
                "Nonaktifkan hanya jam tertentu tanpa menonaktifkan seluruh rute",
            )
            pilihan_jadwal = st.selectbox(
                "Pilih kode jadwal",
                options=[j["id_jadwal"] for j in data_jadwal],
                format_func=lambda jid: next(
                    f"{j['kode_jadwal']} · {j['kota_asal']} → {j['kota_tujuan']} · "
                    f"{j['jam_keberangkatan']} WIB · "
                    f"{'Aktif' if j['aktif'] and j['rute_aktif'] else 'Nonaktif'}"
                    for j in data_jadwal
                    if j["id_jadwal"] == jid
                ),
                key="pilih_jadwal_status",
            )
            jadwal_terpilih = next(
                j for j in data_jadwal if j["id_jadwal"] == pilihan_jadwal
            )
            rute_siap = bool(jadwal_terpilih["rute_aktif"])
            if not rute_siap:
                st.warning(
                    f"Rute {jadwal_terpilih['kota_asal']} → "
                    f"{jadwal_terpilih['kota_tujuan']} sedang nonaktif. Aktifkan rutenya "
                    "terlebih dahulu bila ingin mengatur jadwal ini."
                )
            aktif_baru = st.checkbox(
                "Jadwal ini aktif dan dapat dipesan",
                value=bool(jadwal_terpilih["aktif"]),
                disabled=not rute_siap,
                key=f"status_jadwal_{pilihan_jadwal}",
                help=(
                    "Menonaktifkan jadwal hanya menutup jam tersebut. Dua jam lainnya "
                    "pada rute yang sama tetap dapat dipesan."
                ),
            )
            berubah = aktif_baru != bool(jadwal_terpilih["aktif"])
            if st.button(
                "Simpan status jadwal",
                type="primary",
                disabled=not rute_siap or not berubah,
                key="simpan_status_jadwal",
            ):
                try:
                    db.atur_status_jadwal(pilihan_jadwal, aktif_baru)
                except db.KesalahanBisnis as exc:
                    st.error(str(exc))
                else:
                    ui.set_flash(
                        "success",
                        f"Jadwal {jadwal_terpilih['kode_jadwal']} berhasil "
                        f"di{'aktifkan' if aktif_baru else 'nonaktifkan'}.",
                    )
                    st.rerun()

    with tab_daftar:
        kiri, kanan = st.columns([2, 1])
        cari = kiri.text_input(
            "🔍 Cari rute",
            placeholder="Cari kode rute, kode jadwal, kota asal, atau kota tujuan...",
            key="cari_rute",
        )
        hanya_aktif = kanan.checkbox("Tampilkan rute aktif saja", value=False)

        data = db.daftar_rute(cari, hanya_aktif)
        if not data:
            ui.empty_state(
                "🔎",
                "Rute tidak ditemukan",
                "Ubah filter pencarian atau tambahkan rute baru.",
            )
            return

        st.dataframe(
            _tabel_rute(data),
            hide_index=True,
            width="stretch",
            height=min(420, 42 + len(data) * 35),
        )

        pilihan = st.selectbox(
            "Pilih rute untuk melihat detail dan mengubah data",
            options=[r["id_rute"] for r in data],
            format_func=lambda rid: next(
                f"{r['kode_rute']} · {r['kota_asal']} → {r['kota_tujuan']} · "
                f"{rupiah(r['harga_tiket'])} · {'Aktif' if r['aktif'] else 'Nonaktif'}"
                for r in data
                if r["id_rute"] == rid
            ),
            key="pilih_rute",
        )
        pilih = next(r for r in data if r["id_rute"] == pilihan)
        jadwal_pilih = db.daftar_jadwal(id_rute=pilih["id_rute"])
        chip_jadwal = " ".join(
            ui.badge(
                f"{j['kode_jadwal']} · {j['jam_keberangkatan']}",
                "teal" if j["aktif"] and pilih["aktif"] else "grey",
            )
            for j in jadwal_pilih
        )

        kiri, kanan = st.columns([1, 1.08])
        with kiri:
            st.markdown(
                f"""
                <div class="bk-trip">
                    <div class="bk-trip-top">
                        <span class="bk-trip-code">{ui.esc(pilih['kode_rute'])}</span>
                        {ui.badge_status_aktif(pilih['aktif'])}
                    </div>
                    <div class="bk-trip-route">
                        {ui.esc(pilih['kota_asal'])}<span class="arrow">→</span>{ui.esc(pilih['kota_tujuan'])}
                    </div>
                    <div class="bk-trip-meta">
                        <span>🎟️ Tarif <b>{ui.esc(rupiah(pilih['harga_tiket']))}</b></span>
                        <span>📦 <b>{pilih['jumlah_pemesanan']}</b> pemesanan</span>
                        <span>🎫 <b>{pilih['total_tiket_terjual']}</b> tiket</span>
                    </div>
                    <div class="bk-trip-meta" style="flex-wrap:wrap">
                        <span>🕘 Kode jadwal:</span>{chip_jadwal}
                    </div>
                    <div class="bk-profile-stats" style="margin-top:.85rem">
                        <div class="bk-profile-stat"><span>Pendapatan</span><b>{ui.esc(rupiah(pilih['total_pendapatan']))}</b></div>
                        <div class="bk-profile-stat"><span>Pemesanan</span><b>{pilih['jumlah_pemesanan']}</b></div>
                        <div class="bk-profile-stat"><span>Status</span><b>{'Aktif' if pilih['aktif'] else 'Nonaktif'}</b></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if pilih["jumlah_pemesanan"] > 0:
                st.caption(
                    "Rute ini sudah memiliki riwayat transaksi, sehingga tidak dapat dihapus "
                    "permanen. Gunakan status nonaktif untuk menghentikan penjualan."
                )

        with kanan:
            st.markdown("##### ✏️ Ubah rute dan tarif")
            with st.form(f"form_ubah_rute_{pilih['id_rute']}"):
                asal = st.text_input(
                    "Kota asal *",
                    value=pilih["kota_asal"],
                    key=f"rute_asal_{pilih['id_rute']}",
                )
                tujuan = st.text_input(
                    "Kota tujuan *",
                    value=pilih["kota_tujuan"],
                    key=f"rute_tujuan_{pilih['id_rute']}",
                )
                harga = st.number_input(
                    "Tarif tiket (Rp) *",
                    min_value=1,
                    max_value=100_000_000,
                    value=int(pilih["harga_tiket"]),
                    step=5_000,
                    format="%d",
                    key=f"rute_harga_{pilih['id_rute']}",
                )
                status = st.checkbox(
                    "Rute aktif (dapat dipilih pada pemesanan baru)",
                    value=bool(pilih["aktif"]),
                    key=f"rute_aktif_{pilih['id_rute']}",
                )
                simpan = st.form_submit_button("Simpan perubahan", type="primary")
            if simpan:
                try:
                    db.ubah_rute(pilih["id_rute"], asal, tujuan, int(harga), status)
                except db.KesalahanBisnis as exc:
                    st.error(str(exc))
                else:
                    ui.set_flash(
                        "success",
                        f"Rute {pilih['kode_rute']} berhasil diperbarui.",
                    )
                    st.rerun()

            with st.expander("🗑️ Hapus rute"):
                if pilih["jumlah_pemesanan"] > 0:
                    st.info(
                        f"Rute ini dipakai pada {pilih['jumlah_pemesanan']} pemesanan sehingga "
                        "tidak dapat dihapus permanen. Nonaktifkan rute untuk menghentikan "
                        "penjualan tanpa merusak riwayat."
                    )
                else:
                    st.warning(
                        "Rute belum pernah dipakai dan dapat dihapus permanen. "
                        "Kode rute tidak akan digunakan ulang."
                    )
                    yakin = st.checkbox(
                        f"Saya yakin menghapus rute {pilih['kode_rute']}",
                        key=f"yakin_hapus_rute_{pilih['id_rute']}",
                    )
                    if st.button(
                        "Hapus rute",
                        disabled=not yakin,
                        key=f"hapus_rute_{pilih['id_rute']}",
                    ):
                        try:
                            db.hapus_rute(pilih["id_rute"])
                        except db.KesalahanBisnis as exc:
                            st.error(str(exc))
                        else:
                            ui.set_flash(
                                "success", f"Rute {pilih['kode_rute']} berhasil dihapus."
                            )
                            st.rerun()
