"""KOSPACE - Sistem Administrasi Pengelolaan Kos.

Jalankan dengan:  streamlit run app.py
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="KOSPACE · Administrasi Kos",
    page_icon=str(_ASSETS / "kospace-mark.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

_LOGO_B64 = base64.b64encode((_ASSETS / "kospace-logo.png").read_bytes()).decode("ascii")

from kospace import db, logic, ui  # noqa: E402
from kospace.views import (  # noqa: E402
    dashboard,
    kamar,
    pembayaran,
    pengaturan,
    penghuni,
    riwayat,
    sewa,
)

ICONS = {
    "Dashboard": "🏠",
    "Kamar": "🚪",
    "Penghuni": "👤",
    "Sewa": "📄",
    "Pembayaran": "💳",
    "Riwayat": "🕘",
    "Pengaturan": "⚙️",
}

PAGES = {
    "Dashboard": dashboard.render,
    "Kamar": kamar.render,
    "Penghuni": penghuni.render,
    "Sewa": sewa.render,
    "Pembayaran": pembayaran.render,
    "Riwayat": riwayat.render,
    "Pengaturan": pengaturan.render,
}


def _siapkan_navigasi() -> None:
    """Terapkan target navigasi sebelum widget radio dibuat."""
    target = st.session_state.pop("_nav_target", None)
    if target in PAGES:
        st.session_state["nav_radio"] = target
    if st.session_state.get("nav_radio") not in PAGES:
        st.session_state["nav_radio"] = "Dashboard"


def _sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="ks-brand">
              <div class="ks-brand-card">
                <img src="data:image/png;base64,{_LOGO_B64}" alt="KOSPACE" />
              </div>
              <div class="ks-brand-tag">Administrasi Kos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pilihan = st.radio(
            "Navigasi",
            list(PAGES),
            format_func=lambda p: f"{ICONS[p]}   {p}",
            label_visibility="collapsed",
            key="nav_radio",
        )

        st.markdown("<hr style='margin:14px 0 12px;'>", unsafe_allow_html=True)

        tersedia = db.scalar("SELECT COUNT(*) FROM kamar WHERE status = 'Tersedia'") or 0
        ditempati = db.scalar("SELECT COUNT(*) FROM kamar WHERE status = 'Ditempati'") or 0
        sewa_aktif = db.scalar("SELECT COUNT(*) FROM sewa WHERE status_sewa = 'Aktif'") or 0
        st.markdown(
            f"""
            <div class="ks-side-card">
              <div class="ks-side-label">Ringkasan kos</div>
              <div class="ks-side-row"><span>🟢 Tersedia</span><b>{tersedia}</b></div>
              <div class="ks-side-row"><span>🔵 Ditempati</span><b>{ditempati}</b></div>
              <div class="ks-side-row"><span>📄 Sewa aktif</span><b>{sewa_aktif}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="ks-owner">
              <div class="ks-owner-avatar">👩</div>
              <div>
                <div class="ks-owner-name">Pemilik Kos</div>
                <div class="ks-owner-role">Mode tanpa login</div>
              </div>
            </div>
            <div style="font-size:10px;color:#5eead4;letter-spacing:.4px;padding:8px 2px 2px;">
              KOSPACE v1.0 · SQLite · Streamlit
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div style='font-size:10px;color:#6ee7b7;padding-top:10px;'>📅 {ui.esc(ui.today_label())}</div>",
            unsafe_allow_html=True,
        )
    return pilihan


def main() -> None:
    logic.bootstrap()
    ui.inject_css()
    _siapkan_navigasi()
    pilihan = _sidebar()

    try:
        PAGES[pilihan]()
    except Exception as exc:  # tampilkan kesalahan dengan ramah
        st.error(
            "Terjadi kesalahan saat menampilkan halaman ini. "
            "Periksa pesan teknis di bawah, lalu muat ulang aplikasi."
        )
        with st.expander("Detail kesalahan", expanded=True):
            st.exception(exc)


if __name__ == "__main__":
    main()
else:
    # Streamlit menjalankan modul sebagai __main__, tetapi tetap aman bila diimpor.
    main()
