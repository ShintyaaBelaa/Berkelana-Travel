"""Halaman pengelolaan rute, tarif, dan status aktif (F03, B03, B04)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import services
from ui import components as c


def _reset_form_tambah() -> None:
    for kunci in ("rute_asal", "rute_tujuan", "rute_harga"):
        st.session_state.pop(kunci, None)


def render() -> None:
    if st.session_state.pop("_reset_form_rute", False):
        _reset_form_tambah()

    c.hero(
        "DATA INDUK",
        "Data Rute & Tarif",
        "Kelola perjalanan yang dijual beserta tarifnya. Rute yang sudah dipakai "
        "tidak dapat dihapus permanen, tetapi dapat dinonaktifkan.",
        chips=["F03 · Rute dan tarif", "B03 · Asal ≠ tujuan", "B04 · Nonaktifkan, jangan hapus"],
    )
    c.show_flash()

    semua = services.daftar_rute()
    aktif = [row for row in semua if row["aktif"]]
    nonaktif = [row for row in semua if not row["aktif"]]
    total_pendapatan = sum(row["total_pendapatan"] for row in semua)
    rata_tarif = int(sum(row["harga_tiket"] for row in semua) / len(semua)) if semua else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        c.metric_card("Total Rute", str(len(semua)), f"{len(aktif)} aktif · {len(nonaktif)} nonaktif", "🛣️", "teal")
    with m2:
        c.metric_card("Rute Aktif", str(len(aktif)), "Dapat dipilih saat pemesanan", "✅", "navy")
    with m3:
        c.metric_card("Rata-rata Tarif", services.format_rupiah(rata_tarif), "Dari seluruh rute", "🏷️", "amber")
    with m4:
        c.metric_card("Pendapatan Rute", services.format_rupiah(total_pendapatan), "Akumulasi semua transaksi", "💰", "rose")

    c.section_title("Tambah rute baru", "Tarif harus lebih besar dari nol dan kota asal berbeda dari tujuan.")
    with st.expander("➕  Buka formulir rute", expanded=not semua):
        with st.form("form_tambah_rute"):
            kol1, kol2, kol3 = st.columns([1.2, 1.2, 1])
            with kol1:
                asal = st.text_input(
                    "Kota asal *",
                    key="rute_asal",
                    placeholder="Contoh: Semarang",
                )
            with kol2:
                tujuan = st.text_input(
                    "Kota tujuan *",
                    key="rute_tujuan",
                    placeholder="Contoh: Solo",
                )
            with kol3:
                harga = st.number_input(
                    "Tarif tiket (Rp) *",
                    min_value=0,
                    max_value=1_000_000_000,
                    value=75_000,
                    step=5_000,
                    key="rute_harga",
                    help="Harga yang berlaku untuk pemesanan baru.",
                )
            simpan = st.form_submit_button("Simpan Rute", type="primary")

        if simpan:
            try:
                hasil = services.tambah_rute(asal, tujuan, int(harga))
                c.set_flash(
                    "success",
                    f"Rute {hasil['kode_rute']} — {hasil['kota_asal']} → "
                    f"{hasil['kota_tujuan']} berhasil ditambahkan dengan tarif "
                    f"{services.format_rupiah(hasil['harga_tiket'])}.",
                )
                st.session_state["_reset_form_rute"] = True
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))

    c.section_title("Daftar rute", "Tarif yang ditampilkan adalah tarif yang berlaku saat ini.")
    kol_cari, kol_info = st.columns([2.2, 1])
    with kol_cari:
        cari = st.text_input(
            "Cari rute",
            key="cari_rute",
            placeholder="Ketik kode rute, kota asal, atau kota tujuan…",
            label_visibility="collapsed",
        )
    with kol_info:
        st.caption(f"Menampilkan {len(semua)} rute terdaftar.")

    hasil = services.daftar_rute(cari)
    if not hasil:
        if semua:
            c.empty_state("Rute tidak ditemukan", f"Tidak ada rute yang cocok dengan “{cari}”.", "🔎")
        else:
            c.empty_state("Belum ada rute", "Tambahkan rute pertama melalui formulir di atas.", "🛣️")
    else:
        frame = pd.DataFrame(
            [
                {
                    "Kode": row["kode_rute"],
                    "Kota Asal": row["kota_asal"],
                    "Kota Tujuan": row["kota_tujuan"],
                    "Tarif": services.format_rupiah(row["harga_tiket"]),
                    "Status": "Aktif" if row["aktif"] else "Nonaktif",
                    "Pemesanan": row["jumlah_pemesanan"],
                    "Tiket": row["total_tiket"],
                    "Pendapatan": services.format_rupiah(row["total_pendapatan"]),
                }
                for row in hasil
            ]
        )
        st.dataframe(
            frame,
            width="stretch",
            hide_index=True,
            column_config={
                "Pemesanan": st.column_config.NumberColumn(width="small"),
                "Tiket": st.column_config.NumberColumn(width="small"),
            },
        )

    if not semua:
        return

    c.section_title(
        "Kelola rute terpilih",
        "Perubahan tarif hanya berlaku untuk pemesanan baru; nota lama tetap memakai harga saat pemesanan.",
    )
    pilihan = {row["id_rute"]: row for row in semua}
    id_terpilih = st.selectbox(
        "Pilih rute",
        options=list(pilihan.keys()),
        format_func=lambda x: (
            f"{pilihan[x]['kode_rute']} · {pilihan[x]['kota_asal']} → "
            f"{pilihan[x]['kota_tujuan']} · {services.format_rupiah(pilihan[x]['harga_tiket'])}"
        ),
        key="kelola_rute",
    )
    rute = pilihan[id_terpilih]

    kiri, kanan = st.columns([1, 1.45])
    with kiri:
        status_badge = (
            c.badge("Aktif", "green") if rute["aktif"] else c.badge("Nonaktif", "gray")
        )
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">{c.esc(rute['kota_asal'])} → {c.esc(rute['kota_tujuan'])}</div>
                <div class="panel-note">{c.badge(rute['kode_rute'], 'teal')} {status_badge}</div>
                <div class="summary-line"><span>Tarif saat ini</span><b>{services.format_rupiah(rute['harga_tiket'])}</b></div>
                <div class="summary-line"><span>Jumlah pemesanan</span><b>{rute['jumlah_pemesanan']}</b></div>
                <div class="summary-line"><span>Tiket terjual</span><b>{rute['total_tiket']}</b></div>
                <div class="summary-line"><span>Pendapatan</span><b>{services.format_rupiah(rute['total_pendapatan'])}</b></div>
                <div class="summary-line"><span>Jadwal pernah dipesan</span><b>{rute['jumlah_jadwal']}</b></div>
                <div class="summary-line"><span>Terdaftar</span><b>{services.format_tanggal_singkat(rute['dibuat_pada'][:10])}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not rute["aktif"]:
            st.warning("Rute ini nonaktif dan tidak akan muncul pada pilihan pemesanan baru.")

    with kanan:
        tab_ubah, tab_jadwal, tab_status = st.tabs(
            ["✏️ Ubah Rute", "🗓️ Jadwal", "⚙️ Status & Hapus"]
        )

        with tab_ubah:
            with st.form(f"form_ubah_rute_{id_terpilih}"):
                asal_baru = st.text_input(
                    "Kota asal",
                    value=rute["kota_asal"],
                    key=f"ubah_asal_{id_terpilih}",
                )
                tujuan_baru = st.text_input(
                    "Kota tujuan",
                    value=rute["kota_tujuan"],
                    key=f"ubah_tujuan_{id_terpilih}",
                )
                harga_baru = st.number_input(
                    "Tarif tiket (Rp)",
                    min_value=0,
                    max_value=1_000_000_000,
                    value=int(rute["harga_tiket"]),
                    step=5_000,
                    key=f"ubah_harga_{id_terpilih}",
                )
                simpan = st.form_submit_button("Simpan Perubahan", type="primary")
            if simpan:
                try:
                    hasil = services.ubah_rute(
                        id_terpilih, asal_baru, tujuan_baru, int(harga_baru)
                    )
                    if hasil["harga_lama"] != hasil["harga_tiket"]:
                        pesan = (
                            f"Rute {hasil['kode_rute']} diperbarui. Tarif berubah dari "
                            f"{services.format_rupiah(hasil['harga_lama'])} menjadi "
                            f"{services.format_rupiah(hasil['harga_tiket'])}. "
                            "Transaksi lama tetap memakai harga saat pemesanan."
                        )
                    else:
                        pesan = f"Rute {hasil['kode_rute']} berhasil diperbarui."
                    c.set_flash("success", pesan)
                    st.rerun()
                except services.AturanBisnisError as exc:
                    st.error(str(exc))

        with tab_jadwal:
            jadwal = services.jadwal_rute(id_terpilih, 15)
            if not jadwal:
                c.empty_state(
                    "Belum ada jadwal",
                    "Rute ini belum pernah dipakai pada transaksi.",
                    "🗓️",
                )
            else:
                st.caption("Agregasi pemesanan per tanggal dan jam keberangkatan.")
                frame = pd.DataFrame(
                    [
                        {
                            "Tanggal": services.format_tanggal_singkat(row["tanggal_keberangkatan"]),
                            "Jam": services.format_jam(row["jam_keberangkatan"]),
                            "Pemesanan": row["jumlah_pemesanan"],
                            "Tiket": row["jumlah_tiket"],
                            "Kursi": row["kursi"],
                            "Pendapatan": services.format_rupiah(row["pendapatan"]),
                        }
                        for row in jadwal
                    ]
                )
                st.dataframe(frame, width="stretch", hide_index=True)

        with tab_status:
            if rute["aktif"]:
                st.info(
                    "Menonaktifkan rute akan menyembunyikannya dari pilihan pemesanan baru. "
                    "Transaksi dan jadwal yang sudah ada tetap tersimpan."
                )
                if st.button("Nonaktifkan Rute", key=f"nonaktifkan_{id_terpilih}"):
                    try:
                        services.atur_status_rute(id_terpilih, False)
                        c.set_flash("success", f"Rute {rute['kode_rute']} berhasil dinonaktifkan.")
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))
            else:
                st.info(
                    "Mengaktifkan rute akan menampilkannya kembali pada pilihan pemesanan."
                )
                if st.button(
                    "Aktifkan Rute",
                    type="primary",
                    key=f"aktifkan_{id_terpilih}",
                ):
                    try:
                        services.atur_status_rute(id_terpilih, True)
                        c.set_flash("success", f"Rute {rute['kode_rute']} berhasil diaktifkan.")
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))

            st.divider()
            st.markdown("**Hapus permanen**")
            if rute["jumlah_pemesanan"]:
                st.error(
                    f"Rute ini sudah dipakai pada {rute['jumlah_pemesanan']} pemesanan. "
                    "Sesuai aturan B04, rute tidak boleh dihapus; gunakan tombol nonaktifkan."
                )
            else:
                st.caption(
                    "Rute belum pernah dipakai sehingga masih dapat dihapus permanen."
                )
                konfirmasi = st.checkbox(
                    f"Saya yakin ingin menghapus rute {rute['kode_rute']}",
                    key=f"konfirmasi_hapus_rute_{id_terpilih}",
                )
                if st.button(
                    "Hapus Rute",
                    disabled=not konfirmasi,
                    key=f"hapus_rute_{id_terpilih}",
                ):
                    try:
                        kode = services.hapus_rute(id_terpilih)
                        c.set_flash("success", f"Rute {kode} berhasil dihapus.")
                        st.session_state.pop("kelola_rute", None)
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))
