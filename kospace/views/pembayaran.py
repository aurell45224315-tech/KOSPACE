"""Halaman Pencatatan Pembayaran."""

from datetime import date

import pandas as pd
import streamlit as st

from .. import components, db, logic, ui

_STATUS_EMOJI = {
    "Lunas": "🟢 Lunas",
    "Belum Dibayar": "🟡 Belum Dibayar",
    "Terlambat": "🔴 Terlambat",
}


def _to_csv(rows: list[dict]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def render() -> None:
    pembayaran = db.list_pembayaran()
    bills = logic.build_bills()
    hari_ini = date.today()
    bulan_ini = [
        p for p in pembayaran
        if (logic.parse_date(p["tanggal_bayar"]).year, logic.parse_date(p["tanggal_bayar"]).month)
        == (hari_ini.year, hari_ini.month)
    ]
    telat = [b for b in bills if b["status"] == "Terlambat"]
    belum = [b for b in bills if b["status"] != "Lunas"]
    total_bulan_ini = sum(int(p["nominal"]) for p in bulan_ini)

    ui.page_header("💳", "Pencatatan Pembayaran", "Tagihan per periode, status otomatis, dan riwayat transaksi")
    ui.show_flash()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.stat_card("Diterima bulan ini", ui.rupiah(total_bulan_ini), f"{len(bulan_ini)} transaksi", "💰", "green")
    with c2:
        ui.stat_card("Tagihan belum lunas", str(len(belum)), ui.rupiah(sum(int(b["nominal"]) for b in belum)), "🧾", "amber")
    with c3:
        ui.stat_card("Terlambat", str(len(telat)), ui.rupiah(sum(int(b["nominal"]) for b in telat)), "⏰", "rose")
    with c4:
        ui.stat_card("Total transaksi", str(len(pembayaran)), "Seluruh pembayaran tercatat", "📚", "teal")

    st.write("")
    tab_tagihan, tab_catat, tab_riwayat = ui.tabbed(
        "Pembayaran", ["🧾 Tagihan", "➕ Catat pembayaran", "📚 Riwayat pembayaran"]
    )

    # ------------------------------------------------------------------
    # TAGIHAN
    # ------------------------------------------------------------------
    with tab_tagihan:
        ui.section(
            "Daftar tagihan per periode",
            "Lunas · Belum Dibayar (sebelum tanggal 10) · Terlambat (setelah tanggal 10)",
        )
        status_filter = st.multiselect(
            "Status tagihan", ["Belum Dibayar", "Terlambat", "Lunas"],
            default=["Belum Dibayar", "Terlambat"], key="bayar_status_filter",
        )
        f1, f2, f3 = st.columns([1.6, 1.2, 1.2])
        with f1:
            cari = st.text_input(
                "Cari tagihan", placeholder="Nama penghuni, kamar, atau ID sewa", key="bayar_cari"
            )
        with f2:
            opsi_sewa = {"Semua sewa": "Semua sewa"}
            for s in db.list_sewa():
                opsi_sewa[s["id_sewa"]] = f"{s['id_sewa']} · {s['nama']} · {s['nomor_kamar']}"
            sewa_filter = st.selectbox(
                "Sewa", list(opsi_sewa), format_func=lambda x: opsi_sewa[x], key="bayar_sewa_filter"
            )
        with f3:
            tahun_list = sorted({b["tahun"] for b in bills}, reverse=True)
            tahun_filter = st.selectbox(
                "Tahun periode", ["Semua tahun"] + tahun_list, key="bayar_tahun_filter"
            )

        hasil = []
        for b in bills:
            teks = f"{b['nama']} {b['nomor_kamar']} {b['id_sewa']} {b['periode']}".lower()
            if cari and cari.strip().lower() not in teks:
                continue
            if status_filter and b["status"] not in status_filter:
                continue
            if sewa_filter != "Semua sewa" and b["id_sewa"] != sewa_filter:
                continue
            if tahun_filter != "Semua tahun" and b["tahun"] != tahun_filter:
                continue
            hasil.append(b)

        st.caption(
            f"Menampilkan **{len(hasil)}** tagihan · total "
            f"**{ui.rupiah(sum(int(b['nominal']) for b in hasil))}**."
        )
        if hasil:
            rows = []
            for b in hasil:
                ket = ""
                if b["status"] == "Terlambat":
                    ket = f"{b['hari_telat']} hari terlambat"
                elif b["status"] == "Lunas":
                    ket = f"Dibayar {ui.fmt_date(b['tanggal_bayar'])}"
                else:
                    ket = "Belum jatuh tempo"
                rows.append(
                    {
                        "Sewa": b["id_sewa"],
                        "Penghuni": b["nama"],
                        "Kamar": b["nomor_kamar"],
                        "Periode": b["periode"],
                        "Jatuh tempo": ui.fmt_date(b["jatuh_tempo"]),
                        "Nominal": ui.rupiah(b["nominal"]),
                        "Status": _STATUS_EMOJI.get(b["status"], b["status"]),
                        "Keterangan": ket,
                    }
                )
            st.dataframe(rows, hide_index=True, width="stretch")
            st.download_button(
                "⬇️ Unduh daftar tagihan (CSV)",
                data=_to_csv(
                    [
                        {
                            "id_sewa": b["id_sewa"],
                            "penghuni": b["nama"],
                            "kamar": b["nomor_kamar"],
                            "periode_bulan": b["bulan"],
                            "periode_tahun": b["tahun"],
                            "jatuh_tempo": b["jatuh_tempo"],
                            "nominal": b["nominal"],
                            "status": b["status"],
                        }
                        for b in hasil
                    ]
                ),
                file_name="kospace_tagihan.csv",
                mime="text/csv",
                key="unduh_tagihan",
            )
        else:
            ui.empty_state("🎉", "Tidak ada tagihan pada filter ini", "Coba ubah status atau filter sewa.")

        st.info(
            "Untuk mencatat pembayaran, buka tab **Catat pembayaran**. "
            "Satu sewa hanya boleh punya satu pembayaran per bulan dan tahun (B14)."
        )

    # ------------------------------------------------------------------
    # CATAT PEMBAYARAN
    # ------------------------------------------------------------------
    with tab_catat:
        ui.section("Catat pembayaran baru", "Nominal harus sama dengan harga sewa bulanan (B08)")
        sewa_all = db.list_sewa()
        if not sewa_all:
            ui.empty_state("📄", "Belum ada sewa", "Buat sewa terlebih dahulu sebelum mencatat pembayaran.")
        else:
            urutan = sorted(sewa_all, key=lambda s: (s["status_sewa"] != "Aktif", s["tanggal_mulai"]), reverse=False)
            opsi = {
                s["id_sewa"]: (
                    f"{s['id_sewa']} · {s['nama']} · {s['nomor_kamar']} · "
                    f"{s['status_sewa']} · {ui.rupiah(s['harga_bulanan'])}/bln"
                )
                for s in urutan
            }
            if "bayar_pilih_sewa" in st.session_state and st.session_state["bayar_pilih_sewa"] not in opsi:
                st.session_state.pop("bayar_pilih_sewa", None)
            ui.ensure_select(list(opsi), "bayar_pilih_sewa")
            pilih = st.selectbox(
                "Pilih sewa", list(opsi), format_func=lambda x: opsi[x], key="bayar_pilih_sewa"
            )
            s = db.get_sewa(pilih)
            prog = logic.payment_progress(pilih)
            sisa = prog["total"] - prog["lunas"]

            kiri, kanan = st.columns([1.3, 1])
            with kiri:
                with st.container(border=True):
                    st.markdown("**💳 Form pembayaran**")
                    components.payment_form(s, f"bayar_{s['id_sewa']}")
            with kanan:
                st.markdown(
                    f"""
                    <div class="ks-panel">
                      <div class="ks-panel-title">Ringkasan sewa</div>
                      <div class="ks-panel-sub">{ui.esc(s['id_sewa'])} · {ui.esc(s['nama'])}</div>
                      <div class="ks-kv" style="grid-template-columns:1fr 1fr;">
                        <div class="ks-kv-item"><div class="ks-kv-label">Kamar</div>
                          <div class="ks-kv-value">{ui.esc(s['nomor_kamar'])} · {ui.esc(s['tipe'])}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Status</div>
                          <div class="ks-kv-value">{ui.status_badge(s['status_sewa'])}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Masa sewa</div>
                          <div class="ks-kv-value">{ui.fmt_date(s['tanggal_mulai'])}<br><small>s.d. {ui.fmt_date(s['tanggal_selesai'])}</small></div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Harga/bulan</div>
                          <div class="ks-kv-value">{ui.rupiah(s['harga_bulanan'])}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Sudah lunas</div>
                          <div class="ks-kv-value">{prog['lunas']} periode</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Belum lunas</div>
                          <div class="ks-kv-value" style="color:#be123c;">{sisa} periode</div></div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ------------------------------------------------------------------
    # RIWAYAT PEMBAYARAN
    # ------------------------------------------------------------------
    with tab_riwayat:
        ui.section("Riwayat pembayaran", "Telusuri transaksi berdasarkan tahun, bulan, penghuni, atau kamar")
        f1, f2, f3, f4 = st.columns([1, 1, 1.4, 1.6])
        with f1:
            tahun_list = sorted({p["periode_tahun"] for p in pembayaran}, reverse=True)
            tahun = st.selectbox("Tahun", ["Semua tahun"] + tahun_list, key="riwayat_bayar_tahun")
        with f2:
            bulan = st.selectbox(
                "Bulan", ["Semua bulan"] + list(range(1, 13)),
                format_func=lambda x: x if x == "Semua bulan" else logic.month_label(x),
                key="riwayat_bayar_bulan",
            )
        with f3:
            nama_list = sorted({p["nama"] for p in pembayaran})
            nama = st.selectbox("Penghuni", ["Semua penghuni"] + nama_list, key="riwayat_bayar_nama")
        with f4:
            cari = st.text_input("Cari ID / kamar", placeholder="BY001 atau A01", key="riwayat_bayar_cari")

        hasil = []
        for p in pembayaran:
            if tahun != "Semua tahun" and p["periode_tahun"] != tahun:
                continue
            if bulan != "Semua bulan" and p["periode_bulan"] != bulan:
                continue
            if nama != "Semua penghuni" and p["nama"] != nama:
                continue
            teks = f"{p['id_pembayaran']} {p['nomor_kamar']} {p['id_sewa']}".lower()
            if cari and cari.strip().lower() not in teks:
                continue
            hasil.append(p)

        total = sum(int(p["nominal"]) for p in hasil)
        st.caption(f"Menampilkan **{len(hasil)}** transaksi · total **{ui.rupiah(total)}**.")
        if hasil:
            rows = [
                {
                    "ID": p["id_pembayaran"],
                    "Tanggal": ui.fmt_date(p["tanggal_bayar"]),
                    "Penghuni": p["nama"],
                    "Kamar": p["nomor_kamar"],
                    "Sewa": p["id_sewa"],
                    "Periode": f"{logic.month_label(p['periode_bulan'])} {p['periode_tahun']}",
                    "Nominal": ui.rupiah(p["nominal"]),
                    "Status": "🟢 Lunas",
                }
                for p in hasil
            ]
            st.dataframe(rows, hide_index=True, width="stretch")
            st.download_button(
                "⬇️ Unduh riwayat pembayaran (CSV)",
                data=_to_csv(
                    [
                        {
                            "id_pembayaran": p["id_pembayaran"],
                            "tanggal_bayar": p["tanggal_bayar"],
                            "id_sewa": p["id_sewa"],
                            "penghuni": p["nama"],
                            "kamar": p["nomor_kamar"],
                            "periode_bulan": p["periode_bulan"],
                            "periode_tahun": p["periode_tahun"],
                            "nominal": p["nominal"],
                            "status": p["status_pembayaran"],
                        }
                        for p in hasil
                    ]
                ),
                file_name="kospace_pembayaran.csv",
                mime="text/csv",
                key="unduh_pembayaran",
            )
        else:
            ui.empty_state("💳", "Belum ada pembayaran", "Ubah filter atau catat pembayaran baru.")

        st.write("")
        ui.section("Detail transaksi", "Pilih pembayaran untuk melihat detail dan koreksi")
        if pembayaran:
            opsi = {
                p["id_pembayaran"]: (
                    f"{p['id_pembayaran']} · {ui.fmt_date(p['tanggal_bayar'])} · "
                    f"{p['nama']} · {logic.month_label(p['periode_bulan'])} {p['periode_tahun']}"
                )
                for p in pembayaran
            }
            if "detail_bayar_pilih" in st.session_state and st.session_state["detail_bayar_pilih"] not in opsi:
                st.session_state.pop("detail_bayar_pilih", None)
            ui.ensure_select(list(opsi), "detail_bayar_pilih")
            pilih = st.selectbox(
                "Pilih pembayaran", list(opsi), format_func=lambda x: opsi[x], key="detail_bayar_pilih"
            )
            p = db.get_pembayaran(pilih)
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:6px 0 12px;">
                  <div>
                    <div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#0e7490;font-weight:800;">Detail pembayaran</div>
                    <div style="font-size:24px;font-weight:800;color:#0f172a;">{ui.esc(p['id_pembayaran'])}</div>
                  </div>
                  <div>{ui.status_badge('Lunas')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            ui.kv_grid(
                [
                    ("Penghuni", ui.esc(p["nama"])),
                    ("Kamar", f"{ui.esc(p['nomor_kamar'])} <small>· {ui.esc(p['tipe'])}</small>"),
                    ("Sewa", ui.esc(p["id_sewa"])),
                    ("Periode", f"{logic.month_label(p['periode_bulan'])} {p['periode_tahun']}"),
                    ("Tanggal bayar", ui.fmt_date(p["tanggal_bayar"])),
                    ("Nominal", ui.rupiah(p["nominal"])),
                    ("Status", ui.status_badge(p["status_pembayaran"])),
                    ("Masa sewa", f"{ui.fmt_date(p['tanggal_mulai'])} s.d. {ui.fmt_date(p['tanggal_selesai'])}"),
                ],
                cols=2,
            )

            st.write("")
            with st.expander("🗑️ Hapus pembayaran (koreksi salah catat)"):
                st.caption(
                    "Pembayaran boleh dihapus hanya untuk memperbaiki salah catat. "
                    "Penghapusan tidak memengaruhi tabel lain."
                )
                cek = st.checkbox(
                    f"Saya yakin menghapus pembayaran {p['id_pembayaran']}.",
                    key=f"hapus_bayar_cek_{p['id_pembayaran']}",
                )
                if st.button(
                    "Hapus pembayaran", type="primary", disabled=not cek,
                    key=f"hapus_bayar_btn_{p['id_pembayaran']}",
                ):
                    try:
                        logic.delete_pembayaran(p["id_pembayaran"])
                        ui.flash("success", f"Pembayaran {p['id_pembayaran']} berhasil dihapus.")
                        st.rerun()
                    except logic.BusinessError as exc:
                        st.error(str(exc))
        else:
            ui.empty_state("🧾", "Belum ada transaksi", "Detail akan muncul setelah ada pembayaran.")
