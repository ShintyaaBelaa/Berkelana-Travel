"""Halaman pembuatan pemesanan tiket dengan denah kursi (F05–F08)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

import services
from ui import components as c

JAM_KEBERANGKATAN = [f"{jam:02d}:00" for jam in range(5, 23)]


def _toggle_kursi(id_kursi: int) -> None:
    """Callback tombol kursi: tambah/hapus satu kursi dari pilihan aktif."""
    daftar = st.session_state.setdefault("_booking_seats", [])
    if id_kursi in daftar:
        daftar.remove(id_kursi)
    else:
        daftar.append(id_kursi)


def _siapkan_pelanggan() -> list[dict]:
    """Pelanggan + pemrosesan pelanggan baru yang dipilih otomatis."""
    if st.session_state.pop("_reset_form_booking_customer", False):
        st.session_state.pop("booking_nama_baru", None)
        st.session_state.pop("booking_telepon_baru", None)

    pelanggan = services.daftar_pelanggan()
    id_tersedia = {row["id_pelanggan"] for row in pelanggan}
    pending = st.session_state.pop("_pilih_pelanggan", None)
    if pending and pending in id_tersedia:
        st.session_state["pelanggan_dipilih"] = pending
    if (
        "pelanggan_dipilih" in st.session_state
        and st.session_state["pelanggan_dipilih"] not in id_tersedia
    ):
        st.session_state.pop("pelanggan_dipilih", None)
    return pelanggan


def _render_nota_sukses() -> None:
    id_nota = st.session_state.get("_nota_id")
    if not id_nota:
        return
    nota = services.ambil_nota(id_nota)
    if not nota:
        st.session_state.pop("_nota_id", None)
        return

    c.section_title(
        "Nota pemesanan",
        f"Pemesanan {nota['kode_pemesanan']} berhasil disimpan. Serahkan nota ini kepada pelanggan.",
    )
    kiri, kanan = st.columns([1.75, 1])
    with kiri:
        c.render_nota(nota)
    with kanan:
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">Ringkasan singkat</div>
                <div class="summary-line"><span>Kode</span><b>{c.esc(nota['kode_pemesanan'])}</b></div>
                <div class="summary-line"><span>Pelanggan</span><b>{c.esc(nota['nama_pelanggan'])}</b></div>
                <div class="summary-line"><span>Kursi</span><b>{c.esc(nota['daftar_kursi'])}</b></div>
                <div class="summary-line"><span>Jumlah tiket</span><b>{nota['jumlah_pesan_tiket']}</b></div>
                <div class="summary-line"><span>Total</span><b>{services.format_rupiah(nota['total_harga'])}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️  Unduh nota (.txt)",
            data=c.nota_sebagai_teks(nota),
            file_name=f"nota-{nota['kode_pemesanan']}.txt",
            mime="text/plain",
            width="stretch",
            key="unduh_nota_txt",
        )
        st.download_button(
            "🖨️  Unduh nota cetak (.html)",
            data=c.nota_html_dokumen(nota),
            file_name=f"nota-{nota['kode_pemesanan']}.html",
            mime="text/html",
            width="stretch",
            key="unduh_nota_html",
        )
        if st.button("Tutup nota & buat pemesanan baru", width="stretch"):
            st.session_state.pop("_nota_id", None)
            st.rerun()
        st.caption(
            "File HTML dapat dibuka di browser lalu dicetak atau disimpan sebagai PDF."
        )
    st.divider()


def _render_pelanggan(pelanggan: list[dict]) -> dict | None:
    c.step_label(1, "Pilih pelanggan")
    if not pelanggan:
        c.empty_state(
            "Belum ada pelanggan",
            "Tambahkan pelanggan terlebih dahulu melalui formulir di bawah.",
            "👤",
        )

    terpilih = None
    if pelanggan:
        peta = {row["id_pelanggan"]: row for row in pelanggan}
        id_terpilih = st.selectbox(
            "Pelanggan *",
            options=list(peta.keys()),
            format_func=lambda x: (
                f"{peta[x]['kode_pelanggan']} · {peta[x]['nama_pelanggan']} · "
                f"{peta[x]['nomor_telepon']}"
            ),
            key="pelanggan_dipilih",
            help="Cari dengan mengetik nama atau nomor telepon pada kotak pilihan.",
        )
        terpilih = peta[id_terpilih]
        st.caption(
            f"{terpilih['jumlah_pemesanan']} pemesanan sebelumnya · "
            f"{terpilih['total_tiket']} tiket · total "
            f"{services.format_rupiah(terpilih['total_belanja'])}"
        )

    with st.expander("➕  Pelanggan belum terdaftar? Tambahkan di sini", expanded=not pelanggan):
        with st.form("form_pelanggan_cepat"):
            kol1, kol2 = st.columns(2)
            with kol1:
                nama = st.text_input(
                    "Nama lengkap *",
                    key="booking_nama_baru",
                    placeholder="Contoh: Andi Pratama",
                )
            with kol2:
                telepon = st.text_input(
                    "Nomor telepon *",
                    key="booking_telepon_baru",
                    placeholder="Contoh: 081234567890",
                    help="Hanya angka, 7–15 digit.",
                )
            tambah = st.form_submit_button("Simpan & Pilih Pelanggan", type="primary")

        if tambah:
            try:
                hasil = services.tambah_pelanggan(nama, telepon)
                c.set_flash(
                    "success",
                    f"Pelanggan {hasil['kode_pelanggan']} — {hasil['nama_pelanggan']} "
                    "berhasil ditambahkan dan dipilih.",
                )
                st.session_state["_pilih_pelanggan"] = hasil["id_pelanggan"]
                st.session_state["_reset_form_booking_customer"] = True
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))
    return terpilih


def _render_jadwal(rute_aktif: list[dict]) -> tuple[dict | None, str, str, bool]:
    c.step_label(2, "Pilih rute dan jadwal keberangkatan")
    if not rute_aktif:
        c.empty_state(
            "Belum ada rute aktif",
            "Aktifkan rute melalui menu Data Rute & Tarif sebelum membuat pemesanan.",
            "🛣️",
        )
        return None, "", "", False

    peta = {row["id_rute"]: row for row in rute_aktif}
    if (
        "booking_rute" in st.session_state
        and st.session_state["booking_rute"] not in peta
    ):
        st.session_state.pop("booking_rute", None)

    kol1, kol2, kol3 = st.columns([1.5, 1, 1])
    with kol1:
        id_rute = st.selectbox(
            "Rute aktif *",
            options=list(peta.keys()),
            format_func=lambda x: (
                f"{peta[x]['kode_rute']} · {peta[x]['kota_asal']} → "
                f"{peta[x]['kota_tujuan']} · {services.format_rupiah(peta[x]['harga_tiket'])}"
            ),
            key="booking_rute",
        )
    with kol2:
        hari_ini = date.today()
        if (
            "booking_tanggal" in st.session_state
            and st.session_state["booking_tanggal"] < hari_ini
        ):
            st.session_state["booking_tanggal"] = hari_ini + timedelta(days=1)
        tanggal = st.date_input(
            "Tanggal keberangkatan *",
            value=hari_ini + timedelta(days=1),
            min_value=hari_ini,
            format="DD/MM/YYYY",
            key="booking_tanggal",
        )
    with kol3:
        jam = st.selectbox(
            "Jam keberangkatan *",
            options=JAM_KEBERANGKATAN,
            index=JAM_KEBERANGKATAN.index("08:00"),
            key="booking_jam",
        )

    rute = peta[id_rute]
    tanggal_iso = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)

    jadwal_valid = True
    try:
        services.validasi_jadwal(tanggal_iso, jam)
    except services.AturanBisnisError as exc:
        jadwal_valid = False
        st.warning(str(exc))

    # Reset kursi terpilih jika rute/tanggal/jam berubah.
    sig = f"{id_rute}|{tanggal_iso}|{jam}"
    if st.session_state.get("_booking_sig") != sig:
        st.session_state["_booking_sig"] = sig
        st.session_state["_booking_seats"] = []

    if jadwal_valid:
        ringkas = services.ringkasan_jadwal(id_rute, tanggal_iso, jam)
        kiri, kanan = st.columns([1.5, 1])
        with kiri:
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">{c.esc(rute['kota_asal'])} → {c.esc(rute['kota_tujuan'])}</div>
                    <div class="panel-note">
                        {c.badge(rute['kode_rute'], 'teal')}
                        {c.badge(services.format_tanggal_indo(tanggal_iso), 'amber')}
                        {c.badge('Pukul ' + services.format_jam(jam), 'gray')}
                    </div>
                    <div class="summary-line"><span>Tarif per tiket</span><b>{services.format_rupiah(rute['harga_tiket'])}</b></div>
                    <div class="summary-line"><span>Kursi tersedia</span><b>{ringkas['tersedia']} dari {ringkas['kursi_aktif']} kursi aktif</b></div>
                    <div class="summary-line"><span>Kursi terisi</span><b>{ringkas['terisi']}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kanan:
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Pemeriksaan waktu</div>
                    <div class="panel-note">
                        Waktu sekarang: <b>{datetime.now().strftime('%d-%m-%Y %H:%M')}</b><br>
                        Jadwal harus berada setelah waktu tersebut (aturan B06).
                        Kursi diperiksa ulang saat tombol konfirmasi ditekan.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    return rute, tanggal_iso, jam, jadwal_valid


def _render_denah(id_rute: int, tanggal: str, jam: str) -> list[int]:
    c.step_label(3, "Pilih kursi")
    st.markdown(
        """
        <div class="seat-legend">
            <span><i class="legend-dot legend-available"></i>Tersedia</span>
            <span><i class="legend-dot legend-selected"></i>Dipilih</span>
            <span><i class="legend-dot legend-booked"></i>Sudah dipesan</span>
            <span><i class="legend-dot legend-inactive"></i>Nonaktif</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kursi = services.ambil_kursi_untuk_jadwal(id_rute, tanggal, jam)
    if not kursi:
        c.empty_state(
            "Belum ada kursi",
            "Tambahkan kursi melalui menu Data Kursi terlebih dahulu.",
            "💺",
        )
        return []

    id_valid = {
        row["id_kursi"]
        for row in kursi
        if row["status_aktif"] and not row["terisi"]
    }
    terpilih = [
        x for x in st.session_state.get("_booking_seats", []) if x in id_valid
    ]
    st.session_state["_booking_seats"] = terpilih

    # Denah 2 + lorong + 2, empat kursi per baris.
    for mulai in range(0, len(kursi), 4):
        baris = kursi[mulai: mulai + 4]
        kolom = st.columns([1, 1, 0.28, 1, 1])
        for urutan, kursi_item in enumerate(baris):
            posisi = urutan if urutan < 2 else urutan + 1
            with kolom[posisi]:
                id_kursi = kursi_item["id_kursi"]
                nomor = kursi_item["nomor_kursi"]
                sudah_dipilih = id_kursi in terpilih
                terisi = bool(kursi_item["terisi"])
                nonaktif = not kursi_item["status_aktif"]

                label = nomor
                if sudah_dipilih:
                    label = f"{nomor} ✓"
                elif terisi:
                    label = f"{nomor} · terisi"
                elif nonaktif:
                    label = f"{nomor} · off"

                if terisi:
                    bantuan = (
                        f"Dipesan oleh {kursi_item['nama_pelanggan']} "
                        f"({kursi_item['kode_pemesanan']}) pada jadwal ini."
                    )
                elif nonaktif:
                    bantuan = "Kursi sedang nonaktif dan tidak dapat dipilih."
                else:
                    bantuan = f"Pilih kursi {nomor}."

                st.button(
                    label,
                    key=f"seat_{id_rute}_{tanggal}_{jam}_{id_kursi}",
                    disabled=terisi or nonaktif,
                    type="primary" if sudah_dipilih else "secondary",
                    width="stretch",
                    help=bantuan,
                    on_click=_toggle_kursi,
                    args=(id_kursi,),
                )

    dengan_penumpang = [row for row in kursi if row["terisi"]]
    if dengan_penumpang:
        with st.expander("Lihat kursi yang sudah terisi pada jadwal ini"):
            for row in dengan_penumpang:
                st.markdown(
                    f"- **{c.esc(row['nomor_kursi'])}** — "
                    f"{c.esc(row['kode_pemesanan'])} · {c.esc(row['nama_pelanggan'])}"
                )

    terpilih = sorted(
        st.session_state.get("_booking_seats", []),
        key=lambda x: int(
            next(row["nomor_kursi"] for row in kursi if row["id_kursi"] == x)[1:]
        ),
    )
    return terpilih


def _render_ringkasan(
    pelanggan: dict | None,
    rute: dict | None,
    tanggal: str,
    jam: str,
    harga: int,
    terpilih: list[int],
    jadwal_valid: bool,
    kursi_data: list[dict],
) -> None:
    with st.container(border=True):
        st.markdown("#### Ringkasan pemesanan")
        if not pelanggan:
            st.caption("Pilih pelanggan terlebih dahulu.")
        if not rute:
            st.caption("Pilih rute dan jadwal.")
        if pelanggan and rute:
            st.markdown(
                f"""
                <div class="summary-line"><span>Pelanggan</span><b>{c.esc(pelanggan['nama_pelanggan'])}</b></div>
                <div class="summary-line"><span>Rute</span><b>{c.esc(rute['kota_asal'])} → {c.esc(rute['kota_tujuan'])}</b></div>
                <div class="summary-line"><span>Jadwal</span><b>{services.format_tanggal_singkat(tanggal)} · {services.format_jam(jam)}</b></div>
                <div class="summary-line"><span>Kursi dipilih</span><b>{len(terpilih)} kursi</b></div>
                """,
                unsafe_allow_html=True,
            )
        if terpilih:
            nomor = [
                row["nomor_kursi"] for row in kursi_data if row["id_kursi"] in terpilih
            ]
            st.markdown(
                "".join(f'<span class="seat-chip">{c.esc(n)}</span>' for n in nomor),
                unsafe_allow_html=True,
            )
        else:
            st.caption("Belum ada kursi yang dipilih.")

        jumlah = len(terpilih)
        total = services.hitung_total(harga, jumlah) if rute else 0
        st.markdown(
            f"""
            <div class="summary-line"><span>Harga per tiket</span><b>{services.format_rupiah(harga)}</b></div>
            <div class="summary-line"><span>Jumlah tiket</span><b>{jumlah}</b></div>
            <div class="nota-total" style="margin-top:.7rem">
                <span>TOTAL BAYAR</span><b>{services.format_rupiah(total)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        siap = bool(pelanggan and rute and terpilih and jadwal_valid)
        if st.button(
            "Konfirmasi Pemesanan",
            type="primary",
            width="stretch",
            disabled=not siap,
            key="konfirmasi_pemesanan",
        ):
            try:
                nota = services.buat_pemesanan(
                    pelanggan["id_pelanggan"],
                    rute["id_rute"],
                    tanggal,
                    jam,
                    terpilih,
                )
                st.session_state["_booking_seats"] = []
                st.session_state["_nota_id"] = nota["id_pemesanan"]
                c.set_flash(
                    "success",
                    f"Pemesanan {nota['kode_pemesanan']} berhasil. "
                    f"Kursi {nota['daftar_kursi']} tersimpan untuk "
                    f"{nota['nama_pelanggan']}.",
                )
                st.rerun()
            except services.AturanBisnisError as exc:
                st.error(str(exc))

        if not jadwal_valid:
            st.caption("Konfirmasi dinonaktifkan karena jadwal sudah terlewati.")
        elif not terpilih:
            st.caption("Pilih minimal satu kursi untuk melanjutkan.")
        st.caption(
            "Harga per tiket dikunci saat pemesanan disimpan (B09). "
            "Perubahan tarif rute setelahnya tidak mengubah nota ini."
        )


def render() -> None:
    c.hero(
        "TRANSAKSI",
        "Pemesanan Tiket",
        "Pilih pelanggan, rute, tanggal, dan jam keberangkatan. Sistem menampilkan "
        "kursi yang masih tersedia, menghitung total otomatis, lalu menyimpan nota.",
        chips=["F05–F08 · Pemesanan", "B05–B10 · Aturan transaksi", "Harga dikunci saat pesan"],
    )
    c.show_flash()
    _render_nota_sukses()

    pelanggan_list = _siapkan_pelanggan()
    rute_aktif = services.daftar_rute(hanya_aktif=True)

    kiri, kanan = st.columns([1.7, 1], gap="large")
    with kiri:
        pelanggan = _render_pelanggan(pelanggan_list)
        st.divider()
        rute, tanggal, jam, jadwal_valid = _render_jadwal(rute_aktif)

        terpilih: list[int] = []
        kursi_data: list[dict] = []
        if rute and jadwal_valid:
            st.divider()
            terpilih = _render_denah(rute["id_rute"], tanggal, jam)
            kursi_data = services.ambil_kursi_untuk_jadwal(
                rute["id_rute"], tanggal, jam
            )

    with kanan:
        _render_ringkasan(
            pelanggan,
            rute,
            tanggal,
            jam,
            int(rute["harga_tiket"]) if rute else 0,
            terpilih,
            jadwal_valid,
            kursi_data,
        )
        st.markdown(
            """
            <div class="panel" style="margin-top:1rem">
                <div class="panel-title">Alur yang dijalankan sistem</div>
                <div class="panel-note">
                    1. Validasi pelanggan terdaftar.<br>
                    2. Validasi rute aktif dan jadwal belum terlewati.<br>
                    3. Cek kursi pada rute + tanggal + jam yang sama.<br>
                    4. Hitung total = jumlah kursi × tarif.<br>
                    5. Simpan pemesanan dan detail kursi dalam satu transaksi.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Setelah tersimpan, nota dapat diunduh sebagai teks atau HTML untuk dicetak."
        )
