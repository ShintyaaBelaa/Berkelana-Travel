"""Halaman pengelolaan data pelanggan (F01, F02)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import services
from ui import components as c


def _bersihkan_state(kunci: list[str]) -> None:
    for item in kunci:
        st.session_state.pop(item, None)


def render() -> None:
    # Pembersihan field setelah penyimpanan berhasil (dilakukan sebelum widget dibuat).
    if st.session_state.pop("_reset_form_pelanggan", False):
        _bersihkan_state(["tambah_nama", "tambah_telepon"])

    c.hero(
        "DATA INDUK",
        "Data Pelanggan",
        "Catat pelanggan yang akan memesan tiket. Sistem menolak nama dan nomor "
        "telepon yang sama agar data tidak ganda.",
        chips=["F01 · Kelola pelanggan", "F02 · Tolak duplikasi", "Nomor telepon hanya angka"],
    )
    c.show_flash()

    semua = services.daftar_pelanggan()
    total_belanja = sum(row["total_belanja"] for row in semua)
    pernah_memesan = sum(1 for row in semua if row["jumlah_pemesanan"] > 0)

    m1, m2, m3 = st.columns(3)
    with m1:
        c.metric_card("Total Pelanggan", str(len(semua)), "Seluruh pelanggan terdaftar", "👥", "teal")
    with m2:
        c.metric_card(
            "Pernah Memesan",
            str(pernah_memesan),
            f"{len(semua) - pernah_memesan} belum pernah memesan",
            "🎫",
            "navy",
        )
    with m3:
        c.metric_card(
            "Nilai Transaksi",
            services.format_rupiah(total_belanja),
            "Total seluruh pemesanan pelanggan",
            "💰",
            "amber",
        )

    c.section_title("Tambah pelanggan baru", "Nama dan nomor telepon wajib diisi.")
    with st.expander("➕  Buka formulir pelanggan", expanded=not semua):
        with st.form("form_tambah_pelanggan"):
            kol1, kol2 = st.columns(2)
            with kol1:
                nama = st.text_input(
                    "Nama lengkap *",
                    key="tambah_nama",
                    placeholder="Contoh: Andi Pratama",
                    help="Minimal 2 karakter. Nama boleh sama selama nomor telepon berbeda.",
                )
            with kol2:
                telepon = st.text_input(
                    "Nomor telepon *",
                    key="tambah_telepon",
                    placeholder="Contoh: 081234567890",
                    help="Hanya angka, 7–15 digit. Spasi, tanda hubung, dan huruf akan ditolak.",
                )
            dikirim = st.form_submit_button("Simpan Pelanggan", type="primary")

        if dikirim:
            try:
                hasil = services.tambah_pelanggan(nama, telepon)
                c.set_flash(
                    "success",
                    f"Pelanggan {hasil['kode_pelanggan']} — {hasil['nama_pelanggan']} "
                    "berhasil ditambahkan.",
                )
                st.session_state["_reset_form_pelanggan"] = True
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))

    c.section_title("Daftar pelanggan", "Gunakan pencarian berdasarkan kode, nama, atau telepon.")
    kol_cari, kol_info = st.columns([2.2, 1])
    with kol_cari:
        cari = st.text_input(
            "Cari pelanggan",
            key="cari_pelanggan",
            placeholder="Ketik kode, nama, atau nomor telepon…",
            label_visibility="collapsed",
        )
    with kol_info:
        st.caption(f"Menampilkan {len(semua)} pelanggan terdaftar.")

    hasil = services.daftar_pelanggan(cari)

    if not hasil:
        if semua:
            c.empty_state(
                "Pelanggan tidak ditemukan",
                f"Tidak ada data yang cocok dengan pencarian “{cari}”.",
                "🔎",
            )
        else:
            c.empty_state(
                "Belum ada pelanggan",
                "Tambahkan pelanggan pertama melalui formulir di atas.",
                "👥",
            )
    else:
        frame = pd.DataFrame(
            [
                {
                    "Kode": row["kode_pelanggan"],
                    "Nama Pelanggan": row["nama_pelanggan"],
                    "Nomor Telepon": row["nomor_telepon"],
                    "Pemesanan": row["jumlah_pemesanan"],
                    "Tiket": row["total_tiket"],
                    "Total Belanja": services.format_rupiah(row["total_belanja"]),
                    "Terdaftar": services.format_tanggal_singkat(row["dibuat_pada"][:10]),
                }
                for row in hasil
            ]
        )
        st.dataframe(frame, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # Kelola pelanggan terpilih
    # ------------------------------------------------------------------
    if not semua:
        return

    c.section_title(
        "Kelola data pelanggan",
        "Pilih pelanggan untuk mengubah data, melihat riwayat, atau menghapus data.",
    )
    pilihan = {row["id_pelanggan"]: row for row in semua}
    id_terpilih = st.selectbox(
        "Pilih pelanggan",
        options=list(pilihan.keys()),
        format_func=lambda x: (
            f"{pilihan[x]['kode_pelanggan']} · {pilihan[x]['nama_pelanggan']} · "
            f"{pilihan[x]['nomor_telepon']}"
        ),
        key="kelola_pelanggan",
    )
    pelanggan = pilihan[id_terpilih]

    kiri, kanan = st.columns([1, 1.45])
    with kiri:
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">{c.esc(pelanggan['nama_pelanggan'])}</div>
                <div class="panel-note">
                    {c.badge(pelanggan['kode_pelanggan'], 'teal')}
                    {c.badge('Aktif sebagai pelanggan', 'green')}
                </div>
                <div class="summary-line"><span>Nomor telepon</span><b>{c.esc(pelanggan['nomor_telepon'])}</b></div>
                <div class="summary-line"><span>Terdaftar</span><b>{services.format_tanggal_indo(pelanggan['dibuat_pada'][:10])}</b></div>
                <div class="summary-line"><span>Jumlah pemesanan</span><b>{pelanggan['jumlah_pemesanan']}</b></div>
                <div class="summary-line"><span>Total tiket</span><b>{pelanggan['total_tiket']}</b></div>
                <div class="summary-line"><span>Total belanja</span><b>{services.format_rupiah(pelanggan['total_belanja'])}</b></div>
                <div class="summary-line"><span>Transaksi terakhir</span><b>{pelanggan['terakhir_pemesanan'][:10] if pelanggan['terakhir_pemesanan'] else '—'}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kanan:
        tab_ubah, tab_riwayat, tab_hapus = st.tabs(["✏️ Ubah Data", "🧾 Riwayat", "🗑️ Hapus"])

        with tab_ubah:
            with st.form(f"form_ubah_pelanggan_{id_terpilih}"):
                nama_baru = st.text_input(
                    "Nama lengkap",
                    value=pelanggan["nama_pelanggan"],
                    key=f"ubah_nama_{id_terpilih}",
                )
                telepon_baru = st.text_input(
                    "Nomor telepon",
                    value=pelanggan["nomor_telepon"],
                    key=f"ubah_telepon_{id_terpilih}",
                )
                simpan = st.form_submit_button("Simpan Perubahan", type="primary")
            if simpan:
                try:
                    services.ubah_pelanggan(
                        id_terpilih,
                        nama_baru,
                        telepon_baru,
                    )
                    c.set_flash("success", "Data pelanggan berhasil diperbarui.")
                    st.rerun()
                except services.AturanBisnisError as exc:
                    st.error(str(exc))

        with tab_riwayat:
            riwayat = services.riwayat_pelanggan(id_terpilih)
            if not riwayat:
                c.empty_state(
                    "Belum ada riwayat",
                    "Pelanggan ini belum pernah melakukan pemesanan.",
                    "🧾",
                )
            else:
                st.caption(f"{len(riwayat)} transaksi ditemukan.")
                frame = pd.DataFrame(
                    [
                        {
                            "Kode": row["kode_pemesanan"],
                            "Rute": f"{row['kota_asal']} → {row['kota_tujuan']}",
                            "Keberangkatan": f"{services.format_tanggal_singkat(row['tanggal_keberangkatan'])} {services.format_jam(row['jam_keberangkatan'])}",
                            "Kursi": row["daftar_kursi"],
                            "Tiket": row["jumlah_pesan_tiket"],
                            "Total": services.format_rupiah(row["total_harga"]),
                        }
                        for row in riwayat
                    ]
                )
                st.dataframe(frame, width="stretch", hide_index=True)

        with tab_hapus:
            st.warning(
                "Penghapusan pelanggan hanya dapat dilakukan jika belum memiliki transaksi. "
                "Riwayat pemesanan tidak boleh ikut terhapus."
            )
            if pelanggan["jumlah_pemesanan"]:
                st.error(
                    f"Pelanggan ini memiliki {pelanggan['jumlah_pemesanan']} pemesanan sehingga "
                    "tidak dapat dihapus. Data tetap disimpan untuk menjaga riwayat transaksi."
                )
            else:
                konfirmasi = st.checkbox(
                    f"Saya yakin ingin menghapus {pelanggan['nama_pelanggan']}",
                    key=f"konfirmasi_hapus_{id_terpilih}",
                )
                if st.button(
                    "Hapus Pelanggan",
                    type="primary",
                    disabled=not konfirmasi,
                    key=f"tombol_hapus_{id_terpilih}",
                ):
                    try:
                        kode = services.hapus_pelanggan(id_terpilih)
                        c.set_flash("success", f"Pelanggan {kode} berhasil dihapus.")
                        st.session_state.pop("kelola_pelanggan", None)
                        st.rerun()
                    except services.AturanBisnisError as exc:
                        st.error(str(exc))
