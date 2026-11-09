"""Halaman Riwayat & Detail Transaksi."""

import pandas as pd
import streamlit as st

from .. import db, logic, ui


def _to_csv(rows: list[dict]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def _tabel_sewa(rows: list[dict], key: str = "") -> None:
    if not rows:
        ui.empty_state("📄", "Belum ada riwayat sewa", "Kontrak akan muncul di sini.")
        return
    data = [
        {
            "ID": s["id_sewa"],
            "Kamar": s["nomor_kamar"],
            "Mulai": ui.fmt_date(s["tanggal_mulai"]),
            "Selesai": ui.fmt_date(s["tanggal_selesai"]),
            "Durasi": f"{s['durasi']} bln",
            "Harga/bln": ui.rupiah(s["harga_bulanan"]),
            "Dibayar": ui.rupiah(s["total_bayar"]),
            "Status": "🟢 Aktif" if s["status_sewa"] == "Aktif" else "⚪ Selesai",
        }
        for s in rows
    ]
    st.dataframe(data, hide_index=True, width="stretch", key=key or None)


def _tabel_bayar(rows: list[dict], key: str = "") -> None:
    if not rows:
        ui.empty_state("💳", "Belum ada pembayaran", "Transaksi akan muncul di sini.")
        return
    data = [
        {
            "ID": p["id_pembayaran"],
            "Tanggal": ui.fmt_date(p["tanggal_bayar"]),
            "Sewa": p["id_sewa"],
            "Kamar": p["nomor_kamar"],
            "Periode": f"{logic.month_label(p['periode_bulan'])} {p['periode_tahun']}",
            "Nominal": ui.rupiah(p["nominal"]),
            "Status": "🟢 Lunas",
        }
        for p in rows
    ]
    st.dataframe(data, hide_index=True, width="stretch", key=key or None)


def render() -> None:
    ui.page_header("🕘", "Riwayat & Detail Transaksi", "Telusuri riwayat sewa, pembayaran, dan aktivitas sistem")
    ui.show_flash()

    tab_orang, tab_kamar, tab_linimasa, tab_log = ui.tabbed(
        "Riwayat", ["👤 Per penghuni", "🚪 Per kamar", "🧭 Linimasa", "📝 Log aktivitas"]
    )

    # ------------------------------------------------------------------
    # PER PENGHUNI
    # ------------------------------------------------------------------
    with tab_orang:
        penghuni = db.list_penghuni()
        if not penghuni:
            ui.empty_state("👤", "Belum ada penghuni", "Tambahkan penghuni terlebih dahulu.")
        else:
            ui.section("Riwayat per penghuni", "Kontrak dan pembayaran yang terkait dengan satu orang")
            opsi = {p["id_penghuni"]: f"{p['nama']} · {p['kamar_aktif'] or 'tidak menempati kamar'}" for p in penghuni}
            if "riwayat_orang_pilih" in st.session_state and st.session_state["riwayat_orang_pilih"] not in opsi:
                st.session_state.pop("riwayat_orang_pilih", None)
            ui.ensure_select(list(opsi), "riwayat_orang_pilih")
            pilih = st.selectbox(
                "Pilih penghuni", list(opsi), format_func=lambda x: opsi[x], key="riwayat_orang_pilih"
            )
            p = db.get_penghuni(pilih)
            fin = logic.tenant_financials(pilih)

            st.markdown(
                f"""
                <div class="ks-panel" style="margin-bottom:14px;">
                  <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;">
                    <div>
                      <div class="ks-panel-title" style="font-size:18px;">{ui.esc(p['nama'])}</div>
                      <div class="ks-panel-sub">{ui.esc(p['id_penghuni'])} · {ui.esc(p['telepon'])} · {ui.esc(p['alamat'] or 'Alamat belum diisi')}</div>
                    </div>
                    <div>{ui.status_badge('Aktif') if p['kamar_aktif'] else ui.badge('Tidak menempati', 'slate')}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ui.stat_card("Kontrak", str(fin["jumlah_sewa"]), "Total riwayat sewa", "📄", "teal")
            with c2:
                ui.stat_card("Nilai kontrak", ui.rupiah(fin["total_kontrak"]), "Harga × durasi", "🧮", "indigo")
            with c3:
                ui.stat_card("Total dibayar", ui.rupiah(fin["total_bayar"]), "Akumulasi pembayaran", "💰", "green")
            with c4:
                ui.stat_card("Tunggakan", ui.rupiah(fin["tunggakan"]), f"Belum bayar {ui.rupiah(fin['belum_bayar'])}", "⏰", "rose")

            st.write("")
            ui.section("Riwayat sewa", "Seluruh kontrak penghuni ini")
            _tabel_sewa(fin["sewa"], key=f"riwayat_sewa_orang_{pilih}")

            st.write("")
            ui.section("Riwayat pembayaran", "Seluruh transaksi penghuni ini")
            _tabel_bayar(fin["pembayaran"], key=f"riwayat_bayar_orang_{pilih}")

            st.write("")
            ui.section("Tagihan belum lunas", "Periode yang perlu ditindaklanjuti")
            belum = [b for b in fin["tagihan"] if b["status"] != "Lunas"]
            if belum:
                rows = [
                    {
                        "Sewa": b["id_sewa"],
                        "Kamar": b["nomor_kamar"],
                        "Periode": b["periode"],
                        "Jatuh tempo": ui.fmt_date(b["jatuh_tempo"]),
                        "Nominal": ui.rupiah(b["nominal"]),
                        "Status": "🔴 Terlambat" if b["status"] == "Terlambat" else "🟡 Belum Dibayar",
                    }
                    for b in belum
                ]
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("🎉", "Tidak ada tunggakan", "Semua tagihan penghuni ini lunas.")

    # ------------------------------------------------------------------
    # PER KAMAR
    # ------------------------------------------------------------------
    with tab_kamar:
        kamar = db.list_kamar()
        if not kamar:
            ui.empty_state("🚪", "Belum ada kamar", "Tambahkan kamar terlebih dahulu.")
        else:
            ui.section("Riwayat per kamar", "Siapa saja yang pernah menempati dan berapa pendapatannya")
            opsi = {k["id_kamar"]: f"{k['nomor_kamar']} · {k['tipe']} · {k['status']}" for k in kamar}
            if "riwayat_kamar_pilih" in st.session_state and st.session_state["riwayat_kamar_pilih"] not in opsi:
                st.session_state.pop("riwayat_kamar_pilih", None)
            ui.ensure_select(list(opsi), "riwayat_kamar_pilih")
            pilih = st.selectbox(
                "Pilih kamar", list(opsi), format_func=lambda x: opsi[x], key="riwayat_kamar_pilih"
            )
            k = db.get_kamar(pilih)
            sewa_kamar = db.sewa_for_kamar(pilih)
            bayar_kamar = db.pembayaran_for_kamar(pilih)
            total_pendapatan = sum(int(b["nominal"]) for b in bayar_kamar)
            total_kontrak = sum(int(s["harga_bulanan"]) * int(s["durasi"]) for s in sewa_kamar)

            st.markdown(
                f"""
                <div class="ks-panel" style="margin-bottom:14px;">
                  <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;">
                    <div>
                      <div class="ks-panel-title" style="font-size:18px;">Kamar {ui.esc(k['nomor_kamar'])}</div>
                      <div class="ks-panel-sub">{ui.esc(k['tipe'])} · {ui.esc(k['fasilitas'])} · ID {ui.esc(k['id_kamar'])}</div>
                    </div>
                    <div>{ui.status_badge(k['status'])}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ui.stat_card("Harga kamar", ui.rupiah(k["harga_bulanan"]), "Harga berlaku saat ini", "💵", "teal")
            with c2:
                ui.stat_card("Jumlah sewa", str(len(sewa_kamar)), "Riwayat kontrak", "📄", "indigo")
            with c3:
                ui.stat_card("Nilai kontrak", ui.rupiah(total_kontrak), "Akumulasi seluruh sewa", "🧮", "amber")
            with c4:
                ui.stat_card("Pendapatan", ui.rupiah(total_pendapatan), "Pembayaran diterima", "💰", "green")

            st.write("")
            ui.section("Riwayat penghuni kamar", "Kontrak dari waktu ke waktu")
            _tabel_sewa(sewa_kamar, key=f"riwayat_sewa_kamar_{pilih}")

            st.write("")
            ui.section("Riwayat pembayaran kamar", "Seluruh transaksi untuk kamar ini")
            _tabel_bayar(bayar_kamar, key=f"riwayat_bayar_kamar_{pilih}")

    # ------------------------------------------------------------------
    # LINIMASA
    # ------------------------------------------------------------------
    with tab_linimasa:
        ui.section("Linimasa transaksi", "Gabungan peristiwa sewa dan pembayaran, terbaru di atas")
        events = logic.timeline_events()
        f1, f2, f3 = st.columns([1, 1.3, 1.7])
        with f1:
            tahun_list = sorted({int(e["tanggal"][:4]) for e in events}, reverse=True)
            tahun = st.selectbox("Tahun", ["Semua tahun"] + tahun_list, key="linimasa_tahun")
        with f2:
            jenis = st.multiselect(
                "Jenis peristiwa", ["Sewa mulai", "Sewa selesai", "Pembayaran"],
                default=["Sewa mulai", "Sewa selesai", "Pembayaran"], key="linimasa_jenis",
            )
        with f3:
            cari = st.text_input(
                "Cari keterangan", placeholder="Nama, kamar, atau ID", key="linimasa_cari"
            )

        hasil = []
        for e in events:
            if tahun != "Semua tahun" and int(e["tanggal"][:4]) != tahun:
                continue
            if jenis and e["jenis"] not in jenis:
                continue
            if cari and cari.strip().lower() not in f"{e['keterangan']} {e['id']}".lower():
                continue
            hasil.append(e)

        st.caption(f"Menampilkan **{len(hasil)}** peristiwa.")
        if hasil:
            rows = [
                {
                    "Tanggal": ui.fmt_date(e["tanggal"]),
                    "Jenis": {
                        "Sewa mulai": "🏠 Sewa mulai",
                        "Sewa selesai": "✅ Sewa selesai",
                        "Pembayaran": "💳 Pembayaran",
                    }.get(e["jenis"], e["jenis"]),
                    "Keterangan": e["keterangan"],
                    "Nominal": ui.rupiah(e["nominal"]) if e["nominal"] else "—",
                }
                for e in hasil
            ]
            st.dataframe(rows, hide_index=True, width="stretch")
            st.download_button(
                "⬇️ Unduh linimasa (CSV)",
                data=_to_csv(
                    [
                        {
                            "tanggal": e["tanggal"],
                            "jenis": e["jenis"],
                            "keterangan": e["keterangan"],
                            "nominal": e["nominal"],
                            "id": e["id"],
                        }
                        for e in hasil
                    ]
                ),
                file_name="kospace_linimasa.csv",
                mime="text/csv",
                key="unduh_linimasa",
            )

            st.write("")
            ui.section("Sorotan terbaru", "10 peristiwa terakhir pada filter ini")
            ui.timeline(
                [
                    {
                        "icon": {
                            "Sewa mulai": "🏠",
                            "Sewa selesai": "✅",
                            "Pembayaran": "💳",
                        }.get(e["jenis"], "•"),
                        "title": f"{e['jenis']} · {e['keterangan']}",
                        "subtitle": ui.rupiah(e["nominal"]) if e["nominal"] else "",
                        "time": ui.fmt_date(e["tanggal"]),
                    }
                    for e in hasil[:10]
                ]
            )
        else:
            ui.empty_state("🧭", "Belum ada peristiwa", "Ubah filter atau mulai gunakan sistem.")

    # ------------------------------------------------------------------
    # LOG AKTIVITAS
    # ------------------------------------------------------------------
    with tab_log:
        ui.section("Log aktivitas sistem", "Jejak tambah, ubah, hapus, dan pembayaran")
        logs = db.list_log(300)
        if logs:
            rows = [
                {
                    "Waktu": ui.fmt_datetime(log["waktu"]),
                    "Aksi": log["aksi"],
                    "Entitas": log["entitas"],
                    "Keterangan": log["keterangan"] or "—",
                }
                for log in logs
            ]
            st.dataframe(rows, hide_index=True, width="stretch")
            st.download_button(
                "⬇️ Unduh log aktivitas (CSV)",
                data=_to_csv(
                    [
                        {
                            "waktu": log["waktu"],
                            "aksi": log["aksi"],
                            "entitas": log["entitas"],
                            "keterangan": log["keterangan"],
                        }
                        for log in logs
                    ]
                ),
                file_name="kospace_log.csv",
                mime="text/csv",
                key="unduh_log",
            )
        else:
            ui.empty_state("📝", "Belum ada aktivitas", "Log akan terisi setelah ada perubahan data.")
