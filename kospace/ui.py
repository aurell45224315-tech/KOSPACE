"""KOSPACE - Komponen tampilan bersama, CSS, dan utilitas format."""

from __future__ import annotations

import html
import textwrap
from datetime import date, datetime

import streamlit as st

from . import logic

# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
def rupiah(value) -> str:
    try:
        angka = int(round(float(value or 0)))
    except (TypeError, ValueError):
        angka = 0
    return "Rp" + f"{angka:,}".replace(",", ".")


def fmt_date(value) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    try:
        return datetime.fromisoformat(str(value)[:10]).strftime("%d-%m-%Y")
    except ValueError:
        return str(value)


def fmt_datetime(value) -> str:
    if value in (None, ""):
        return "-"
    try:
        return datetime.fromisoformat(str(value)[:19]).strftime("%d-%m-%Y %H:%M")
    except ValueError:
        return str(value)


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def today_label() -> str:
    return logic.today_label()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_CSS = """
<style>
:root {
  --ks-ink: #0f172a;
  --ks-muted: #64748b;
  --ks-line: #e2e8f0;
  --ks-teal: #0e7490;
  --ks-teal-dark: #155e75;
  --ks-soft: #f1f5f9;
}
html, body, [class*="st-"] {
  font-family: "Segoe UI", "Inter", system-ui, -apple-system, sans-serif;
}
.stApp {
  background:
    radial-gradient(1200px 420px at 15% -10%, rgba(14,116,144,.08), transparent 60%),
    radial-gradient(900px 380px at 95% 0%, rgba(5,150,105,.07), transparent 55%),
    #f6f9f8;
}
.block-container {max-width: 1280px; padding-top: 1.5rem; padding-bottom: 4rem;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stToolbar"] {right: 0.6rem;}

/* Sidebar */
[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at 18% 0%, #0f766e 0%, transparent 42%),
    linear-gradient(180deg, #073b38 0%, #062b29 60%, #041f1e 100%);
  border-right: 1px solid rgba(255,255,255,.06);
}
[data-testid="stSidebar"] > div:first-child {padding-top: 1.2rem;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color: #d1fae5;}
[data-testid="stSidebar"] .stRadio > label {display: none;}
[data-testid="stSidebar"] .stRadio label p {
  color: #d6f5ee !important; font-weight: 600 !important; font-size: 14px !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {gap: 4px;}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
  padding: 8px 10px; border-radius: 11px; transition: background .15s ease;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
  background: rgba(255,255,255,.07);
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
  background: rgba(45,212,191,.16);
  box-shadow: inset 0 0 0 1px rgba(94,234,212,.25);
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) p {
  color: #ffffff !important;
}
[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,.10);}

/* Brand */
.ks-brand {padding:2px 2px 18px; text-align:center;}
.ks-brand-card {
  background:#fff; border-radius:16px; padding:14px 18px;
  display:flex; align-items:center; justify-content:center;
  box-shadow: 0 12px 26px rgba(0,0,0,.28);
}
.ks-brand-card img {width:100%; max-width:190px; height:auto; display:block;}
.ks-brand-tag {font-size:9px; letter-spacing:2.2px; text-transform:uppercase; color:#99f6e4; margin-top:10px;}

/* Sidebar mini cards */
.ks-side-card {
  background: rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.09);
  border-radius:14px; padding:12px 13px; margin: 4px 0 10px;
}
.ks-side-label {font-size:10px; letter-spacing:1.2px; text-transform:uppercase; color:#99f6e4;}
.ks-side-value {font-size:20px; font-weight:800; color:#fff; margin-top:2px;}
.ks-side-row {display:flex; align-items:center; justify-content:space-between; padding:4px 0; font-size:12px; color:#a7f3d0;}
.ks-side-row b {color:#fff; font-size:13px;}
.ks-owner {display:flex; align-items:center; gap:10px; padding:10px 2px 4px;}
.ks-owner-avatar {
  width:36px; height:36px; border-radius:50%; background: linear-gradient(135deg,#fbbf24,#f59e0b);
  display:flex; align-items:center; justify-content:center; font-size:17px; color:#422006;
}
.ks-owner-name {font-size:13px; font-weight:700; color:#fff; line-height:1.1;}
.ks-owner-role {font-size:10px; color:#99f6e4; letter-spacing:.4px;}

/* Header */
.ks-header {
  display:flex; justify-content:space-between; align-items:flex-end; gap:18px;
  margin: 2px 0 22px; padding-bottom: 16px; border-bottom: 1px solid var(--ks-line);
  flex-wrap: wrap;
}
.ks-eyebrow {font-size:10px; font-weight:800; letter-spacing:2px; color:#0e7490; text-transform:uppercase;}
.ks-header h1 {font-size:30px; font-weight:800; color:#0f172a; margin:3px 0 4px; letter-spacing:-.7px;}
.ks-header p {margin:0; color:#64748b; font-size:14px;}
.ks-header-right {text-align:right; color:#64748b; font-size:12px;}
.ks-date-chip {
  display:inline-flex; align-items:center; gap:8px; background:#fff; border:1px solid var(--ks-line);
  border-radius:999px; padding:8px 14px; font-size:12px; font-weight:600; color:#334155;
  box-shadow: 0 6px 18px rgba(15,23,42,.04);
}

/* Section headings */
.ks-section {display:flex; justify-content:space-between; align-items:flex-end; gap:12px; margin: 6px 0 10px;}
.ks-section h3 {margin:0; font-size:16px; font-weight:800; color:#0f172a; letter-spacing:-.2px;}
.ks-section p {margin:2px 0 0; font-size:12px; color:#64748b;}
.ks-section-right {font-size:12px; color:#64748b;}

/* Hero */
.ks-hero {
  position:relative; overflow:hidden; border-radius:22px; padding:24px 28px;
  background: linear-gradient(120deg, #0f766e 0%, #0e7490 55%, #155e75 100%);
  color:#fff; box-shadow: 0 18px 40px rgba(13,116,144,.22); margin-bottom:18px;
}
.ks-hero:after {
  content:""; position:absolute; width:320px; height:320px; border-radius:50%;
  background: rgba(255,255,255,.07); right:-90px; top:-150px;
}
.ks-hero:before {
  content:""; position:absolute; width:180px; height:180px; border-radius:50%;
  background: rgba(45,212,191,.13); right:80px; bottom:-120px;
}
.ks-hero-grid {display:flex; justify-content:space-between; gap:26px; align-items:center; flex-wrap:wrap; position:relative; z-index:1;}
.ks-hero-eyebrow {font-size:10px; letter-spacing:2px; text-transform:uppercase; color:#a7f3d0; font-weight:800;}
.ks-hero-title {font-size:25px; font-weight:800; letter-spacing:-.5px; margin:5px 0 3px;}
.ks-hero-sub {font-size:13px; color:#d1fae5; max-width:620px;}
.ks-hero-ring {text-align:center; min-width:130px;}
.ks-hero-pct {font-size:36px; font-weight:800; line-height:1; letter-spacing:-1px;}
.ks-hero-pct span {font-size:16px; font-weight:600; color:#a7f3d0;}
.ks-hero-ring-label {font-size:10px; letter-spacing:1.4px; text-transform:uppercase; color:#a7f3d0; margin-top:5px;}
.ks-hero-bar {height:7px; border-radius:999px; background:rgba(255,255,255,.18); margin-top:10px; overflow:hidden;}
.ks-hero-bar > div {height:100%; border-radius:999px; background:linear-gradient(90deg,#5eead4,#fbbf24);}

/* Stat cards */
.ks-stat {
  position:relative; overflow:hidden; background:#fff; border:1px solid #e6edf0;
  border-radius:17px; padding:15px 17px; height:100%;
  box-shadow: 0 8px 24px rgba(15,23,42,.035);
}
.ks-stat:before {content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--tone, #0e7490);}
.ks-stat-top {display:flex; align-items:center; gap:9px;}
.ks-stat-icon {
  width:31px; height:31px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background: var(--soft, #ecfeff); font-size:15px;
}
.ks-stat-label {font-size:10px; font-weight:800; letter-spacing:.9px; text-transform:uppercase; color:#64748b; line-height:1.25;}
.ks-stat-value {font-size:25px; font-weight:800; color:#0f172a; letter-spacing:-.6px; margin-top:10px; line-height:1.1;}
.ks-stat-sub {font-size:11px; color:#64748b; margin-top:4px; line-height:1.3;}
.ks-teal {--tone:#0e7490; --soft:#ecfeff;}
.ks-green {--tone:#059669; --soft:#ecfdf5;}
.ks-amber {--tone:#d97706; --soft:#fffbeb;}
.ks-rose {--tone:#e11d48; --soft:#fff1f2;}
.ks-indigo {--tone:#4f46e5; --soft:#eef2ff;}
.ks-slate {--tone:#475569; --soft:#f1f5f9;}

/* Badges */
.ks-badge {
  display:inline-flex; align-items:center; gap:5px; padding:4px 10px; border-radius:999px;
  font-size:10.5px; font-weight:800; line-height:1.25; letter-spacing:.2px;
  border:1px solid transparent; white-space:nowrap;
}
.ks-b-green {background:#ecfdf5; color:#047857; border-color:#a7f3d0;}
.ks-b-teal {background:#ecfeff; color:#0e7490; border-color:#a5f3fc;}
.ks-b-amber {background:#fffbeb; color:#b45309; border-color:#fde68a;}
.ks-b-rose {background:#fff1f2; color:#be123c; border-color:#fecdd3;}
.ks-b-slate {background:#f1f5f9; color:#475569; border-color:#e2e8f0;}
.ks-b-indigo {background:#eef2ff; color:#4338ca; border-color:#c7d2fe;}

/* Panels */
.ks-panel {
  background:#fff; border:1px solid #e6edf0; border-radius:16px; padding:16px 18px;
  box-shadow: 0 8px 24px rgba(15,23,42,.03); height:100%;
}
.ks-panel-title {font-size:14px; font-weight:800; color:#0f172a; margin-bottom:2px;}
.ks-panel-sub {font-size:11px; color:#64748b; margin-bottom:10px;}

/* Detail grid */
.ks-kv {display:grid; gap:10px 18px;}
.ks-kv-item {min-width:0;}
.ks-kv-label {font-size:10px; letter-spacing:.8px; text-transform:uppercase; color:#94a3b8; font-weight:800;}
.ks-kv-value {font-size:13.5px; color:#0f172a; font-weight:600; margin-top:2px; word-break:break-word;}
.ks-kv-value small {font-weight:400; color:#64748b;}

/* Timeline */
.ks-timeline {margin-top:4px;}
.ks-timeline-item {display:flex; gap:12px; padding:10px 0; border-bottom:1px dashed #e2e8f0;}
.ks-timeline-item:last-child {border-bottom:none;}
.ks-timeline-dot {
  width:30px; height:30px; border-radius:10px; background:#ecfeff; color:#0e7490;
  display:flex; align-items:center; justify-content:center; font-size:14px; flex:0 0 auto;
}
.ks-timeline-title {font-size:12.5px; font-weight:700; color:#0f172a;}
.ks-timeline-sub {font-size:11px; color:#64748b; margin-top:1px;}
.ks-timeline-time {font-size:10px; color:#94a3b8; margin-top:2px;}

/* Empty state */
.ks-empty {
  text-align:center; padding:34px 16px; border:1px dashed #cbd5e1; border-radius:16px;
  background: rgba(255,255,255,.55);
}
.ks-empty-icon {font-size:30px; margin-bottom:6px;}
.ks-empty-title {font-size:14px; font-weight:800; color:#334155;}
.ks-empty-sub {font-size:12px; color:#64748b; margin-top:3px;}

/* Streamlit overrides */
.stButton > button {
  border-radius:10px; font-weight:700; font-size:13px; border:1px solid #d8e2e4;
  transition: transform .08s ease, box-shadow .15s ease;
}
.stButton > button:hover {transform: translateY(-1px); box-shadow:0 6px 16px rgba(15,23,42,.08);}
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #0e7490, #0f766e) !important;
  border: none !important; color: #fff !important;
}
.stDownloadButton > button {border-radius:10px; font-weight:600;}
[data-testid="stDataFrame"] {border:1px solid #e6edf0; border-radius:14px; overflow:hidden;}
[data-testid="stExpander"] {border:1px solid #e6edf0; border-radius:14px; background:#fff;}
[data-testid="stForm"] {border:1px solid #e6edf0; border-radius:16px; padding:18px 20px; background:#fff;}
.stTabs [data-baseweb="tab-list"] {
  gap:4px; background:#eaf2f1; padding:5px; border-radius:12px; width:fit-content;
}
.stTabs [data-baseweb="tab"] {
  border-radius:9px; padding:6px 14px; height:auto; font-size:12.5px; font-weight:700; color:#475569;
}
.stTabs [aria-selected="true"] {
  background:#fff !important; color:#0e7490 !important; box-shadow:0 2px 8px rgba(15,23,42,.08);
}
.stProgress > div > div > div > div {background: linear-gradient(90deg, #0e7490, #2dd4bf);}
[data-testid="stMetricValue"] {font-size:22px; font-weight:800;}
div[data-testid="stToast"] {border-radius:12px;}
.stAlert {border-radius:12px;}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {display:none;}

@media (max-width: 760px) {
  .ks-header h1 {font-size:24px;}
  .ks-hero {padding:20px;}
  .ks-hero-title {font-size:21px;}
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Komponen HTML
# ---------------------------------------------------------------------------
def page_header(icon: str, title: str, subtitle: str, right: str | None = None) -> None:
    right_html = right if right is not None else (
        f'<span class="ks-date-chip">📅 {esc(today_label())}</span>'
    )
    st.markdown(
        f"""
        <div class="ks-header">
          <div>
            <div class="ks-eyebrow">KOSPACE · Administrasi Kos</div>
            <h1>{esc(icon)} {esc(title)}</h1>
            <p>{esc(subtitle)}</p>
          </div>
          <div class="ks-header-right">{right_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "", right: str = "") -> None:
    st.markdown(
        f"""
        <div class="ks-section">
          <div>
            <h3>{esc(title)}</h3>
            <p>{esc(subtitle)}</p>
          </div>
          <div class="ks-section-right">{right}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, sub: str = "", icon: str = "•", tone: str = "teal") -> None:
    st.markdown(
        f"""
        <div class="ks-stat ks-{esc(tone)}">
          <div class="ks-stat-top">
            <div class="ks-stat-icon">{esc(icon)}</div>
            <div class="ks-stat-label">{esc(label)}</div>
          </div>
          <div class="ks-stat-value">{esc(value)}</div>
          <div class="ks-stat-sub">{esc(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, tone: str = "slate") -> str:
    return f'<span class="ks-badge ks-b-{esc(tone)}">{esc(text)}</span>'


def status_badge(status: str) -> str:
    mapping = {
        "Tersedia": "green",
        "Ditempati": "teal",
        "Lunas": "green",
        "Belum Dibayar": "amber",
        "Terlambat": "rose",
        "Aktif": "teal",
        "Selesai": "slate",
    }
    icons = {
        "Tersedia": "●",
        "Ditempati": "●",
        "Lunas": "✓",
        "Belum Dibayar": "◔",
        "Terlambat": "!",
        "Aktif": "●",
        "Selesai": "✓",
    }
    return badge(f"{icons.get(status, '•')} {status}", mapping.get(status, "slate"))


def kv_grid(pairs: list[tuple[str, str]], cols: int = 2) -> None:
    items = "".join(
        f'<div class="ks-kv-item"><div class="ks-kv-label">{esc(label)}</div>'
        f'<div class="ks-kv-value">{value}</div></div>'
        for label, value in pairs
    )
    st.markdown(
        f'<div class="ks-kv" style="grid-template-columns: repeat({int(cols)}, minmax(0, 1fr));">'
        f"{items}</div>",
        unsafe_allow_html=True,
    )


def panel(title: str, subtitle: str, body_html: str) -> None:
    body = textwrap.dedent(body_html).strip()
    st.markdown(
        f'<div class="ks-panel">'
        f'<div class="ks-panel-title">{esc(title)}</div>'
        f'<div class="ks-panel-sub">{esc(subtitle)}</div>'
        f"{body}"
        f"</div>",
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="ks-empty">
          <div class="ks-empty-icon">{esc(icon)}</div>
          <div class="ks-empty-title">{esc(title)}</div>
          <div class="ks-empty-sub">{esc(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def timeline(items: list[dict]) -> None:
    """items: [{icon, title, subtitle, time}]"""
    if not items:
        empty_state("🕘", "Belum ada aktivitas", "Riwayat akan muncul di sini.")
        return
    rows = "".join(
        f"""
        <div class="ks-timeline-item">
          <div class="ks-timeline-dot">{it.get('icon', '•')}</div>
          <div>
            <div class="ks-timeline-title">{esc(it.get('title', ''))}</div>
            <div class="ks-timeline-sub">{esc(it.get('subtitle', ''))}</div>
            <div class="ks-timeline-time">{esc(it.get('time', ''))}</div>
          </div>
        </div>
        """
        for it in items
    )
    st.markdown(f'<div class="ks-timeline">{rows}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Navigasi & pesan
# ---------------------------------------------------------------------------
def flash(kind: str, message: str) -> None:
    st.session_state.setdefault("_flash", []).append((kind, message))


def show_flash() -> None:
    pesan = st.session_state.pop("_flash", [])
    for kind, message in pesan:
        fungsi = getattr(st, kind, st.info)
        fungsi(message)


def goto(page: str, tab: str | None = None, **state) -> None:
    # Target diterapkan di app.py sebelum widget radio dibuat, agar tidak
    # mengubah state widget yang sudah terinstansiasi pada run yang sama.
    st.session_state["_nav_target"] = page
    if tab:
        st.session_state[f"_tab_target_{page}"] = tab
    for kunci, nilai in state.items():
        st.session_state[kunci] = nilai
    st.rerun()


def tabbed(page: str, labels: list[str]):
    """Buat tab yang bisa diarahkan dari tombol lain lewat ui.goto(page, tab=...)."""
    key = f"_tabs_{page.lower()}"
    target = st.session_state.pop(f"_tab_target_{page}", None)
    if target in labels:
        st.session_state[key] = target
    if st.session_state.get(key) not in labels:
        st.session_state[key] = labels[0]
    return st.tabs(labels, default=st.session_state[key], key=key, on_change="rerun")


def ensure_select(options: list, key: str, default=None):
    """Pastikan nilai widget selectbox selalu ada di daftar opsi."""
    if not options:
        return None
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]
    return st.session_state[key]


def apply_pending_selection(pending_key: str, widget_key: str, options: list) -> None:
    """Pindahkan pilihan dari tombol 'Buka detail' ke widget selectbox."""
    if pending_key in st.session_state:
        nilai = st.session_state.pop(pending_key)
        if nilai in options:
            st.session_state[widget_key] = nilai


def progress_bar(persen: float, label: str = "") -> None:
    persen = max(0, min(100, float(persen or 0)))
    st.markdown(
        f"""
        <div style="margin:2px 0 8px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:4px;">
            <span>{esc(label)}</span><b style="color:#0e7490;">{persen:.0f}%</b>
          </div>
          <div style="height:8px;background:#e8eff0;border-radius:999px;overflow:hidden;">
            <div style="height:100%;width:{persen:.1f}%;background:linear-gradient(90deg,#0e7490,#2dd4bf);border-radius:999px;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
