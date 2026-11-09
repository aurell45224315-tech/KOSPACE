"""Halaman Dashboard KOSPACE."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from .. import db, logic, ui

_STATUS_EMOJI = {
    "Lunas": "🟢 Lunas",
    "Belum Dibayar": "🟡 Belum Dibayar",
    "Terlambat": "🔴 Terlambat",
}


def _open(page: str, **state):
    ui.goto(page, **state)


def render() -> None:
    m = logic.dashboard_metrics()
    ui.page_header(
        "🏠",
        "Dashboard",
        "Ringkasan administrasi KOSPACE hari ini",
    )
    ui.show_flash()

    if m["is_demo"]:
        st.info(
            "ℹ️ Aplikasi saat ini berisi **data contoh** agar dashboard langsung terisi. "
            "Kelola atau hapus data contoh di menu **Pengaturan → Database**."
        )

    okupansi = m["okupansi"]
    st.markdown(
        f"""
        <div class="ks-hero">
          <div class="ks-hero-grid">
            <div>
              <div class="ks-hero-eyebrow">Selamat datang, Pemilik Kos</div>
              <div class="ks-hero-title">Kos Putri KOSPACE 🏡</div>
              <div class="ks-hero-sub">
                {m['total_kamar']} kamar · {m['sewa_aktif']} sewa aktif ·
                {m['tersedia']} kamar siap dihuni. Semua data kamar, penghuni, sewa,
                dan pembayaran tersimpan rapi dalam satu sistem.
              </div>
            </div>
            <div class="ks-hero-ring">
              <div class="ks-hero-pct">{okupansi:.0f}<span>%</span></div>
              <div class="ks-hero-ring-label">Tingkat hunian</div>
              <div class="ks-hero-bar"><div style="width:{max(2, okupansi):.1f}%"></div></div>
              <div style="font-size:11px;color:#a7f3d0;margin-top:6px;">{m['ditempati']} dari {m['total_kamar']} kamar</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    aksi = st.columns(4)
    with aksi[0]:
        if st.button("＋ Tambah penghuni", width="stretch"):
            _open("Penghuni", tab="➕ Tambah penghuni")
    with aksi[1]:
        if st.button("＋ Buat sewa", width="stretch"):
            _open("Sewa", tab="➕ Buat sewa")
    with aksi[2]:
        if st.button("💳 Catat pembayaran", width="stretch"):
            _open("Pembayaran", tab="➕ Catat pembayaran")
    with aksi[3]:
        if st.button("🕘 Lihat riwayat", width="stretch"):
            _open("Riwayat", tab="🧭 Linimasa")

    st.write("")

    k1, k2, k3 = st.columns(3)
    with k1:
        ui.stat_card("Total kamar", str(m["total_kamar"]), "3 tipe kamar · 25 unit", "🚪", "teal")
    with k2:
        ui.stat_card("Kamar tersedia", str(m["tersedia"]), f"{m['okupansi']:.0f}% terisi", "✅", "green")
    with k3:
        ui.stat_card("Kamar ditempati", str(m["ditempati"]), f"{m['sewa_aktif']} sewa aktif", "👥", "indigo")

    k4, k5, k6 = st.columns(3)
    with k4:
        ui.stat_card("Penerimaan bulan ini", ui.rupiah(m["penerimaan_bulan_ini"]), f"{m['transaksi_bulan_ini']} transaksi tercatat", "💰", "teal")
    with k5:
        ui.stat_card("Tunggakan", ui.rupiah(m["tunggakan_nominal"]), f"{m['tunggakan_count']} tagihan terlambat", "⏰", "rose")
    with k6:
        ui.stat_card("Total penghuni", str(m["total_penghuni"]), f"{m['penghuni_aktif']} sedang menempati kamar", "🧾", "amber")

    st.write("")

    c1, c2 = st.columns([1.15, 1])
    with c1:
        ui.section("Okupansi per tipe kamar", "Perbandingan kamar tersedia dan ditempati")
        df_tipe = pd.DataFrame(m["breakdown"])
        st.bar_chart(
            df_tipe,
            x="Tipe",
            y=["Tersedia", "Ditempati"],
            stack=True,
            height=255,
            color=["#2dd4bf", "#0e7490"],
        )
    with c2:
        ui.section("Pendapatan 6 bulan terakhir", "Berdasarkan tanggal pembayaran diterima")
        df_rev = pd.DataFrame(m["revenue"])
        st.bar_chart(
            df_rev,
            x="Bulan",
            y="Pendapatan",
            height=255,
            color="#0e7490",
        )

    st.write("")
    left, right = st.columns([1.25, 1])
    with left:
        ui.section(
            "Jatuh tempo & tunggakan",
            "Prioritas penagihan: terlambat lebih dahulu",
        )
        if m["jatuh_tempo"]:
            rows = []
            for b in m["jatuh_tempo"][:8]:
                rows.append(
                    {
                        "Periode": b["periode"],
                        "Penghuni": b["nama"],
                        "Kamar": b["nomor_kamar"],
                        "Jatuh tempo": ui.fmt_date(b["jatuh_tempo"]),
                        "Nominal": ui.rupiah(b["nominal"]),
                        "Status": _STATUS_EMOJI.get(b["status"], b["status"]),
                    }
                )
            st.dataframe(rows, hide_index=True, width="stretch", height=330)
        else:
            ui.empty_state("🎉", "Tidak ada tunggakan", "Semua tagihan sudah lunas.")

    with right:
        ui.section("Pembayaran terbaru", "Enam transaksi terakhir yang tercatat")
        if m["recent_payments"]:
            rows = []
            for p in m["recent_payments"]:
                rows.append(
                    {
                        "Tanggal": ui.fmt_date(p["tanggal_bayar"]),
                        "Penghuni": p["nama"],
                        "Kamar": p["nomor_kamar"],
                        "Periode": f"{logic.month_label(p['periode_bulan'])[:3]} {p['periode_tahun']}",
                        "Nominal": ui.rupiah(p["nominal"]),
                    }
                )
            st.dataframe(rows, hide_index=True, width="stretch", height=330)
        else:
            ui.empty_state("💳", "Belum ada pembayaran", "Catat pembayaran pertama Anda.")

    st.write("")
    ui.section("Sewa aktif", "Progres pembayaran tiap sewa yang sedang berjalan")
    if m["active_rentals"]:
        rows = []
        for s in m["active_rentals"]:
            prog = m["progress"].get(s["id_sewa"], {})
            rows.append(
                {
                    "ID": s["id_sewa"],
                    "Penghuni": s["nama"],
                    "Kamar": s["nomor_kamar"],
                    "Mulai": ui.fmt_date(s["tanggal_mulai"]),
                    "Selesai": ui.fmt_date(s["tanggal_selesai"]),
                    "Durasi": f"{s['durasi']} bln",
                    "Harga/bln": ui.rupiah(s["harga_bulanan"]),
                    "Pembayaran": f"{prog.get('lunas', 0)}/{prog.get('total', 0)} periode",
                    "Status": "🟢 Aktif",
                }
            )
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        ui.empty_state("🏠", "Belum ada sewa aktif", "Buat sewa dari menu Sewa.")

    st.write("")
    ui.section("Aktivitas terbaru", "Jejak perubahan data terakhir di sistem")
    items = []
    icons = {"Tambah": "➕", "Ubah": "✏️", "Hapus": "🗑️", "Bayar": "💳", "Selesai": "✅", "Sistem": "⚙️"}
    for log in m["logs"]:
        items.append(
            {
                "icon": icons.get(log["aksi"], "•"),
                "title": f"{log['aksi']} {log['entitas']}",
                "subtitle": log["keterangan"] or "",
                "time": ui.fmt_datetime(log["waktu"]),
            }
        )
    ui.timeline(items)
