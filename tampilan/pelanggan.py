"""Halaman pengelolaan pelanggan."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import database as db
from utils import rupiah, tanggal_singkat


def _tabel_pelanggan(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    return pd.DataFrame(
        {
            "Kode": df["kode_pelanggan"],
            "Nama pelanggan": df["nama_pelanggan"],
            "Nomor telepon": df["nomor_telepon"],
            "Pemesanan": df["jumlah_pemesanan"],
            "Tiket": df["total_tiket"],
            "Total belanja": df["total_belanja"].map(rupiah),
            "Perjalanan terakhir": df["perjalanan_terakhir"].map(
                lambda x: tanggal_singkat(x) if pd.notna(x) else "Belum pernah"
            ),
        }
    )


def render() -> None:
    ui.page_header(
        "👥",
        "Data Pelanggan",
        "Kelola identitas pelanggan. Sistem menolak nama + nomor telepon yang sama.",
    )

    semua = db.daftar_pelanggan()
    total_pemesanan = sum(p["jumlah_pemesanan"] for p in semua)
    total_belanja = sum(p["total_belanja"] for p in semua)
    aktif = sum(1 for p in semua if p["jumlah_pemesanan"] > 0)

    kolom = st.columns(4)
    with kolom[0]:
        ui.metrik("Pelanggan", f"{len(semua)}", "👤", "Seluruh data pelanggan")
    with kolom[1]:
        ui.metrik("Sudah memesan", f"{aktif}", "✅", "Pelanggan dengan transaksi")
    with kolom[2]:
        ui.metrik("Total pemesanan", f"{total_pemesanan}", "🎫", "Seluruh transaksi aktif")
    with kolom[3]:
        ui.metrik("Total belanja", rupiah(total_belanja), "💳", "Akumulasi nilai transaksi")

    tab_daftar, tab_tambah = st.tabs(["📋 Daftar Pelanggan", "➕ Tambah Pelanggan"])

    with tab_tambah:
        st.markdown(
            """
            <div class="bk-note">
                <b>Aturan B01 & B02:</b> nama dan nomor telepon wajib diisi. Nomor telepon
                hanya boleh berisi angka. Pasangan nama + nomor telepon yang sudah ada akan
                ditolak sebagai data ganda.
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("form_tambah_pelanggan", clear_on_submit=True):
            kiri, kanan = st.columns(2)
            nama = kiri.text_input(
                "Nama pelanggan *",
                placeholder="Contoh: Andi Pratama",
                help="Gunakan nama lengkap agar mudah dicari.",
            )
            telepon = kanan.text_input(
                "Nomor telepon *",
                placeholder="Contoh: 081234567890",
                help="Hanya angka, tanpa spasi atau tanda hubung.",
            )
            st.caption("* Wajib diisi. Kode pelanggan dibuat otomatis (contoh P001).")
            disimpan = st.form_submit_button("Simpan pelanggan", type="primary")
        if disimpan:
            try:
                baru = db.tambah_pelanggan(nama, telepon)
            except db.KesalahanBisnis as exc:
                st.error(str(exc))
            else:
                ui.set_flash(
                    "success",
                    f"Pelanggan {baru['kode_pelanggan']} — {baru['nama_pelanggan']} berhasil ditambahkan.",
                )
                st.rerun()

    with tab_daftar:
        cari = st.text_input(
            "🔍 Cari pelanggan",
            placeholder="Cari kode, nama, atau nomor telepon...",
            key="cari_pelanggan",
        )
        data = db.daftar_pelanggan(cari)
        if not data:
            ui.empty_state(
                "🔎",
                "Pelanggan tidak ditemukan",
                "Ubah kata kunci pencarian atau tambahkan pelanggan baru.",
            )
            return

        st.dataframe(
            _tabel_pelanggan(data),
            hide_index=True,
            width="stretch",
            height=min(420, 42 + len(data) * 35),
        )

        pilihan = st.selectbox(
            "Pilih pelanggan untuk melihat detail dan mengubah data",
            options=[p["id_pelanggan"] for p in data],
            format_func=lambda pid: next(
                f"{p['kode_pelanggan']} · {p['nama_pelanggan']} · {p['nomor_telepon']}"
                for p in data
                if p["id_pelanggan"] == pid
            ),
            key="pilih_pelanggan",
        )
        pilih = next(p for p in data if p["id_pelanggan"] == pilihan)

        kiri, kanan = st.columns([1, 1.08])
        with kiri:
            ui.kartu_pelanggan(pilih)
            st.caption(
                "Perjalanan terakhir: "
                + (
                    tanggal_singkat(pilih["perjalanan_terakhir"])
                    if pilih["perjalanan_terakhir"]
                    else "belum pernah memesan"
                )
            )

        with kanan:
            st.markdown("##### ✏️ Ubah data pelanggan")
            with st.form(f"form_ubah_pelanggan_{pilih['id_pelanggan']}"):
                nama_baru = st.text_input(
                    "Nama pelanggan *",
                    value=pilih["nama_pelanggan"],
                    key=f"ubah_nama_{pilih['id_pelanggan']}",
                )
                telepon_baru = st.text_input(
                    "Nomor telepon *",
                    value=pilih["nomor_telepon"],
                    key=f"ubah_telepon_{pilih['id_pelanggan']}",
                )
                simpan = st.form_submit_button("Simpan perubahan", type="primary")
            if simpan:
                try:
                    db.ubah_pelanggan(
                        pilih["id_pelanggan"],
                        nama_baru,
                        telepon_baru,
                    )
                except db.KesalahanBisnis as exc:
                    st.error(str(exc))
                else:
                    ui.set_flash(
                        "success",
                        f"Data pelanggan {pilih['kode_pelanggan']} berhasil diperbarui.",
                    )
                    st.rerun()

            with st.expander("🗑️ Hapus pelanggan"):
                if pilih["jumlah_pemesanan"] > 0:
                    st.info(
                        f"Pelanggan ini memiliki {pilih['jumlah_pemesanan']} pemesanan sehingga "
                        "tidak dapat dihapus. Batalkan seluruh pemesanannya terlebih dahulu "
                        "apabila data memang harus dihapus."
                    )
                else:
                    st.warning(
                        "Penghapusan bersifat permanen. Kode pelanggan tidak akan digunakan ulang."
                    )
                    yakin = st.checkbox(
                        f"Saya yakin menghapus {pilih['nama_pelanggan']}",
                        key=f"yakin_hapus_pelanggan_{pilih['id_pelanggan']}",
                    )
                    if st.button(
                        "Hapus pelanggan",
                        disabled=not yakin,
                        key=f"hapus_pelanggan_{pilih['id_pelanggan']}",
                    ):
                        try:
                            db.hapus_pelanggan(pilih["id_pelanggan"])
                        except db.KesalahanBisnis as exc:
                            st.error(str(exc))
                        else:
                            ui.set_flash(
                                "success",
                                f"Pelanggan {pilih['kode_pelanggan']} berhasil dihapus.",
                            )
                            st.rerun()

        ui.judul_bagian(
            "Riwayat pemesanan pelanggan",
            f"{pilih['jumlah_pemesanan']} transaksi aktif",
        )
        riwayat = db.daftar_pemesanan(cari=pilih["kode_pelanggan"])
        if not riwayat:
            st.caption("Pelanggan ini belum memiliki pemesanan.")
        else:
            df = pd.DataFrame(riwayat)
            tampil = pd.DataFrame(
                {
                    "Kode": df["kode_pemesanan"],
                    "Rute": df["kota_asal"] + " → " + df["kota_tujuan"],
                    "Tanggal": df["tanggal_keberangkatan"].map(tanggal_singkat),
                    "Jam": df["jam_keberangkatan"],
                    "Kursi": df["nomor_kursi"],
                    "Tiket": df["jumlah_pesan_tiket"],
                    "Total": df["total_harga"].map(rupiah),
                }
            )
            st.dataframe(tampil, hide_index=True, width="stretch")
            st.caption(
                "Untuk melihat nota atau membatalkan pemesanan, buka menu "
                "**Riwayat Pemesanan**."
            )
