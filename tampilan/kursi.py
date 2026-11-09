"""Halaman pengelolaan kursi."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import database as db


def _tabel_kursi(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    return pd.DataFrame(
        {
            "Nomor kursi": df["nomor_kursi"],
            "Status": df["status_aktif"].map(lambda x: "Aktif" if x else "Nonaktif"),
            "Total pemakaian": df["total_pemakaian"],
            "Pemakaian mendatang": df["pemakaian_mendatang"],
        }
    )


def render() -> None:
    ui.page_header(
        "💺",
        "Data Kursi",
        "Kelola nomor kursi dan statusnya. Kursi nonaktif tidak dapat dipilih pada pemesanan.",
    )

    semua = db.daftar_kursi()
    aktif = [k for k in semua if k["status_aktif"]]
    nonaktif = [k for k in semua if not k["status_aktif"]]
    pemakaian_mendatang = sum(k["pemakaian_mendatang"] for k in semua)

    kolom = st.columns(4)
    with kolom[0]:
        ui.metrik("Total kursi", f"{len(semua)}", "💺", "Seluruh kursi terdaftar")
    with kolom[1]:
        ui.metrik("Kursi aktif", f"{len(aktif)}", "✅", "Dapat dipilih pada pemesanan")
    with kolom[2]:
        ui.metrik("Kursi nonaktif", f"{len(nonaktif)}", "⏸️", "Tidak dijual untuk sementara")
    with kolom[3]:
        ui.metrik(
            "Terpakai mendatang",
            f"{pemakaian_mendatang}",
            "🎫",
            "Detail kursi pada jadwal yang akan datang",
        )

    ui.judul_bagian("Denah kursi", "Status fisik kursi saat ini")
    ui.denah_kursi(semua, label_depan="Denah kursi Berkelana")

    tab_daftar, tab_tambah = st.tabs(["📋 Daftar Kursi", "➕ Tambah Kursi"])

    with tab_tambah:
        st.markdown(
            """
            <div class="bk-note">
                <b>Aturan F04:</b> nomor kursi wajib unik dan mengikuti pola huruf K
                diikuti angka (K1, K2, ..., K10). Kursi baru otomatis tersedia untuk
                jadwal mana pun. Kursi standar aplikasi adalah K1–K8.
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("form_tambah_kursi", clear_on_submit=True):
            kiri, kanan = st.columns([1, 1])
            nomor = kiri.text_input(
                "Nomor kursi *",
                placeholder="Contoh: K9",
                help="Huruf K diikuti 1–3 angka.",
            )
            status = kanan.checkbox("Kursi aktif dan dapat dipesan", value=True)
            simpan = st.form_submit_button("Simpan kursi", type="primary")
        if simpan:
            try:
                baru = db.tambah_kursi(nomor, status)
            except db.KesalahanBisnis as exc:
                st.error(str(exc))
            else:
                ui.set_flash(
                    "success",
                    f"Kursi {baru['nomor_kursi']} berhasil ditambahkan dengan status "
                    f"{'aktif' if baru['status_aktif'] else 'nonaktif'}.",
                )
                st.rerun()

    with tab_daftar:
        cari = st.text_input(
            "🔍 Cari nomor kursi",
            placeholder="Contoh: K1",
            key="cari_kursi",
        )
        data = [
            k for k in semua if cari.strip().upper() in str(k["nomor_kursi"]).upper()
        ] if cari.strip() else semua

        if not data:
            ui.empty_state("🔎", "Kursi tidak ditemukan", "Ubah kata kunci pencarian.")
            return

        st.dataframe(
            _tabel_kursi(data),
            hide_index=True,
            width="stretch",
            height=min(360, 42 + len(data) * 35),
        )

        pilihan = st.selectbox(
            "Pilih kursi untuk melihat detail dan mengubah data",
            options=[k["id_kursi"] for k in data],
            format_func=lambda kid: next(
                f"{k['nomor_kursi']} · {'Aktif' if k['status_aktif'] else 'Nonaktif'}"
                f" · {k['total_pemakaian']} pemakaian"
                for k in data
                if k["id_kursi"] == kid
            ),
            key="pilih_kursi",
        )
        pilih = next(k for k in data if k["id_kursi"] == pilihan)

        kiri, kanan = st.columns([1, 1.08])
        with kiri:
            st.markdown(
                f"""
                <div class="bk-trip">
                    <div class="bk-trip-top">
                        <span class="bk-trip-code">KURSI {ui.esc(pilih['nomor_kursi'])}</span>
                        {ui.badge_status_aktif(pilih['status_aktif'])}
                    </div>
                    <div class="bk-trip-route" style="font-size:1.5rem">💺 {ui.esc(pilih['nomor_kursi'])}</div>
                    <div class="bk-trip-meta">
                        <span>📦 Total pemakaian <b>{pilih['total_pemakaian']}</b></span>
                        <span>📅 Jadwal mendatang <b>{pilih['pemakaian_mendatang']}</b></span>
                    </div>
                    <div class="bk-note" style="margin-top:.8rem;margin-bottom:0">
                        {'Kursi ini sudah pernah dipakai. Nomor kursi dikunci agar nota lama tetap konsisten.'
                         if pilih['total_pemakaian'] else
                         'Kursi ini belum pernah dipakai sehingga nomor dan datanya masih dapat diubah.'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                "Menonaktifkan kursi tidak membatalkan pemesanan yang sudah ada. Kursi hanya "
                "hilang dari pilihan pemesanan baru."
            )

        with kanan:
            st.markdown("##### ✏️ Ubah data kursi")
            with st.form(f"form_ubah_kursi_{pilih['id_kursi']}"):
                nomor = st.text_input(
                    "Nomor kursi *",
                    value=pilih["nomor_kursi"],
                    disabled=bool(pilih["total_pemakaian"]),
                    key=f"kursi_nomor_{pilih['id_kursi']}",
                    help=(
                        "Nomor dikunci karena kursi sudah dipakai pada transaksi."
                        if pilih["total_pemakaian"]
                        else "Huruf K diikuti angka, contoh K9."
                    ),
                )
                status = st.checkbox(
                    "Kursi aktif (dapat dipilih pada pemesanan baru)",
                    value=bool(pilih["status_aktif"]),
                    key=f"kursi_aktif_{pilih['id_kursi']}",
                )
                simpan = st.form_submit_button("Simpan perubahan", type="primary")
            if simpan:
                try:
                    db.ubah_kursi(pilih["id_kursi"], nomor, status)
                except db.KesalahanBisnis as exc:
                    st.error(str(exc))
                else:
                    ui.set_flash(
                        "success", f"Data kursi {pilih['nomor_kursi']} berhasil diperbarui."
                    )
                    st.rerun()

            with st.expander("🗑️ Hapus kursi"):
                if pilih["total_pemakaian"] > 0:
                    st.info(
                        f"Kursi ini sudah dipakai pada {pilih['total_pemakaian']} detail "
                        "pemesanan sehingga tidak dapat dihapus. Nonaktifkan kursi saja."
                    )
                else:
                    st.warning(
                        "Kursi belum pernah dipakai dan dapat dihapus permanen."
                    )
                    yakin = st.checkbox(
                        f"Saya yakin menghapus kursi {pilih['nomor_kursi']}",
                        key=f"yakin_hapus_kursi_{pilih['id_kursi']}",
                    )
                    if st.button(
                        "Hapus kursi",
                        disabled=not yakin,
                        key=f"hapus_kursi_{pilih['id_kursi']}",
                    ):
                        try:
                            db.hapus_kursi(pilih["id_kursi"])
                        except db.KesalahanBisnis as exc:
                            st.error(str(exc))
                        else:
                            ui.set_flash(
                                "success", f"Kursi {pilih['nomor_kursi']} berhasil dihapus."
                            )
                            st.rerun()
