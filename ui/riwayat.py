"""Halaman riwayat, pencarian, detail, dan pembatalan transaksi (F09, B10)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import services
from ui import components as c


def _filter(
    q: str,
    id_rute: int | None,
    dari: date | None,
    sampai: date | None,
) -> list[dict]:
    return services.cari_pemesanan(
        q=q,
        id_rute=id_rute,
        dari=dari.isoformat() if dari else None,
        sampai=sampai.isoformat() if sampai else None,
        urutkan=st.session_state.get("riwayat_urutkan", "terbaru"),
        limit=300,
    )


def _batalkan(nota: dict) -> None:
    st.warning(
        f"Pembatalan **{nota['kode_pemesanan']}** akan menghapus data pemesanan dan "
        f"membebaskan kursi **{nota['daftar_kursi']}**. Pengembalian dana dilakukan "
        "di luar sistem."
    )
    yakin = st.checkbox(
        "Saya yakin ingin membatalkan pemesanan ini",
        key=f"yakin_batal_{nota['id_pemesanan']}",
    )
    kol1, kol2 = st.columns(2)
    with kol1:
        if st.button(
            "Ya, Batalkan Pemesanan",
            type="primary",
            disabled=not yakin,
            width="stretch",
            key=f"konfirmasi_batal_{nota['id_pemesanan']}",
        ):
            try:
                hasil = services.batalkan_pemesanan(nota["id_pemesanan"])
                c.set_flash(
                    "success",
                    f"Pemesanan {hasil['kode_pemesanan']} dibatalkan. "
                    f"Kursi {hasil['daftar_kursi']} kembali tersedia.",
                )
                st.session_state.pop("_nota_id", None)
                st.session_state.pop("_konfirmasi_batal", None)
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))
    with kol2:
        if st.button(
            "Tidak Jadi",
            width="stretch",
            key=f"batal_batal_{nota['id_pemesanan']}",
        ):
            st.session_state.pop("_konfirmasi_batal", None)
            st.rerun()


def render() -> None:
    c.hero(
        "TRANSAKSI",
        "Riwayat Pemesanan",
        "Cari transaksi berdasarkan kode, nama pelanggan, nomor telepon, atau rute. "
        "Buka detail untuk melihat nota dan membatalkan pemesanan bila diperlukan.",
        chips=["F09 · Cari & batalkan", "B10 · Kursi kembali tersedia", "Pencarian multi-kata"],
    )
    c.show_flash()

    services.cari_pemesanan(limit=None)
    semua_rute = services.daftar_rute()

    c.section_title("Filter pencarian", "Kosongkan filter untuk menampilkan seluruh transaksi.")
    kol1, kol2, kol3, kol4 = st.columns([1.8, 1.2, 1, 1])
    with kol1:
        q = st.text_input(
            "Kata kunci",
            placeholder="Contoh: PSN001, Andi, 0812, atau Solo…",
            key="riwayat_q",
        )
    with kol2:
        opsi_rute = {0: "Semua rute"}
        opsi_rute.update(
            {
                row["id_rute"]: f"{row['kode_rute']} · {row['kota_asal']} → {row['kota_tujuan']}"
                for row in semua_rute
            }
        )
        id_rute = st.selectbox(
            "Rute",
            options=list(opsi_rute.keys()),
            format_func=lambda x: opsi_rute[x],
            key="riwayat_rute",
        )
    with kol3:
        dari = st.date_input("Dari tanggal", value=None, key="riwayat_dari")
    with kol4:
        sampai = st.date_input("Sampai tanggal", value=None, key="riwayat_sampai")

    st.selectbox(
        "Urutkan",
        options=["terbaru", "keberangkatan", "terlama", "harga", "kode"],
        format_func=lambda x: {
            "terbaru": "Paling baru dibuat",
            "keberangkatan": "Jadwal terdekat",
            "terlama": "Paling lama dibuat",
            "harga": "Total tertinggi",
            "kode": "Kode A–Z",
        }[x],
        key="riwayat_urutkan",
    )

    if dari and sampai and dari > sampai:
        st.error("Tanggal awal tidak boleh melebihi tanggal akhir.")
        hasil: list[dict] = []
    else:
        hasil = _filter(q, id_rute or None, dari, sampai)

    total_tiket = sum(row["jumlah_pesan_tiket"] for row in hasil)
    total_nilai = sum(row["total_harga"] for row in hasil)
    pelanggan_unik = len({row["id_pelanggan"] for row in hasil})

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        c.metric_card("Transaksi Ditemukan", str(len(hasil)), "Maksimal 300 baris ditampilkan", "🧾", "teal")
    with m2:
        c.metric_card("Tiket", str(total_tiket), "Jumlah kursi pada hasil filter", "🎟️", "navy")
    with m3:
        c.metric_card("Pelanggan", str(pelanggan_unik), "Pelanggan unik pada hasil filter", "👥", "amber")
    with m4:
        c.metric_card("Nilai Transaksi", services.format_rupiah(total_nilai), "Total pada hasil filter", "💰", "rose")

    judul_hasil, kol_ekspor = st.columns([2.4, 1])
    with judul_hasil:
        c.section_title("Hasil pencarian", f"{len(hasil)} transaksi sesuai filter.")
    with kol_ekspor:
        if hasil:
            ekspor = pd.DataFrame(services.data_untuk_ekspor(
                q=q,
                id_rute=id_rute or None,
                dari=dari.isoformat() if dari else None,
                sampai=sampai.isoformat() if sampai else None,
            ))
            st.download_button(
                "⬇️  Ekspor hasil ke CSV",
                data=ekspor.to_csv(index=False).encode("utf-8-sig"),
                file_name="riwayat-pemesanan-berkelana.csv",
                mime="text/csv",
                width="stretch",
                key="unduh_csv_riwayat",
            )
        else:
            st.caption("Ekspor tersedia setelah ada hasil pencarian.")
    if not hasil:
        c.empty_state(
            "Tidak ada transaksi",
            "Ubah kata kunci atau filter tanggal untuk menemukan pemesanan.",
            "🔎",
        )
        return

    frame = pd.DataFrame(
        [
            {
                "Kode": row["kode_pemesanan"],
                "Pelanggan": row["nama_pelanggan"],
                "Telepon": row["nomor_telepon"],
                "Rute": f"{row['kota_asal']} → {row['kota_tujuan']}",
                "Keberangkatan": f"{services.format_tanggal_singkat(row['tanggal_keberangkatan'])} {services.format_jam(row['jam_keberangkatan'])}",
                "Kursi": row["daftar_kursi"],
                "Tiket": row["jumlah_pesan_tiket"],
                "Total": services.format_rupiah(row["total_harga"]),
                "Dibuat": row["dibuat_pada"][:10],
            }
            for row in hasil
        ]
    )
    st.dataframe(frame, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # Detail transaksi
    # ------------------------------------------------------------------
    c.section_title(
        "Detail & pembatalan",
        "Pilih kode transaksi untuk membuka rincian nota dan tindakan pembatalan.",
    )
    peta = {row["id_pemesanan"]: row for row in hasil}
    if (
        "riwayat_detail" in st.session_state
        and st.session_state["riwayat_detail"] not in peta
    ):
        st.session_state.pop("riwayat_detail", None)
    id_terpilih = st.selectbox(
        "Pilih transaksi",
        options=list(peta.keys()),
        format_func=lambda x: (
            f"{peta[x]['kode_pemesanan']} · {peta[x]['nama_pelanggan']} · "
            f"{peta[x]['kota_asal']} → {peta[x]['kota_tujuan']} · "
            f"{services.format_rupiah(peta[x]['total_harga'])}"
        ),
        key="riwayat_detail",
    )
    nota = services.ambil_nota(id_terpilih)
    if not nota:
        c.empty_state("Transaksi tidak ditemukan", "Data mungkin baru saja dibatalkan.", "🧾")
        return

    kiri, kanan = st.columns([1.2, 1])
    with kiri:
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">{c.esc(nota['kode_pemesanan'])}
                    {c.badge('Tersimpan', 'green')}</div>
                <div class="panel-note">Dibuat {c.esc(nota['dibuat_pada'])}</div>
                <div class="summary-line"><span>Pelanggan</span><b>{c.esc(nota['nama_pelanggan'])} ({c.esc(nota['kode_pelanggan'])})</b></div>
                <div class="summary-line"><span>Telepon</span><b>{c.esc(nota['nomor_telepon'])}</b></div>
                <div class="summary-line"><span>Rute</span><b>{c.esc(nota['kota_asal'])} → {c.esc(nota['kota_tujuan'])}</b></div>
                <div class="summary-line"><span>Jadwal</span><b>{services.format_tanggal_singkat(nota['tanggal_keberangkatan'])} · {services.format_jam(nota['jam_keberangkatan'])}</b></div>
                <div class="summary-line"><span>Kursi</span><b>{c.esc(nota['daftar_kursi'])}</b></div>
                <div class="summary-line"><span>Jumlah tiket</span><b>{nota['jumlah_pesan_tiket']}</b></div>
                <div class="summary-line"><span>Harga saat pesan</span><b>{services.format_rupiah(nota['harga_per_tiket'])} / tiket</b></div>
                <div class="summary-line"><span>Total</span><b>{services.format_rupiah(nota['total_harga'])}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Lihat bentuk nota"):
            c.render_nota(nota)
    with kanan:
        st.markdown("#### Tindakan")
        st.download_button(
            "⬇️  Unduh nota (.txt)",
            data=c.nota_sebagai_teks(nota),
            file_name=f"nota-{nota['kode_pemesanan']}.txt",
            mime="text/plain",
            width="stretch",
            key=f"unduh_riwayat_txt_{id_terpilih}",
        )
        st.download_button(
            "🖨️  Unduh nota cetak (.html)",
            data=c.nota_html_dokumen(nota),
            file_name=f"nota-{nota['kode_pemesanan']}.html",
            mime="text/html",
            width="stretch",
            key=f"unduh_riwayat_html_{id_terpilih}",
        )

        st.divider()
        konfirmasi_id = st.session_state.get("_konfirmasi_batal")
        if konfirmasi_id == id_terpilih:
            _batalkan(nota)
        else:
            st.caption(
                "Pembatalan menghapus pemesanan beserta detail kursi. Kursi yang "
                "dibebaskan dapat dipesan kembali pada jadwal yang sama."
            )
            if st.button(
                "Batalkan Pemesanan",
                width="stretch",
                key=f"minta_batal_{id_terpilih}",
            ):
                st.session_state["_konfirmasi_batal"] = id_terpilih
                st.rerun()

        st.markdown(
            """
            <div class="panel" style="margin-top:1rem">
                <div class="panel-title">Informasi aturan</div>
                <div class="panel-note">
                    Jika pemesanan tidak ditemukan, sistem menolak pembatalan (B10).
                    Pengembalian dana tidak diproses oleh sistem.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
