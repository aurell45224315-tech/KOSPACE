"""Halaman Pengelolaan Sewa."""

from datetime import date

import streamlit as st

from .. import components, db, logic, ui


def _sync_harga_sewa() -> None:
    id_kamar = st.session_state.get("sewa_baru_kamar")
    if not id_kamar:
        return
    kamar = db.get_kamar(id_kamar)
    if kamar:
        st.session_state["sewa_baru_harga"] = int(kamar["harga_bulanan"])


def render() -> None:
    sewa = db.list_sewa()
    aktif = [s for s in sewa if s["status_sewa"] == "Aktif"]
    selesai = [s for s in sewa if s["status_sewa"] == "Selesai"]
    total_dibayar = sum(int(s["total_bayar"] or 0) for s in sewa)

    ui.page_header("📄", "Pengelolaan Sewa", "Kontrak sewa, masa huni, dan pencegahan jadwal bertabrakan")
    ui.show_flash()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.stat_card("Total sewa", str(len(sewa)), "Seluruh kontrak", "📄", "teal")
    with c2:
        ui.stat_card("Sewa aktif", str(len(aktif)), "Sedang berjalan", "🟢", "green")
    with c3:
        ui.stat_card("Sewa selesai", str(len(selesai)), "Sudah berakhir", "✅", "slate")
    with c4:
        ui.stat_card("Total dibayar", ui.rupiah(total_dibayar), "Akumulasi seluruh sewa", "💰", "amber")

    st.write("")
    tab_daftar, tab_baru, tab_detail = ui.tabbed(
        "Sewa", ["📋 Daftar sewa", "➕ Buat sewa", "🔎 Detail & aksi"]
    )

    # ------------------------------------------------------------------
    # DAFTAR
    # ------------------------------------------------------------------
    with tab_daftar:
        ui.section("Daftar seluruh sewa", "Status Selesai diisi otomatis saat tanggal selesai terlewati")
        f1, f2, f3 = st.columns([2, 1.4, 1.4])
        with f1:
            cari = st.text_input(
                "Cari sewa", placeholder="ID sewa, nama penghuni, atau kamar", key="sewa_cari"
            )
        with f2:
            status_filter = st.multiselect(
                "Status sewa", ["Aktif", "Selesai"], default=["Aktif", "Selesai"], key="sewa_status_filter"
            )
        with f3:
            kamar_options = ["Semua kamar"] + sorted({s["nomor_kamar"] for s in sewa})
            kamar_filter = st.selectbox("Kamar", kamar_options, key="sewa_kamar_filter")

        hasil = []
        for s in sewa:
            teks = f"{s['id_sewa']} {s['nama']} {s['nomor_kamar']} {s['telepon']}".lower()
            if cari and cari.strip().lower() not in teks:
                continue
            if status_filter and s["status_sewa"] not in status_filter:
                continue
            if kamar_filter != "Semua kamar" and s["nomor_kamar"] != kamar_filter:
                continue
            hasil.append(s)

        st.caption(f"Menampilkan **{len(hasil)}** dari **{len(sewa)}** sewa.")
        if hasil:
            rows = []
            for s in hasil:
                prog = logic.payment_progress(s["id_sewa"])
                rows.append(
                    {
                        "ID": s["id_sewa"],
                        "Penghuni": s["nama"],
                        "Kamar": s["nomor_kamar"],
                        "Mulai": ui.fmt_date(s["tanggal_mulai"]),
                        "Selesai": ui.fmt_date(s["tanggal_selesai"]),
                        "Durasi": f"{s['durasi']} bln",
                        "Harga/bln": ui.rupiah(s["harga_bulanan"]),
                        "Dibayar": ui.rupiah(s["total_bayar"]),
                        "Progres": f"{prog['lunas']}/{prog['total']} periode",
                        "Status": "🟢 Aktif" if s["status_sewa"] == "Aktif" else "⚪ Selesai",
                    }
                )
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            ui.empty_state("🔍", "Sewa tidak ditemukan", "Ubah kata kunci atau filter.")

    # ------------------------------------------------------------------
    # BUAT SEWA
    # ------------------------------------------------------------------
    with tab_baru:
        ui.section("Buat sewa baru", "Jadwal yang bertabrakan di kamar yang sama akan ditolak")
        penghuni = db.list_penghuni()
        kamar = db.list_kamar()

        if not penghuni:
            st.warning("Belum ada penghuni. Tambahkan penghuni terlebih dahulu sebelum membuat sewa.")
            if st.button("➕ Buka menu Penghuni", type="primary"):
                ui.goto("Penghuni", tab="➕ Tambah penghuni")
        elif not kamar:
            st.warning("Belum ada data kamar.")
        else:
            tenant_ids = [p["id_penghuni"] for p in penghuni]
            room_ids = [k["id_kamar"] for k in kamar]
            kamar_map = {k["id_kamar"]: k for k in kamar}

            ui.ensure_select(tenant_ids, "sewa_baru_penghuni")
            default_room = next((k["id_kamar"] for k in kamar if k["status"] == "Tersedia"), room_ids[0])
            ui.ensure_select(room_ids, "sewa_baru_kamar", default=default_room)
            if "sewa_baru_harga" not in st.session_state:
                st.session_state["sewa_baru_harga"] = int(
                    kamar_map[st.session_state["sewa_baru_kamar"]]["harga_bulanan"]
                )

            kiri, kanan = st.columns([1.25, 1])
            with kiri:
                id_penghuni = st.selectbox(
                    "Penghuni *",
                    tenant_ids,
                    format_func=lambda x: next(
                        f"{p['nama']} · {p['telepon']}" for p in penghuni if p["id_penghuni"] == x
                    ),
                    key="sewa_baru_penghuni",
                )
                id_kamar = st.selectbox(
                    "Kamar *",
                    room_ids,
                    format_func=lambda x: (
                        f"{kamar_map[x]['nomor_kamar']} · {kamar_map[x]['tipe']} · "
                        f"{ui.rupiah(kamar_map[x]['harga_bulanan'])} · {kamar_map[x]['status']}"
                    ),
                    key="sewa_baru_kamar",
                    on_change=_sync_harga_sewa,
                )
                tanggal_mulai = st.date_input(
                    "Tanggal mulai *", value=date.today(), key="sewa_baru_mulai"
                )
                mode = st.radio(
                    "Penentuan tanggal selesai",
                    ["Durasi otomatis", "Tanggal selesai manual"],
                    horizontal=True,
                    key="sewa_baru_mode",
                )
                if mode == "Durasi otomatis":
                    durasi = st.number_input(
                        "Durasi (bulan) *", min_value=1, max_value=60, value=12,
                        step=1, key="sewa_baru_durasi",
                    )
                    tanggal_selesai = logic.rental_end_date(tanggal_mulai, int(durasi))
                    durasi_final = int(durasi)
                    st.caption(
                        f"Tanggal selesai otomatis: **{ui.fmt_date(tanggal_selesai)}** "
                        f"(inklusif, {durasi_final} bulan)."
                    )
                else:
                    tanggal_selesai = st.date_input(
                        "Tanggal selesai *",
                        value=logic.rental_end_date(tanggal_mulai, 12),
                        key="sewa_baru_selesai",
                    )
                    durasi_final = logic.duration_months(tanggal_mulai, tanggal_selesai)
                    st.caption(f"Durasi terhitung: **{durasi_final} bulan**.")

                harga = st.number_input(
                    "Harga sewa per bulan (Rp) *",
                    min_value=1, step=50_000, key="sewa_baru_harga",
                    help="Harga tersalin saat sewa dibuat dan tidak berubah bila harga kamar berubah.",
                )

                bentrok = []
                if tanggal_selesai > tanggal_mulai:
                    bentrok = logic.check_room_conflict(id_kamar, tanggal_mulai, tanggal_selesai)

                tombol = st.button(
                    "💾 Simpan sewa",
                    type="primary",
                    disabled=bool(bentrok) or tanggal_selesai <= tanggal_mulai,
                    key="sewa_baru_submit",
                )
                if tombol:
                    try:
                        new_id = logic.create_sewa(
                            id_penghuni,
                            id_kamar,
                            tanggal_mulai,
                            tanggal_selesai,
                            harga,
                            durasi_final,
                        )
                        ui.flash(
                            "success",
                            f"Sewa {new_id} berhasil dibuat untuk kamar "
                            f"{kamar_map[id_kamar]['nomor_kamar']}.",
                        )
                        st.rerun()
                    except logic.BusinessError as exc:
                        st.error(str(exc))

            with kanan:
                nama_penghuni = next(
                    p["nama"] for p in penghuni if p["id_penghuni"] == id_penghuni
                )
                kamar_ini = kamar_map[id_kamar]
                total_kontrak = int(harga) * int(max(1, durasi_final))
                konflik_html = ""
                if tanggal_selesai <= tanggal_mulai:
                    konflik_html = (
                        '<div style="background:#fff1f2;border:1px solid #fecdd3;color:#be123c;'
                        'border-radius:12px;padding:10px 12px;font-size:12px;margin-top:10px;">'
                        "❌ Tanggal selesai harus setelah tanggal mulai (B06).</div>"
                    )
                elif bentrok:
                    items = "".join(
                        f"<li>{ui.esc(b['id_sewa'])} · {ui.esc(b['nama'])} · "
                        f"{ui.fmt_date(b['tanggal_mulai'])} s.d. {ui.fmt_date(b['tanggal_selesai'])}</li>"
                        for b in bentrok
                    )
                    konflik_html = (
                        '<div style="background:#fff1f2;border:1px solid #fecdd3;color:#be123c;'
                        'border-radius:12px;padding:10px 12px;font-size:12px;margin-top:10px;">'
                        "❌ Jadwal bertabrakan dengan sewa berikut:<ul style='margin:6px 0 0 16px;'>"
                        f"{items}</ul></div>"
                    )
                else:
                    konflik_html = (
                        '<div style="background:#ecfdf5;border:1px solid #a7f3d0;color:#047857;'
                        'border-radius:12px;padding:10px 12px;font-size:12px;margin-top:10px;">'
                        "✅ Jadwal tersedia, tidak ada bentrok.</div>"
                    )

                st.markdown(
                    f"""
                    <div class="ks-panel">
                      <div class="ks-panel-title">Ringkasan sewa</div>
                      <div class="ks-panel-sub">Periksa sebelum menyimpan</div>
                      <div class="ks-kv" style="grid-template-columns:1fr 1fr;">
                        <div class="ks-kv-item"><div class="ks-kv-label">Penghuni</div>
                          <div class="ks-kv-value">{ui.esc(nama_penghuni)}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Kamar</div>
                          <div class="ks-kv-value">{ui.esc(kamar_ini['nomor_kamar'])} · {ui.esc(kamar_ini['tipe'])}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Mulai</div>
                          <div class="ks-kv-value">{ui.fmt_date(tanggal_mulai)}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Selesai</div>
                          <div class="ks-kv-value">{ui.fmt_date(tanggal_selesai)}</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Durasi</div>
                          <div class="ks-kv-value">{max(1, durasi_final)} bulan</div></div>
                        <div class="ks-kv-item"><div class="ks-kv-label">Harga/bulan</div>
                          <div class="ks-kv-value">{ui.rupiah(harga)}</div></div>
                      </div>
                      <div style="border-top:1px dashed #e2e8f0;margin:12px 0 8px;"></div>
                      <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;">
                        <span>Nilai kontrak</span><b style="color:#0f172a;font-size:14px;">{ui.rupiah(total_kontrak)}</b>
                      </div>
                      {konflik_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")
                with st.expander("📅 Jadwal kamar terpilih"):
                    riwayat_kamar = db.sewa_for_kamar(id_kamar)
                    if riwayat_kamar:
                        rows = [
                            {
                                "ID": s["id_sewa"],
                                "Penghuni": s["nama"],
                                "Mulai": ui.fmt_date(s["tanggal_mulai"]),
                                "Selesai": ui.fmt_date(s["tanggal_selesai"]),
                                "Status": "🟢 Aktif" if s["status_sewa"] == "Aktif" else "⚪ Selesai",
                            }
                            for s in riwayat_kamar
                        ]
                        st.dataframe(rows, hide_index=True, width="stretch")
                    else:
                        st.caption("Kamar ini belum memiliki jadwal sewa.")
                    st.caption(
                        "Aturan bentrok: mulai baru ≤ selesai lama **dan** selesai baru ≥ mulai lama (B06/B15)."
                    )

    # ------------------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------------------
    with tab_detail:
        if not sewa:
            ui.empty_state("📄", "Belum ada sewa", "Buat sewa terlebih dahulu.")
        else:
            opsi = {
                s["id_sewa"]: f"{s['id_sewa']} · {s['nama']} · {s['nomor_kamar']} · {s['status_sewa']}"
                for s in sewa
            }
            ui.apply_pending_selection("selected_sewa", "sewa_detail_pilih", list(opsi))
            ui.ensure_select(list(opsi), "sewa_detail_pilih")
            pilih = st.selectbox(
                "Pilih sewa", list(opsi), format_func=lambda x: opsi[x], key="sewa_detail_pilih"
            )
            s = db.get_sewa(pilih)
            bills = logic.bills_for_sewa(pilih)
            progres = logic.payment_progress(pilih)
            sisa = sum(int(b["nominal"]) for b in bills if b["status"] != "Lunas")
            lunas = sum(int(b["nominal"]) for b in bills if b["status"] == "Lunas")
            mulai = logic.parse_date(s["tanggal_mulai"])
            akhir = logic.parse_date(s["tanggal_selesai"])
            sisa_hari = (akhir - date.today()).days

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 14px;">
                  <div>
                    <div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#0e7490;font-weight:800;">Detail sewa</div>
                    <div style="font-size:26px;font-weight:800;color:#0f172a;letter-spacing:-.5px;">
                      {ui.esc(s['id_sewa'])} · {ui.esc(s['nama'])}
                    </div>
                    <div style="font-size:12px;color:#64748b;">
                      Kamar {ui.esc(s['nomor_kamar'])} ({ui.esc(s['tipe'])}) · {ui.esc(s['telepon'])}
                    </div>
                  </div>
                  <div>{ui.status_badge(s['status_sewa'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            d1, d2, d3, d4 = st.columns(4)
            with d1:
                ui.stat_card("Harga/bulan", ui.rupiah(s["harga_bulanan"]), "Harga terkunci saat kontrak", "💵", "teal")
            with d2:
                ui.stat_card("Nilai kontrak", ui.rupiah(int(s["harga_bulanan"]) * int(s["durasi"])), f"{s['durasi']} bulan", "📄", "indigo")
            with d3:
                ui.stat_card("Sudah dibayar", ui.rupiah(lunas), f"{progres['lunas']} dari {progres['total']} periode", "💰", "green")
            with d4:
                ui.stat_card("Sisa tagihan", ui.rupiah(sisa), f"{progres['belum']} periode belum lunas", "⏰", "rose")

            st.write("")
            ui.progress_bar(progres["persen"], f"Progres pembayaran {progres['lunas']}/{progres['total']} periode")
            ui.kv_grid(
                [
                    ("Penghuni", f"{ui.esc(s['nama'])} <small>· {ui.esc(s['telepon'])}</small>"),
                    ("Kamar", f"{ui.esc(s['nomor_kamar'])} <small>· {ui.esc(s['tipe'])}</small>"),
                    ("Tanggal mulai", ui.fmt_date(s["tanggal_mulai"])),
                    ("Tanggal selesai", ui.fmt_date(s["tanggal_selesai"])),
                    ("Durasi", f"{s['durasi']} bulan"),
                    ("Sisa waktu", f"{max(0, sisa_hari)} hari" if s["status_sewa"] == "Aktif" else "Sewa selesai"),
                ],
                cols=3,
            )

            st.write("")
            ui.section("Tagihan per periode", "Status Lunas, Belum Dibayar, atau Terlambat dihitung otomatis")
            if bills:
                rows = []
                for b in bills:
                    ket = ""
                    if b["status"] == "Terlambat":
                        ket = f"{b['hari_telat']} hari terlambat"
                    elif b["status"] == "Lunas":
                        ket = f"Dibayar {ui.fmt_date(b['tanggal_bayar'])} · {b['id_pembayaran']}"
                    else:
                        ket = "Belum jatuh tempo"
                    rows.append(
                        {
                            "Periode": b["periode"],
                            "Jatuh tempo": ui.fmt_date(b["jatuh_tempo"]),
                            "Nominal": ui.rupiah(b["nominal"]),
                            "Status": {
                                "Lunas": "🟢 Lunas",
                                "Belum Dibayar": "🟡 Belum Dibayar",
                                "Terlambat": "🔴 Terlambat",
                            }[b["status"]],
                            "Keterangan": ket,
                        }
                    )
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("🧾", "Belum ada periode tagihan", "Periksa tanggal sewa.")

            st.write("")
            with st.expander("💳 Catat pembayaran untuk sewa ini", expanded=False):
                components.payment_form(s, f"sewa_{s['id_sewa']}")

            st.write("")
            ui.section("Riwayat pembayaran", "Transaksi yang tercatat untuk sewa ini")
            pembayaran = logic.db.pembayaran_for_sewa(pilih)
            if pembayaran:
                rows = [
                    {
                        "ID": b["id_pembayaran"],
                        "Tanggal": ui.fmt_date(b["tanggal_bayar"]),
                        "Periode": f"{logic.month_label(b['periode_bulan'])} {b['periode_tahun']}",
                        "Nominal": ui.rupiah(b["nominal"]),
                        "Status": "🟢 Lunas",
                    }
                    for b in pembayaran
                ]
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("💳", "Belum ada pembayaran", "Gunakan form di atas untuk mencatat pembayaran.")

            # ---------------- Aksi ----------------
            st.write("")
            ui.section("Aksi sewa", "Akhiri, ubah, atau hapus kontrak")

            if s["status_sewa"] == "Aktif":
                with st.expander("⏹️ Akhiri sewa lebih awal"):
                    st.caption(
                        "Sewa yang berhenti lebih awal diubah statusnya menjadi Selesai. "
                        "Tanggal selesai akan mengikuti tanggal berhenti."
                    )
                    default_akhir = max(date.today(), mulai)
                    tgl_akhir = st.date_input(
                        "Tanggal berhenti", value=default_akhir,
                        key=f"akhiri_tanggal_{s['id_sewa']}",
                    )
                    cek_akhir = st.checkbox(
                        f"Saya yakin mengakhiri sewa {s['id_sewa']} pada {ui.fmt_date(tgl_akhir)}.",
                        key=f"akhiri_cek_{s['id_sewa']}",
                    )
                    if st.button(
                        "Akhiri sewa", type="primary", disabled=not cek_akhir,
                        key=f"akhiri_btn_{s['id_sewa']}",
                    ):
                        try:
                            logic.end_sewa(s["id_sewa"], tgl_akhir)
                            ui.flash("success", f"Sewa {s['id_sewa']} telah diakhiri.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))

            with st.expander("✏️ Ubah tanggal & harga sewa"):
                ada_bayar = int(s["jml_bayar"] or 0) > 0
                if ada_bayar:
                    st.info(
                        "Sewa ini sudah memiliki pembayaran. Tanggal mulai dan harga dikunci agar "
                        "riwayat tidak berubah. Tanggal selesai hanya dapat diperpanjang."
                    )
                with st.form(f"form_edit_sewa_{s['id_sewa']}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        e_mulai = st.date_input(
                            "Tanggal mulai", value=mulai, disabled=ada_bayar,
                            key=f"edit_mulai_{s['id_sewa']}",
                        )
                    with e2:
                        e_selesai = st.date_input(
                            "Tanggal selesai", value=akhir,
                            key=f"edit_selesai_{s['id_sewa']}",
                        )
                    e_harga = st.number_input(
                        "Harga per bulan (Rp)", min_value=1, step=50_000,
                        value=int(s["harga_bulanan"]), disabled=ada_bayar,
                        key=f"edit_harga_{s['id_sewa']}",
                    )
                    st.caption(
                        f"Durasi saat ini {s['durasi']} bulan. Setelah diubah, durasi dihitung ulang "
                        "dari tanggal dan jadwal bentrok diperiksa kembali."
                    )
                    if st.form_submit_button("Simpan perubahan", type="primary"):
                        try:
                            logic.update_sewa(
                                s["id_sewa"], e_mulai, e_selesai, e_harga,
                                logic.duration_months(e_mulai, e_selesai),
                            )
                            ui.flash("success", f"Sewa {s['id_sewa']} berhasil diperbarui.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))

            with st.expander("🗑️ Hapus sewa"):
                if int(s["jml_bayar"] or 0) > 0:
                    st.warning(
                        f"Sewa ini memiliki **{s['jml_bayar']} pembayaran** sehingga tidak bisa dihapus. "
                        "Hapus pembayaran terlebih dahulu bila memang salah catat."
                    )
                else:
                    st.caption("Sewa ini belum memiliki pembayaran sehingga boleh dihapus.")
                    cek_hapus = st.checkbox(
                        f"Saya yakin ingin menghapus sewa {s['id_sewa']}.",
                        key=f"hapus_sewa_cek_{s['id_sewa']}",
                    )
                    if st.button(
                        "Hapus sewa permanen", type="primary", disabled=not cek_hapus,
                        key=f"hapus_sewa_btn_{s['id_sewa']}",
                    ):
                        try:
                            logic.delete_sewa(s["id_sewa"])
                            ui.flash("success", f"Sewa {s['id_sewa']} berhasil dihapus.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))
