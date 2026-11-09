"""Halaman pengelolaan data kursi (F04, B07, B08)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import services
from ui import components as c


def render() -> None:
    if st.session_state.pop("_reset_form_kursi", False):
        st.session_state.pop("kursi_baru", None)

    c.hero(
        "DATA INDUK",
        "Data Kursi",
        "Atur nomor dan status kursi. Ketersediaan kursi selalu diperiksa per "
        "rute, tanggal, dan jam keberangkatan sehingga kursi yang sudah dipesan "
        "tidak dapat dipilih lagi pada jadwal yang sama.",
        chips=["F04 · Kelola kursi", "Default K1–K8", "B08 · Cek kursi per jadwal"],
    )
    c.show_flash()

    semua = services.daftar_kursi()
    aktif = [row for row in semua if row["status_aktif"]]
    nonaktif = [row for row in semua if not row["status_aktif"]]
    total_dipakai = sum(row["jumlah_dipakai"] for row in semua)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        c.metric_card("Total Kursi", str(len(semua)), "Seluruh nomor kursi", "💺", "teal")
    with m2:
        c.metric_card("Kursi Aktif", str(len(aktif)), "Dapat dipilih pelanggan", "✅", "navy")
    with m3:
        c.metric_card("Kursi Nonaktif", str(len(nonaktif)), "Tidak tampil sebagai pilihan", "⏸️", "amber")
    with m4:
        c.metric_card("Total Pemakaian", str(total_dipakai), "Kursi pada seluruh transaksi", "🎫", "rose")

    c.section_title("Denah status kursi", "Status pada bagian ini adalah status induk, bukan status per jadwal.")
    if semua:
        kartu = []
        for row in semua:
            kelas = "seat-master" + ("" if row["status_aktif"] else " off")
            status = (
                c.badge("Aktif", "green") if row["status_aktif"] else c.badge("Nonaktif", "gray")
            )
            kartu.append(
                f"""
                <div class="{kelas}">
                    <div class="seat-nomor">{c.esc(row['nomor_kursi'])}</div>
                    <div>{status}</div>
                    <div class="seat-meta">{row['jumlah_dipakai']}× dipakai</div>
                </div>
                """
            )
        st.markdown(
            '<div class="seat-master-grid">' + "".join(kartu) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        c.empty_state("Belum ada kursi", "Tambahkan kursi pertama melalui formulir di bawah.", "💺")

    c.section_title("Tambah kursi", "Nomor kursi harus unik dan berformat K diikuti angka.")
    with st.expander("➕  Buka formulir kursi", expanded=not semua):
        with st.form("form_tambah_kursi"):
            nomor = st.text_input(
                "Nomor kursi *",
                key="kursi_baru",
                placeholder="Contoh: K9",
                help="Sistem akan mengubah huruf menjadi kapital dan menolak nomor ganda.",
            )
            simpan = st.form_submit_button("Simpan Kursi", type="primary")
        if simpan:
            try:
                hasil = services.tambah_kursi(nomor)
                c.set_flash("success", f"Kursi {hasil['nomor_kursi']} berhasil ditambahkan.")
                st.session_state["_reset_form_kursi"] = True
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))

    c.section_title("Daftar kursi", "Jumlah pemakaian dihitung dari seluruh detail pemesanan.")
    if semua:
        frame = pd.DataFrame(
            [
                {
                    "Nomor": row["nomor_kursi"],
                    "Status": "Aktif" if row["status_aktif"] else "Nonaktif",
                    "Dipakai": row["jumlah_dipakai"],
                    "Jadwal Mendatang": row["jadwal_mendatang"],
                    "Dibuat": services.format_tanggal_singkat(row["dibuat_pada"][:10]),
                }
                for row in semua
            ]
        )
        st.dataframe(
            frame,
            width="stretch",
            hide_index=True,
            column_config={
                "Dipakai": st.column_config.NumberColumn(width="small"),
                "Jadwal Mendatang": st.column_config.NumberColumn(width="small"),
            },
        )
    else:
        c.empty_state("Belum ada data kursi", "Kursi yang ditambahkan akan tampil di sini.", "💺")

    if not semua:
        return

    c.section_title(
        "Kelola kursi terpilih",
        "Perubahan nomor kursi juga akan mengubah tampilan nomor pada nota lama.",
    )
    pilihan = {row["id_kursi"]: row for row in semua}
    id_terpilih = st.selectbox(
        "Pilih kursi",
        options=list(pilihan.keys()),
        format_func=lambda x: (
            f"{pilihan[x]['nomor_kursi']} · "
            f"{'Aktif' if pilihan[x]['status_aktif'] else 'Nonaktif'} · "
            f"{pilihan[x]['jumlah_dipakai']}× dipakai"
        ),
        key="kelola_kursi",
    )
    kursi = pilihan[id_terpilih]

    kiri, kanan = st.columns([1, 1.45])
    with kiri:
        status_badge = (
            c.badge("Aktif", "green") if kursi["status_aktif"] else c.badge("Nonaktif", "gray")
        )
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">Kursi {c.esc(kursi['nomor_kursi'])}</div>
                <div class="panel-note">{status_badge}</div>
                <div class="summary-line"><span>Total pemakaian</span><b>{kursi['jumlah_dipakai']} transaksi</b></div>
                <div class="summary-line"><span>Jadwal mendatang</span><b>{kursi['jadwal_mendatang']} jadwal</b></div>
                <div class="summary-line"><span>Dibuat</span><b>{services.format_tanggal_singkat(kursi['dibuat_pada'][:10])}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if kursi["jumlah_dipakai"]:
            st.info(
                "Kursi ini sudah muncul pada nota transaksi. Mengubah nomornya akan "
                "mengubah label kursi pada riwayat lama."
            )
        if kursi["jadwal_mendatang"]:
            st.warning(
                "Kursi ini masih dipakai pada jadwal mendatang. Menonaktifkannya tidak "
                "membatalkan pemesanan yang sudah ada, tetapi kursi tidak bisa dipilih lagi."
            )

    with kanan:
        tab_ubah, tab_status = st.tabs(["✏️ Ubah Nomor", "⚙️ Status & Hapus"])

        with tab_ubah:
            with st.form(f"form_ubah_kursi_{id_terpilih}"):
                nomor_baru = st.text_input(
                    "Nomor kursi",
                    value=kursi["nomor_kursi"],
                    key=f"ubah_nomor_kursi_{id_terpilih}",
                )
                status_baru = st.toggle(
                    "Kursi aktif",
                    value=bool(kursi["status_aktif"]),
                    key=f"ubah_status_kursi_{id_terpilih}",
                    help="Kursi nonaktif tidak dapat dipilih pada pemesanan baru.",
                )
                simpan = st.form_submit_button("Simpan Perubahan", type="primary")
            if simpan:
                try:
                    hasil = services.ubah_kursi(id_terpilih, nomor_baru, status_baru)
                    pesan = f"Kursi {hasil['nomor_lama']} diperbarui menjadi {hasil['nomor_kursi']}."
                    if hasil["nomor_lama"] == hasil["nomor_kursi"]:
                        pesan = f"Data kursi {hasil['nomor_kursi']} berhasil diperbarui."
                    c.set_flash("success", pesan)
                    st.rerun()
                except services.AturanBisnisError as exc:
                    st.error(str(exc))

        with tab_status:
            if kursi["status_aktif"]:
                st.info(
                    "Kursi nonaktif tetap tersimpan dan tetap muncul pada nota lama, tetapi "
                    "tidak dapat dipilih untuk pemesanan baru."
                )
                if st.button("Nonaktifkan Kursi", key=f"nonaktifkan_kursi_{id_terpilih}"):
                    try:
                        services.atur_status_kursi(id_terpilih, False)
                        c.set_flash("success", f"Kursi {kursi['nomor_kursi']} dinonaktifkan.")
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))
            else:
                if st.button(
                    "Aktifkan Kursi",
                    type="primary",
                    key=f"aktifkan_kursi_{id_terpilih}",
                ):
                    try:
                        services.atur_status_kursi(id_terpilih, True)
                        c.set_flash("success", f"Kursi {kursi['nomor_kursi']} diaktifkan.")
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))

            st.divider()
            st.markdown("**Hapus permanen**")
            if kursi["jumlah_dipakai"]:
                st.error(
                    f"Kursi ini sudah dipakai pada {kursi['jumlah_dipakai']} transaksi sehingga "
                    "tidak dapat dihapus. Nonaktifkan kursi bila tidak ingin dipakai lagi."
                )
            else:
                konfirmasi = st.checkbox(
                    f"Saya yakin ingin menghapus kursi {kursi['nomor_kursi']}",
                    key=f"konfirmasi_hapus_kursi_{id_terpilih}",
                )
                if st.button(
                    "Hapus Kursi",
                    disabled=not konfirmasi,
                    key=f"hapus_kursi_{id_terpilih}",
                ):
                    try:
                        nomor = services.hapus_kursi(id_terpilih)
                        c.set_flash("success", f"Kursi {nomor} berhasil dihapus.")
                        st.session_state.pop("kelola_kursi", None)
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))
