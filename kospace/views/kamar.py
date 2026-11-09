"""Halaman Pengelolaan Kamar."""

from datetime import date

import streamlit as st

from .. import db, logic, ui

ROOM_DEFAULT_TIPE = "Tipe A"


def _sync_tipe_kamar(versi: int) -> None:
    tipe = st.session_state.get(f"kamar_add_tipe_{versi}", ROOM_DEFAULT_TIPE)
    data = logic.ROOM_DEFAULTS.get(tipe, logic.ROOM_DEFAULTS[ROOM_DEFAULT_TIPE])
    st.session_state[f"kamar_add_harga_{versi}"] = data["harga"]
    st.session_state[f"kamar_add_fasilitas_{versi}"] = data["fasilitas"]


def _siapkan_tambah_kamar(versi: int) -> None:
    kunci_tipe = f"kamar_add_tipe_{versi}"
    if kunci_tipe not in st.session_state:
        st.session_state[kunci_tipe] = ROOM_DEFAULT_TIPE
        st.session_state[f"kamar_add_harga_{versi}"] = logic.ROOM_DEFAULTS[ROOM_DEFAULT_TIPE]["harga"]
        st.session_state[f"kamar_add_fasilitas_{versi}"] = logic.ROOM_DEFAULTS[ROOM_DEFAULT_TIPE]["fasilitas"]


def render() -> None:
    kamar = db.list_kamar()
    tersedia = sum(1 for k in kamar if k["status"] == "Tersedia")
    ditempati = len(kamar) - tersedia
    rata = sum(int(k["harga_bulanan"]) for k in kamar) // len(kamar) if kamar else 0

    ui.page_header("🚪", "Pengelolaan Kamar", "Data kamar, harga, fasilitas, dan status hunian")
    ui.show_flash()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.stat_card("Total kamar", str(len(kamar)), "A01–C10", "🚪", "teal")
    with c2:
        ui.stat_card("Tersedia", str(tersedia), "Siap dihuni", "✅", "green")
    with c3:
        ui.stat_card("Ditempati", str(ditempati), "Ada sewa aktif", "👥", "indigo")
    with c4:
        ui.stat_card("Rata-rata harga", ui.rupiah(rata), "Per bulan", "💵", "amber")

    st.write("")
    tab_daftar, tab_tambah, tab_detail = ui.tabbed(
        "Kamar", ["📋 Daftar kamar", "➕ Tambah kamar", "🔎 Detail & ubah"]
    )

    # ------------------------------------------------------------------
    # DAFTAR
    # ------------------------------------------------------------------
    with tab_daftar:
        ui.section("Daftar seluruh kamar", "Status diperbarui otomatis dari sewa yang aktif")
        f1, f2, f3 = st.columns([2, 1.2, 1.2])
        with f1:
            cari = st.text_input("Cari nomor kamar", placeholder="Contoh: A01", key="kamar_cari")
        with f2:
            tipe_filter = st.multiselect(
                "Tipe kamar", logic.ROOM_TYPES, default=logic.ROOM_TYPES, key="kamar_filter_tipe"
            )
        with f3:
            status_filter = st.multiselect(
                "Status", ["Tersedia", "Ditempati"], default=["Tersedia", "Ditempati"],
                key="kamar_filter_status",
            )

        hasil = [
            k for k in kamar
            if (not cari or cari.strip().upper() in k["nomor_kamar"])
            and (not tipe_filter or k["tipe"] in tipe_filter)
            and (not status_filter or k["status"] in status_filter)
        ]
        st.caption(f"Menampilkan **{len(hasil)}** dari **{len(kamar)}** kamar.")

        if hasil:
            rows = []
            for k in hasil:
                rows.append(
                    {
                        "Nomor": k["nomor_kamar"],
                        "Tipe": k["tipe"],
                        "Harga/bulan": ui.rupiah(k["harga_bulanan"]),
                        "Fasilitas": k["fasilitas"],
                        "Status": "🟢 Tersedia" if k["status"] == "Tersedia" else "🔵 Ditempati",
                        "Penghuni aktif": k["penghuni_aktif"] or "—",
                    }
                )
            st.dataframe(
                rows,
                hide_index=True,
                width="stretch",
                column_config={
                    "Nomor": st.column_config.TextColumn(width="small"),
                    "Tipe": st.column_config.TextColumn(width="small"),
                    "Harga/bulan": st.column_config.TextColumn(width="small"),
                    "Fasilitas": st.column_config.TextColumn(width="large"),
                    "Status": st.column_config.TextColumn(width="small"),
                    "Penghuni aktif": st.column_config.TextColumn(width="medium"),
                },
            )
        else:
            ui.empty_state("🔍", "Kamar tidak ditemukan", "Ubah kata kunci atau filter.")

        st.write("")
        ui.section("Rekap per tipe", "Jumlah unit dan potensi pendapatan")
        rekap = []
        for tipe in logic.ROOM_TYPES:
            subset = [k for k in kamar if k["tipe"] == tipe]
            isi = sum(1 for k in subset if k["status"] == "Ditempati")
            rekap.append(
                {
                    "Tipe": tipe,
                    "Jumlah": len(subset),
                    "Ditempati": isi,
                    "Tersedia": len(subset) - isi,
                    "Harga standar": ui.rupiah(logic.ROOM_DEFAULTS[tipe]["harga"]),
                    "Fasilitas": logic.ROOM_DEFAULTS[tipe]["fasilitas"],
                }
            )
        st.dataframe(rekap, hide_index=True, width="stretch")

    # ------------------------------------------------------------------
    # TAMBAH
    # ------------------------------------------------------------------
    with tab_tambah:
        ui.section("Tambah kamar baru", "Nomor kamar harus unik dan tidak boleh sama dengan kamar lain (B01)")
        versi = st.session_state.setdefault("kamar_add_versi", 0)
        _siapkan_tambah_kamar(versi)
        kiri, kanan = st.columns([1.35, 1])
        with kiri:
            nomor = st.text_input(
                "Nomor kamar *", placeholder="Contoh: A26", key=f"kamar_add_nomor_{versi}",
                help="Kode yang dikenal pemilik, misalnya A01, B11, atau C10.",
            )
            tipe = st.selectbox(
                "Tipe kamar *", logic.ROOM_TYPES, key=f"kamar_add_tipe_{versi}",
                on_change=_sync_tipe_kamar, args=(versi,),
            )
            harga = st.number_input(
                "Harga bulanan (Rp) *", min_value=1, step=50_000,
                key=f"kamar_add_harga_{versi}",
            )
            fasilitas = st.text_area(
                "Fasilitas *", key=f"kamar_add_fasilitas_{versi}", height=90,
                help="Pisahkan dengan koma, misalnya: AC, Wi-Fi, kamar mandi dalam.",
            )
            if st.button("💾 Simpan kamar", type="primary", key=f"kamar_add_submit_{versi}"):
                try:
                    new_id = logic.create_kamar(nomor, tipe, harga, fasilitas)
                    st.session_state["kamar_add_versi"] = versi + 1
                    ui.flash("success", f"Kamar baru berhasil disimpan dengan ID {new_id}.")
                    st.rerun()
                except logic.BusinessError as exc:
                    st.error(str(exc))
        with kanan:
            ui.panel(
                "Panduan tipe kamar",
                "Standar KOSPACE",
                f"""
                <div class="ks-panel-sub" style="margin-top:8px;">
                  <b>Tipe A</b> · AC, Wi-Fi, kamar mandi dalam · {ui.rupiah(1_300_000)}<br><br>
                  <b>Tipe B</b> · AC, Wi-Fi, kamar mandi luar · {ui.rupiah(950_000)}<br><br>
                  <b>Tipe C</b> · kipas angin, Wi-Fi, kamar mandi luar · {ui.rupiah(700_000)}
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:14px;">
                  Status kamar baru otomatis <b>Tersedia</b>. Status akan berubah menjadi
                  <b>Ditempati</b> ketika ada sewa aktif yang mencakup tanggal hari ini.
                </div>
                """,
            )

    # ------------------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------------------
    with tab_detail:
        if not kamar:
            ui.empty_state("🚪", "Belum ada kamar", "Tambahkan kamar terlebih dahulu.")
        else:
            opsi = {k["id_kamar"]: f"{k['nomor_kamar']} · {k['tipe']} · {k['status']}" for k in kamar}
            ui.apply_pending_selection("selected_kamar", "kamar_detail_pilih", list(opsi))
            ui.ensure_select(list(opsi), "kamar_detail_pilih")
            pilih = st.selectbox(
                "Pilih kamar", list(opsi), format_func=lambda x: opsi[x],
                key="kamar_detail_pilih",
            )
            k = db.get_kamar(pilih)
            finansial = logic.room_financials(pilih)

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 14px;">
                  <div>
                    <div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#0e7490;font-weight:800;">Detail kamar</div>
                    <div style="font-size:28px;font-weight:800;color:#0f172a;letter-spacing:-.5px;">Kamar {ui.esc(k['nomor_kamar'])}</div>
                    <div style="font-size:12px;color:#64748b;">{ui.esc(k['tipe'])} · ID {ui.esc(k['id_kamar'])}</div>
                  </div>
                  <div>{ui.status_badge(k['status'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            d1, d2, d3 = st.columns(3)
            with d1:
                ui.stat_card("Harga bulanan", ui.rupiah(k["harga_bulanan"]), "Harga berlaku saat ini", "💵", "teal")
            with d2:
                ui.stat_card("Total sewa", str(finansial["jumlah_sewa"]), "Riwayat kontrak", "📄", "indigo")
            with d3:
                ui.stat_card("Total pendapatan", ui.rupiah(finansial["total_pendapatan"]), f"Tunggakan {ui.rupiah(finansial['tunggakan'])}", "💰", "green")

            st.write("")
            ui.kv_grid(
                [
                    ("Fasilitas", ui.esc(k["fasilitas"])),
                    ("Status kamar", ui.status_badge(k["status"])),
                    ("Penghuni aktif", ui.esc(k["penghuni_aktif"] or "Belum ada")),
                    ("ID sewa aktif", ui.esc(k["sewa_aktif"] or "—")),
                ],
                cols=2,
            )
            st.write("")

            if k["penghuni_aktif"] and k["sewa_aktif"]:
                sewa_aktif = db.get_sewa(k["sewa_aktif"])
                sisa = (logic.parse_date(sewa_aktif["tanggal_selesai"]) - date.today()).days
                st.markdown(
                    f"""
                    <div class="ks-panel">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
                        <div>
                          <div class="ks-panel-title">👤 Penghuni saat ini</div>
                          <div class="ks-panel-sub">{ui.esc(sewa_aktif['nama'])} · {ui.esc(sewa_aktif['telepon'])}</div>
                          <div style="font-size:12px;color:#334155;">
                            {ui.fmt_date(sewa_aktif['tanggal_mulai'])} s.d. {ui.fmt_date(sewa_aktif['tanggal_selesai'])}
                            · {sewa_aktif['durasi']} bulan · {ui.rupiah(sewa_aktif['harga_bulanan'])}/bulan
                          </div>
                        </div>
                        <div style="text-align:right;">
                          {ui.status_badge('Aktif')}
                          <div style="font-size:11px;color:#64748b;margin-top:5px;">Sisa {max(0, sisa)} hari</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Buka detail sewa", key="kamar_ke_sewa"):
                    ui.goto("Sewa", tab="🔎 Detail & aksi", selected_sewa=k["sewa_aktif"])

            st.write("")
            ui.section("Riwayat sewa kamar ini", "Seluruh kontrak yang pernah tercatat")
            if finansial["sewa"]:
                rows = [
                    {
                        "ID": s["id_sewa"],
                        "Penghuni": s["nama"],
                        "Mulai": ui.fmt_date(s["tanggal_mulai"]),
                        "Selesai": ui.fmt_date(s["tanggal_selesai"]),
                        "Durasi": f"{s['durasi']} bln",
                        "Harga/bln": ui.rupiah(s["harga_bulanan"]),
                        "Status": "🟢 Aktif" if s["status_sewa"] == "Aktif" else "⚪ Selesai",
                    }
                    for s in finansial["sewa"]
                ]
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("📄", "Belum pernah disewa", "Kamar ini belum memiliki riwayat sewa.")

            st.write("")
            with st.expander("✏️ Ubah data kamar"):
                with st.form(f"form_edit_kamar_{k['id_kamar']}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        e_nomor = st.text_input("Nomor kamar", value=k["nomor_kamar"])
                        e_tipe = st.selectbox(
                            "Tipe", logic.ROOM_TYPES,
                            index=logic.ROOM_TYPES.index(k["tipe"]) if k["tipe"] in logic.ROOM_TYPES else 0,
                        )
                    with e2:
                        e_harga = st.number_input(
                            "Harga bulanan (Rp)", min_value=1, step=50_000,
                            value=int(k["harga_bulanan"]),
                        )
                    e_fas = st.text_area("Fasilitas", value=k["fasilitas"], height=85)
                    st.caption(
                        "Perubahan harga kamar tidak mengubah harga pada sewa yang sudah ada. "
                        "Harga sewa tersalin saat kontrak dibuat."
                    )
                    if st.form_submit_button("Simpan perubahan", type="primary"):
                        try:
                            logic.update_kamar(k["id_kamar"], e_nomor, e_tipe, e_harga, e_fas)
                            ui.flash("success", f"Data kamar {e_nomor} berhasil diperbarui.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))

            with st.expander("🗑️ Hapus kamar"):
                if k["total_sewa"]:
                    st.warning(
                        f"Kamar ini memiliki **{k['total_sewa']} riwayat sewa** sehingga tidak bisa "
                        "dihapus (B10). Riwayat sewa dan pembayaran harus tetap utuh."
                    )
                else:
                    st.caption("Kamar ini belum memiliki riwayat sewa sehingga boleh dihapus.")
                    konfirmasi = st.checkbox(
                        f"Saya yakin ingin menghapus kamar {k['nomor_kamar']}.",
                        key=f"hapus_kamar_cek_{k['id_kamar']}",
                    )
                    if st.button(
                        "Hapus kamar permanen", type="primary",
                        disabled=not konfirmasi, key=f"hapus_kamar_btn_{k['id_kamar']}",
                    ):
                        try:
                            logic.delete_kamar(k["id_kamar"])
                            ui.flash("success", f"Kamar {k['nomor_kamar']} berhasil dihapus.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))
