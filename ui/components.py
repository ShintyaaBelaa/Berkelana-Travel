"""Komponen tampilan bersama: CSS, hero, kartu metrik, dan nota."""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

import database
import services

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo-berkelana-transparent.png"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    """Kembalikan logo sebagai data URI agar bisa dipakai di HTML kustom."""
    try:
        data = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{data}"

HALAMAN = {
    "Dashboard": "📊",
    "Pemesanan Tiket": "🎫",
    "Riwayat Pemesanan": "🧾",
    "Data Pelanggan": "👥",
    "Data Rute & Tarif": "🛣️",
    "Data Kursi": "💺",
    "Panduan Sistem": "📘",
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --navy: #08366c;
            --navy-2: #0f4f91;
            --teal: #1f6fb8;
            --teal-soft: #e8f1fb;
            --azure: #5d9ed6;
            --amber: #f2b544;
            --amber-soft: #fff4dc;
            --ink: #102a43;
            --muted: #5d7189;
            --line: #dbe6f2;
            --paper: #f3f7fd;
            --white: #ffffff;
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', 'Segoe UI', Tahoma, sans-serif;
        }

        .stApp {
            background:
                radial-gradient(ellipse 55rem 38rem at 88% -8%, rgba(93, 158, 214, 0.26), transparent 62%),
                radial-gradient(ellipse 48rem 34rem at -8% 18%, rgba(8, 54, 108, 0.10), transparent 60%),
                radial-gradient(ellipse 42rem 30rem at 52% 108%, rgba(242, 181, 68, 0.10), transparent 62%),
                linear-gradient(rgba(8, 54, 108, 0.026) 1px, transparent 1px),
                linear-gradient(90deg, rgba(8, 54, 108, 0.026) 1px, transparent 1px),
                linear-gradient(180deg, #f8fbff 0%, #eef4fc 52%, #f7f9fd 100%);
            background-size: auto, auto, auto, 44px 44px, 44px 44px, auto;
            background-attachment: fixed;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 2.1rem;
            padding-bottom: 4rem;
        }

        #MainMenu, footer { visibility: hidden; }

        h1, h2, h3, h4 {
            color: var(--ink);
            letter-spacing: -0.025em;
        }

        p, li, label, .stMarkdown { color: var(--ink); }

        /* ---------------------------- SIDEBAR ---------------------------- */
        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 12% -4%, rgba(93, 158, 214, 0.38), transparent 17rem),
                radial-gradient(circle at 118% 42%, rgba(48, 111, 173, 0.34), transparent 20rem),
                radial-gradient(circle at 10% 105%, rgba(242, 181, 68, 0.13), transparent 14rem),
                linear-gradient(180deg, #072b57 0%, #083a70 55%, #06223f 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
            box-shadow: 18px 0 45px rgba(8, 54, 108, 0.08);
        }

        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 1.1rem;
        }

        .brand-box {
            padding: 0.4rem 0.35rem 1.1rem 0.35rem;
            border-bottom: 1px solid rgba(255,255,255,0.10);
            margin-bottom: 1rem;
        }

        .brand-logo-card {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #ffffff;
            border: 1px solid rgba(255,255,255,0.55);
            border-radius: 0.9rem;
            padding: 0.7rem 0.85rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 12px 30px rgba(2, 20, 42, 0.32);
        }

        .brand-logo-card img {
            display: block;
            width: 100%;
            max-width: 11.5rem;
            height: auto;
        }

        .brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.55rem;
            height: 2.55rem;
            border-radius: 0.85rem;
            background: var(--amber);
            color: #102a43;
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 0.65rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.22);
        }

        .brand-title {
            color: #ffffff;
            font-size: 1.02rem;
            font-weight: 800;
            letter-spacing: 0.09em;
            line-height: 1.2;
        }

        .brand-sub {
            color: rgba(255,255,255,0.58);
            font-size: 0.73rem;
            margin-top: 0.3rem;
            letter-spacing: 0.03em;
        }

        .nav-label {
            color: rgba(255,255,255,0.42);
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            padding: 0 0.45rem;
            margin: 0.2rem 0 0.45rem 0;
        }

        section[data-testid="stSidebar"] .stButton { margin-bottom: 0.1rem; }

        section[data-testid="stSidebar"] .stButton > button {
            width: 100%;
            justify-content: flex-start;
            text-align: left;
            border-radius: 0.62rem;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.055);
            color: #e8f1fb;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 0.55rem 0.8rem;
            transition: all 0.15s ease;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.12);
            border-color: rgba(255,255,255,0.18);
            color: #ffffff;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: var(--amber);
            border-color: var(--amber);
            color: #102a43;
            box-shadow: 0 6px 18px rgba(242,181,68,0.22);
        }

        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: #f7c568;
            border-color: #f7c568;
            color: #102a43;
        }

        .side-card {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 0.8rem;
            padding: 0.75rem 0.85rem;
            margin-top: 0.7rem;
        }

        .side-card-title {
            color: rgba(255,255,255,0.52);
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            margin-bottom: 0.55rem;
        }

        .side-stat {
            display: flex;
            justify-content: space-between;
            color: rgba(255,255,255,0.75);
            font-size: 0.73rem;
            padding: 0.18rem 0;
        }

        .side-stat b { color: #ffffff; font-weight: 700; }

        .side-footer {
            color: rgba(255,255,255,0.35);
            font-size: 0.64rem;
            line-height: 1.5;
            padding: 0.9rem 0.35rem 0.4rem;
            border-top: 1px solid rgba(255,255,255,0.08);
            margin-top: 1rem;
        }

        /* ----------------------------- HERO ------------------------------ */
        .hero {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.6rem;
            border-radius: 1.15rem;
            padding: 1.55rem 1.8rem 1.45rem;
            margin-bottom: 1.35rem;
            color: #ffffff;
            background:
                radial-gradient(circle at 88% 6%, rgba(93, 158, 214, 0.45), transparent 20rem),
                radial-gradient(circle at 8% 100%, rgba(242, 181, 68, 0.20), transparent 16rem),
                linear-gradient(115deg, #062a54 0%, #0b4682 58%, #2f7cc0 100%);
            box-shadow: 0 16px 38px rgba(8, 54, 108, 0.22);
        }

        .hero-copy {
            position: relative;
            z-index: 1;
            min-width: 0;
        }

        .hero-logo {
            position: relative;
            z-index: 1;
            flex: 0 0 auto;
            width: 10.6rem;
            padding: 0.65rem 0.8rem;
            border-radius: 0.9rem;
            background: rgba(255, 255, 255, 0.97);
            box-shadow: 0 14px 34px rgba(2, 20, 42, 0.28);
        }

        .hero-logo img {
            display: block;
            width: 100%;
            height: auto;
        }

        .hero::after {
            content: "";
            position: absolute;
            right: -4rem;
            bottom: -5.5rem;
            width: 15rem;
            height: 15rem;
            border: 1.4rem solid rgba(255,255,255,0.055);
            border-radius: 50%;
        }

        .hero-kicker {
            color: var(--amber);
            font-size: 0.66rem;
            font-weight: 800;
            letter-spacing: 0.17em;
            margin-bottom: 0.5rem;
        }

        .hero h1 {
            color: #ffffff;
            font-size: 1.72rem;
            line-height: 1.16;
            margin: 0 0 0.45rem 0;
            font-weight: 800;
        }

        .hero p {
            color: rgba(255,255,255,0.72);
            font-size: 0.87rem;
            line-height: 1.6;
            max-width: 48rem;
            margin: 0;
        }

        .hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.95rem;
        }

        .hero-chip {
            display: inline-block;
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.12);
            color: rgba(255,255,255,0.82);
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 600;
            padding: 0.24rem 0.62rem;
        }

        /* ---------------------------- CARDS ------------------------------ */
        .metric-card {
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 0.95rem;
            padding: 1rem 1.05rem;
            min-height: 6.7rem;
            box-shadow: 0 3px 12px rgba(13,43,54,0.035);
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: "";
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 0.27rem;
            background: var(--teal);
        }

        .metric-card.amber::before { background: var(--amber); }
        .metric-card.navy::before { background: var(--navy-2); }
        .metric-card.rose::before { background: #c86565; }

        .metric-label {
            color: var(--muted);
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .metric-value {
            color: var(--ink);
            font-size: 1.58rem;
            line-height: 1.2;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-top: 0.4rem;
        }

        .metric-sub {
            color: var(--muted);
            font-size: 0.7rem;
            margin-top: 0.3rem;
        }

        .section-head {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.7rem 0 0.7rem;
        }

        .section-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.02em;
        }

        .section-sub {
            color: var(--muted);
            font-size: 0.76rem;
            margin-top: 0.18rem;
        }

        .panel {
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 0.95rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 3px 12px rgba(13,43,54,0.03);
        }

        .panel-title {
            font-size: 0.83rem;
            font-weight: 800;
            color: var(--ink);
            margin-bottom: 0.55rem;
        }

        .panel-note {
            color: var(--muted);
            font-size: 0.73rem;
            line-height: 1.55;
        }

        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            white-space: nowrap;
        }

        .badge-green { background: #e5f5ef; color: #0c6b55; }
        .badge-gray  { background: #edf0f1; color: #5d7189; }
        .badge-amber { background: var(--amber-soft); color: #8c5b05; }
        .badge-red   { background: #fbeaea; color: #a33a3a; }
        .badge-teal  { background: var(--teal-soft); color: #1f6fb8; }

        .empty-state {
            background: var(--white);
            border: 1.5px dashed #cfdded;
            border-radius: 0.95rem;
            padding: 2rem 1.4rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.82rem;
        }

        .empty-state .es-icon { font-size: 1.55rem; margin-bottom: 0.4rem; }
        .empty-state b { color: var(--ink); }

        .info-strip {
            border-radius: 0.8rem;
            border: 1px solid #f0d9a8;
            background: #fff9ec;
            padding: 0.7rem 0.9rem;
            color: #7b5a12;
            font-size: 0.75rem;
            line-height: 1.55;
        }

        .step-label {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
            font-weight: 800;
            color: var(--ink);
            margin: 0.7rem 0 0.45rem;
        }

        .step-num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 0.48rem;
            background: var(--navy);
            color: #ffffff;
            font-size: 0.72rem;
            font-weight: 800;
        }

        .seat-legend {
            display: flex;
            gap: 0.9rem;
            flex-wrap: wrap;
            margin: 0.25rem 0 0.8rem;
            color: var(--muted);
            font-size: 0.7rem;
        }

        .legend-dot {
            width: 0.62rem;
            height: 0.62rem;
            border-radius: 0.18rem;
            display: inline-block;
            margin-right: 0.3rem;
            vertical-align: -0.05rem;
        }

        .legend-available { background: #ffffff; border: 1px solid #9db6cf; }
        .legend-selected { background: var(--teal); }
        .legend-booked { background: #c9d2d3; }
        .legend-inactive { background: #efe7dc; border: 1px dashed #b9a58b; }

        .mini-label {
            color: var(--muted);
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .big-number {
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.03em;
        }

        .summary-line {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            font-size: 0.78rem;
            padding: 0.33rem 0;
            border-bottom: 1px dashed #e5eae9;
        }

        .summary-line:last-child { border-bottom: none; }
        .summary-line span { color: var(--muted); }
        .summary-line b { color: var(--ink); text-align: right; }

        .seat-chip {
            display: inline-block;
            background: var(--teal-soft);
            color: #12558f;
            border: 1px solid #c3dbf2;
            padding: 0.2rem 0.52rem;
            border-radius: 0.42rem;
            font-size: 0.72rem;
            font-weight: 700;
            margin: 0.12rem 0.12rem 0.12rem 0;
        }

        .seat-master-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(7.2rem, 1fr));
            gap: 0.65rem;
            margin-bottom: 0.4rem;
        }

        .seat-master {
            background: #ffffff;
            border: 1px solid var(--line);
            border-top: 0.22rem solid var(--teal);
            border-radius: 0.7rem;
            padding: 0.7rem 0.55rem 0.6rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(13,43,54,0.03);
        }

        .seat-master.off {
            border-top-color: #c7b299;
            background: #fbf9f5;
        }

        .seat-nomor {
            font-size: 1.12rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
        }

        .seat-meta {
            color: var(--muted);
            font-size: 0.64rem;
            margin-top: 0.35rem;
        }

        /* ----------------------------- NOTA ------------------------------ */
        .nota {
            background: #ffffff;
            border-radius: 1rem;
            border: 1px solid #d9e4f0;
            box-shadow: 0 18px 45px rgba(13,43,54,0.12);
            overflow: hidden;
            max-width: 46rem;
            margin-bottom: 1rem;
        }

        .nota-head {
            background:
                radial-gradient(circle at 88% 0%, rgba(93, 158, 214, 0.45), transparent 16rem),
                linear-gradient(115deg, #062a54, #0b4682 62%, #2f7cc0);
            color: #ffffff;
            padding: 1.2rem 1.4rem;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .nota-brand-row {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .nota-logo {
            display: block;
            width: 7.6rem;
            height: auto;
            background: #ffffff;
            border-radius: 0.55rem;
            padding: 0.3rem 0.45rem;
        }

        .nota-brand {
            font-size: 1.02rem;
            font-weight: 800;
            letter-spacing: 0.1em;
        }

        .nota-brand-sub {
            font-size: 0.68rem;
            color: rgba(255,255,255,0.62);
            margin-top: 0.22rem;
        }

        .nota-code {
            text-align: right;
            font-size: 1.06rem;
            font-weight: 800;
            color: var(--amber);
            letter-spacing: 0.05em;
        }

        .nota-code span {
            display: block;
            font-size: 0.58rem;
            color: rgba(255,255,255,0.6);
            letter-spacing: 0.15em;
            margin-top: 0.15rem;
            font-weight: 600;
        }

        .nota-body { padding: 1.2rem 1.4rem 0.5rem; }

        .nota-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.8rem 1.5rem;
            margin-bottom: 1rem;
        }

        .nota-field-label {
            color: var(--muted);
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        .nota-field-value {
            color: var(--ink);
            font-size: 0.82rem;
            font-weight: 600;
            margin-top: 0.12rem;
            line-height: 1.4;
        }

        .nota-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
            margin: 0.4rem 0 0.9rem;
        }

        .nota-table th {
            text-align: left;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--muted);
            border-bottom: 1px solid var(--line);
            padding: 0.45rem 0.3rem;
        }

        .nota-table td {
            padding: 0.55rem 0.3rem;
            border-bottom: 1px solid #eef3f9;
            color: var(--ink);
        }

        .nota-total {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f0f6fd;
            border: 1px solid #d7e6f5;
            border-radius: 0.7rem;
            padding: 0.75rem 0.95rem;
            margin: 0.5rem 0 1rem;
        }

        .nota-total span { font-size: 0.72rem; color: #4a6580; font-weight: 700; }
        .nota-total b { font-size: 1.3rem; color: #12558f; letter-spacing: -0.03em; }

        .nota-foot {
            border-top: 1px dashed #d9e4f0;
            padding: 0.8rem 1.4rem 1rem;
            color: var(--muted);
            font-size: 0.65rem;
            line-height: 1.55;
        }

        /* --------------------------- DATAFRAME --------------------------- */
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 0.8rem;
            overflow: hidden;
        }

        /* --------------------------- FORM/WIDGET ------------------------- */
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 0.95rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 3px 12px rgba(13,43,54,0.03);
        }

        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 0.8rem;
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            font-weight: 700;
            font-size: 0.82rem;
            color: var(--ink);
        }

        .stButton > button {
            border-radius: 0.58rem;
            font-weight: 700;
            font-size: 0.82rem;
            border: 1px solid #cfdded;
            transition: all 0.12s ease;
        }

        .stButton > button[kind="primary"] {
            background: var(--teal);
            border-color: var(--teal);
            color: #ffffff;
        }

        .stButton > button[kind="primary"]:hover {
            background: #12558f;
            border-color: #12558f;
            color: #ffffff;
        }

        .stButton > button:disabled {
            background: #eef2f7;
            border-color: #dfe7f0;
            color: #97a6b6;
        }

        div[data-testid="stAlert"] {
            border-radius: 0.7rem;
            font-size: 0.8rem;
        }

        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"], .stTimeInput input {
            border-radius: 0.55rem !important;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 0.8rem;
            padding: 0.8rem 0.9rem;
        }

        @media (max-width: 780px) {
            .hero { padding: 1.2rem 1.15rem; }
            .hero h1 { font-size: 1.34rem; }
            .hero-logo { display: none; }
            .metric-card { min-height: 5.9rem; }
            .nota-grid { grid-template-columns: 1fr; }
            .nota-head { flex-direction: column; }
            .nota-code { text-align: left; }
            .nota-logo { width: 92px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KOMPONEN
# ---------------------------------------------------------------------------

def esc(value) -> str:
    return html.escape(str(value if value is not None else "-"))


def hero(kicker: str, judul: str, deskripsi: str, chips: list[str] | None = None) -> None:
    chip_html = ""
    if chips:
        chip_html = (
            '<div class="hero-meta">'
            + "".join(f'<span class="hero-chip">{esc(chip)}</span>' for chip in chips)
            + "</div>"
        )
    logo = logo_data_uri()
    logo_html = (
        f'<div class="hero-logo"><img src="{logo}" alt="Logo Berkelana Travel"></div>'
        if logo
        else ""
    )
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-copy">
                <div class="hero-kicker">{esc(kicker)}</div>
                <h1>{esc(judul)}</h1>
                <p>{esc(deskripsi)}</p>
                {chip_html}
            </div>
            {logo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    sub: str = "",
    ikon: str = "•",
    warna: str = "teal",
) -> None:
    st.markdown(
        f"""
        <div class="metric-card {esc(warna)}">
            <div class="metric-label">{esc(ikon)} {esc(label)}</div>
            <div class="metric-value">{esc(value)}</div>
            <div class="metric-sub">{esc(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(judul: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <div>
                <div class="section-title">{esc(judul)}</div>
                <div class="section-sub">{esc(sub)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def panel(judul: str, isi_html: str) -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{esc(judul)}</div>
            <div class="panel-note">{isi_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(teks: str, warna: str = "gray") -> str:
    return f'<span class="badge badge-{esc(warna)}">{esc(teks)}</span>'


def step_label(nomor: int, judul: str) -> None:
    st.markdown(
        f'<div class="step-label"><span class="step-num">{nomor}</span>{esc(judul)}</div>',
        unsafe_allow_html=True,
    )


def empty_state(judul: str, pesan: str, ikon: str = "🗂️") -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="es-icon">{esc(ikon)}</div>
            <b>{esc(judul)}</b><br>{esc(pesan)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_strip(teks: str) -> None:
    st.markdown(f'<div class="info-strip">{teks}</div>', unsafe_allow_html=True)


def set_flash(jenis: str, pesan: str) -> None:
    """Simpan pesan agar tetap tampil setelah st.rerun()."""
    st.session_state["_flash"] = (jenis, pesan)


def show_flash() -> None:
    data = st.session_state.pop("_flash", None)
    if not data:
        return
    jenis, pesan = data
    if jenis == "success":
        st.success(pesan)
    elif jenis == "error":
        st.error(pesan)
    elif jenis == "warning":
        st.warning(pesan)
    else:
        st.info(pesan)


def go_to(halaman: str) -> None:
    st.session_state["halaman"] = halaman
    st.rerun()


# ---------------------------------------------------------------------------
# NOTA
# ---------------------------------------------------------------------------

def nota_sebagai_teks(nota: dict) -> str:
    garis = "=" * 52
    tipis = "-" * 52
    kursi = ", ".join(nota.get("nomor_kursi", [])) or "-"
    return "\n".join(
        [
            garis,
            "             BERKELANA TRAVEL",
            "       Sistem Administrasi Perjalanan",
            garis,
            f"Kode Pemesanan : {nota.get('kode_pemesanan', '-')}",
            f"Dicetak        : {database.format_waktu_lokal()}",
            tipis,
            "DATA PELANGGAN",
            f"Kode           : {nota.get('kode_pelanggan', '-')}",
            f"Nama           : {nota.get('nama_pelanggan', '-')}",
            f"Telepon        : {nota.get('nomor_telepon', '-')}",
            tipis,
            "DETAIL PERJALANAN",
            (f"Rute           : {nota.get('kode_rute', '-')} "
            f"({nota.get('kota_asal', '-')} - {nota.get('kota_tujuan', '-')})"),
            f"Keberangkatan  : {services.format_tanggal_indo(nota.get('tanggal_keberangkatan'))}",
            f"Jam            : {services.format_jam(nota.get('jam_keberangkatan'))}",
            f"Kursi          : {kursi}",
            tipis,
            f"Jumlah Tiket   : {nota.get('jumlah_pesan_tiket', 0)}",
            f"Harga/Tiket    : {services.format_rupiah(nota.get('harga_per_tiket'))}",
            f"TOTAL BAYAR    : {services.format_rupiah(nota.get('total_harga'))}",
            garis,
            "Simpan nota ini sebagai bukti pemesanan.",
            "Pembatalan dapat dilakukan melalui petugas loket.",
            "Pengembalian dana dilakukan di luar sistem.",
            garis,
        ]
    )


def _nota_isi_html(nota: dict) -> str:
    detail_rows = "".join(
        f"""
        <tr>
            <td><b>{esc(item.get("nomor_kursi"))}</b></td>
            <td>Kursi penumpang</td>
            <td style="text-align:right">{esc(services.format_rupiah(item.get("harga_saat_pemesanan")))}</td>
        </tr>
        """
        for item in nota.get("detail_kursi", [])
    )
    logo = logo_data_uri()
    logo_html = (
        f'<img class="nota-logo" src="{logo}" alt="Logo Berkelana Travel">' if logo else ""
    )
    return f"""
        <div class="nota-head">
            <div class="nota-brand-row">
                {logo_html}
                <div>
                    <div class="nota-brand">BERKELANA TRAVEL</div>
                    <div class="nota-brand-sub">Sistem Administrasi Perjalanan · Nota Pemesanan</div>
                </div>
            </div>
            <div class="nota-code">
                {esc(nota.get("kode_pemesanan"))}
                <span>BUKTI PEMESANAN</span>
            </div>
        </div>
        <div class="nota-body">
            <div class="nota-grid">
                <div>
                    <div class="nota-field-label">Pelanggan</div>
                    <div class="nota-field-value">{esc(nota.get("nama_pelanggan"))} ({esc(nota.get("kode_pelanggan"))})</div>
                </div>
                <div>
                    <div class="nota-field-label">Nomor Telepon</div>
                    <div class="nota-field-value">{esc(nota.get("nomor_telepon"))}</div>
                </div>
                <div>
                    <div class="nota-field-label">Rute</div>
                    <div class="nota-field-value">{esc(nota.get("kota_asal"))} → {esc(nota.get("kota_tujuan"))} · {esc(nota.get("kode_rute"))}</div>
                </div>
                <div>
                    <div class="nota-field-label">Keberangkatan</div>
                    <div class="nota-field-value">{esc(services.format_tanggal_indo(nota.get("tanggal_keberangkatan")))} · {esc(services.format_jam(nota.get("jam_keberangkatan")))}</div>
                </div>
            </div>
            <table class="nota-table">
                <thead><tr><th>Kursi</th><th>Keterangan</th><th style="text-align:right">Harga</th></tr></thead>
                <tbody>{detail_rows}</tbody>
            </table>
            <div class="nota-total">
                <span>{esc(nota.get("jumlah_pesan_tiket", 0))} tiket × {esc(services.format_rupiah(nota.get("harga_per_tiket")))}</span>
                <b>{esc(services.format_rupiah(nota.get("total_harga")))}</b>
            </div>
        </div>
        <div class="nota-foot">
            Nota dibuat otomatis oleh Sistem Administrasi Travel Berkelana pada
            {esc(database.format_waktu_lokal())}. Simpan nota ini sebagai bukti pemesanan.
            Pembatalan dilakukan melalui petugas loket; pengembalian dana di luar sistem.
        </div>
    """


def render_nota(nota: dict) -> None:
    st.markdown(f'<div class="nota">{_nota_isi_html(nota)}</div>', unsafe_allow_html=True)


def nota_html_dokumen(nota: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nota {esc(nota.get('kode_pemesanan'))} - Berkelana Travel</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f3f7fd; color: #102a43; padding: 32px; }}
    .nota {{ max-width: 720px; margin: 0 auto; background: #fff; border: 1px solid #d9e4f0; border-radius: 14px; overflow: hidden; box-shadow: 0 18px 45px rgba(13,43,54,.12); }}
    .nota-head {{ background: linear-gradient(115deg,#08366c,#1f6fb8); color: #fff; padding: 22px 26px; display: flex; justify-content: space-between; gap: 18px; }}
    .nota-brand-row {{ display: flex; align-items: center; gap: 12px; }}
    .nota-logo {{ display: block; width: 116px; height: auto; background: #fff; border-radius: 8px; padding: 5px 7px; }}
    .nota-brand {{ font-size: 17px; font-weight: 800; letter-spacing: .1em; }}
    .nota-brand-sub {{ font-size: 11px; color: rgba(255,255,255,.62); margin-top: 3px; }}
    .nota-code {{ text-align: right; font-size: 18px; font-weight: 800; color: #f2b544; letter-spacing: .05em; }}
    .nota-code span {{ display: block; font-size: 9px; color: rgba(255,255,255,.6); letter-spacing: .15em; margin-top: 2px; }}
    .nota-body {{ padding: 22px 26px 6px; }}
    .nota-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px 26px; margin-bottom: 18px; }}
    .nota-field-label {{ color: #5d7189; font-size: 10px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
    .nota-field-value {{ font-size: 13px; font-weight: 600; margin-top: 2px; line-height: 1.4; }}
    .nota-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 8px 0 14px; }}
    .nota-table th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #5d7189; border-bottom: 1px solid #dde7f2; padding: 7px 5px; }}
    .nota-table td {{ padding: 9px 5px; border-bottom: 1px solid #eef3f9; }}
    .nota-total {{ display: flex; justify-content: space-between; align-items: center; background: #f0f6fd; border: 1px solid #d7e6f5; border-radius: 11px; padding: 12px 15px; margin: 8px 0 16px; }}
    .nota-total span {{ font-size: 12px; color: #4a6580; font-weight: 700; }}
    .nota-total b {{ font-size: 21px; color: #12558f; }}
    .nota-foot {{ border-top: 1px dashed #d9e4f0; padding: 14px 26px 18px; color: #5d7189; font-size: 10px; line-height: 1.55; }}
    @media print {{ body {{ background: #fff; padding: 0; }} .nota {{ box-shadow: none; }} }}
</style>
</head>
<body>
<div class="nota">{_nota_isi_html(nota)}</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

def render_sidebar(halaman_aktif: str) -> None:
    logo = logo_data_uri()
    brand_logo = (
        f'<div class="brand-logo-card"><img src="{logo}" alt="Logo Berkelana Travel"></div>'
        if logo
        else '<div class="brand-mark">B</div>'
    )
    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand-box">
                {brand_logo}
                <div class="brand-title">BERKELANA TRAVEL</div>
                <div class="brand-sub">Sistem Administrasi Perjalanan</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="nav-label">MENU UTAMA</div>', unsafe_allow_html=True)
        for nama, ikon in HALAMAN.items():
            if st.button(
                f"{ikon}  {nama}",
                key=f"nav_{nama}",
                type="primary" if nama == halaman_aktif else "secondary",
                width="stretch",
            ):
                go_to(nama)

        try:
            data = services.info_ringkas_data()
            info = database.info_database()
            st.markdown(
                f"""
                <div class="side-card">
                    <div class="side-card-title">RINGKASAN DATA</div>
                    <div class="side-stat"><span>Pelanggan</span><b>{data['pelanggan']}</b></div>
                    <div class="side-stat"><span>Rute</span><b>{data['rute']}</b></div>
                    <div class="side-stat"><span>Kursi</span><b>{data['kursi']}</b></div>
                    <div class="side-stat"><span>Pemesanan</span><b>{data['pemesanan']}</b></div>
                </div>
                <div class="side-footer">
                    🗄️ {esc(info['nama_file'])} · {info['ukuran_kb']} KB<br>
                    SQLite lokal · Tanpa login · v1.0.0<br>
                    Sistem berjalan di komputer petugas loket.
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception:  # noqa: BLE001 - sidebar must stay usable if DB is unavailable
            st.markdown(
                '<div class="side-footer">Database belum siap.</div>',
                unsafe_allow_html=True,
            )
