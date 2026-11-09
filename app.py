"""
app.py
=================
Titik masuk Sistem Administrasi Travel Berkelana.

Jalankan dengan:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import database
from ui import components as c
from ui import dashboard, kursi, panduan, pelanggan, pemesanan, riwayat, rute

LOGO_MARK = Path(__file__).resolve().parent / "assets" / "logo-mark.png"

st.set_page_config(
    page_title="Berkelana Travel · Sistem Administrasi",
    page_icon=str(LOGO_MARK) if LOGO_MARK.exists() else "🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def siapkan_database() -> bool:
    """Membuat skema dan data contoh satu kali per proses aplikasi."""
    database.init_db()
    return True


PAGES = {
    "Dashboard": dashboard.render,
    "Pemesanan Tiket": pemesanan.render,
    "Riwayat Pemesanan": riwayat.render,
    "Data Pelanggan": pelanggan.render,
    "Data Rute & Tarif": rute.render,
    "Data Kursi": kursi.render,
    "Panduan Sistem": panduan.render,
}


def main() -> None:
    c.inject_css()

    try:
        siapkan_database()
    except Exception as exc:  # noqa: BLE001 - pesan ramah untuk kegagalan database
        st.error(
            "Database tidak dapat disiapkan. Pastikan folder proyek dapat ditulis dan "
            f"file database tidak sedang dikunci aplikasi lain.\n\nDetail: {exc}"
        )
        st.stop()

    if st.session_state.get("halaman") not in PAGES:
        st.session_state["halaman"] = "Dashboard"

    halaman = st.session_state["halaman"]
    c.render_sidebar(halaman)

    try:
        PAGES[halaman]()
    except Exception as exc:  # noqa: BLE001 - tetap tampilkan konteks kesalahan
        st.error(
            "Terjadi kesalahan saat menampilkan halaman. Data yang sudah tersimpan "
            "di SQLite tidak terpengaruh."
        )
        with st.expander("Detail teknis untuk pemeriksaan"):
            st.exception(exc)

    st.markdown(
        """
        <div style="margin-top:2.2rem;padding-top:.9rem;border-top:1px solid #dde7f2;
                    display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;
                    color:#7d90a6;font-size:.68rem;">
            <span>BERKELANA TRAVEL · Sistem Administrasi Perjalanan</span>
            <span>Python · Streamlit · SQLite · v1.0.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
