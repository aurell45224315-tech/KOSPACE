"""Halaman Pengelolaan Penghuni."""

import streamlit as st

from .. import db, logic, ui


def render() -> None:
    penghuni = db.list_penghuni()
    aktif = sum(1 for p in penghuni if p["kamar_aktif"])
    tidak_aktif = len(penghuni) - aktif
    total_sewa = sum(int(p["total_sewa"] or 0) for p in penghuni)

    ui.page_header("👤", "Pengelolaan Penghuni", "Identitas penghuni dan riwayat huniannya")
    ui.show_flash()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.stat_card("Total penghuni", str(len(penghuni)), "Seluruh yang pernah tercatat", "👤", "teal")
    with c2:
        ui.stat_card("Sedang menempati", str(aktif), "Punya sewa aktif", "🏠", "green")
    with c3:
        ui.stat_card("Tidak menempati", str(tidak_aktif), "Belum punya sewa aktif", "🚪", "slate")
    with c4:
        ui.stat_card("Total kontrak", str(total_sewa), "Akumulasi riwayat sewa", "📄", "indigo")

    st.write("")
    tab_daftar, tab_tambah, tab_detail = ui.tabbed(
        "Penghuni", ["📋 Daftar penghuni", "➕ Tambah penghuni", "🔎 Detail & ubah"]
    )

    # ------------------------------------------------------------------
    # DAFTAR
    # ------------------------------------------------------------------
    with tab_daftar:
        ui.section("Daftar penghuni", "Cari berdasarkan nama, nomor telepon, atau kamar")
        f1, f2 = st.columns([2, 1.4])
        with f1:
            cari = st.text_input(
                "Cari penghuni", placeholder="Nama, telepon, atau nomor kamar",
                key="penghuni_cari",
            )
        with f2:
            status = st.multiselect(
                "Status hunian", ["Menempati", "Tidak menempati"],
                default=["Menempati", "Tidak menempati"], key="penghuni_status",
            )

        hasil = []
        for p in penghuni:
            label_status = "Menempati" if p["kamar_aktif"] else "Tidak menempati"
            teks = " ".join(
                str(p.get(x) or "") for x in ("nama", "telepon", "telepon_ortu", "alamat", "kamar_aktif")
            ).lower()
            if cari and cari.strip().lower() not in teks:
                continue
            if status and label_status not in status:
                continue
            hasil.append((p, label_status))

        st.caption(f"Menampilkan **{len(hasil)}** dari **{len(penghuni)}** penghuni.")
        if hasil:
            rows = []
            for p, label_status in hasil:
                rows.append(
                    {
                        "ID": p["id_penghuni"],
                        "Nama": p["nama"],
                        "Telepon": p["telepon"],
                        "Telepon orang tua": p["telepon_ortu"] or "—",
                        "Alamat": p["alamat"] or "—",
                        "Kamar": p["kamar_aktif"] or "—",
                        "Status": "🟢 Menempati" if p["kamar_aktif"] else "⚪ Tidak menempati",
                    }
                )
            st.dataframe(
                rows, hide_index=True, width="stretch",
                column_config={
                    "ID": st.column_config.TextColumn(width="small"),
                    "Nama": st.column_config.TextColumn(width="medium"),
                    "Alamat": st.column_config.TextColumn(width="large"),
                    "Status": st.column_config.TextColumn(width="small"),
                },
            )
        else:
            ui.empty_state("🔍", "Penghuni tidak ditemukan", "Ubah kata kunci atau filter status.")

    # ------------------------------------------------------------------
    # TAMBAH
    # ------------------------------------------------------------------
    with tab_tambah:
        versi = st.session_state.setdefault("penghuni_add_versi", 0)
        ui.section("Tambah penghuni baru", "Nama dan nomor telepon wajib diisi")
        kiri, kanan = st.columns([1.35, 1])
        with kiri:
            nama = st.text_input("Nama lengkap *", key=f"penghuni_add_nama_{versi}")
            telepon = st.text_input(
                "Nomor telepon *", key=f"penghuni_add_telp_{versi}",
                placeholder="Contoh: 081234567890",
            )
            telepon_ortu = st.text_input(
                "Nomor telepon orang tua", key=f"penghuni_add_ortu_{versi}",
                placeholder="Opsional",
            )
            alamat = st.text_area(
                "Alamat", key=f"penghuni_add_alamat_{versi}", height=90,
                placeholder="Opsional, alamat asal penghuni",
            )
            if st.button("💾 Simpan penghuni", type="primary", key=f"penghuni_add_btn_{versi}"):
                try:
                    new_id = logic.create_penghuni(nama, telepon, telepon_ortu, alamat)
                    st.session_state["penghuni_add_versi"] = versi + 1
                    ui.flash("success", f"Penghuni baru berhasil disimpan dengan ID {new_id}.")
                    st.rerun()
                except logic.BusinessError as exc:
                    st.error(str(exc))
        with kanan:
            ui.panel(
                "Kenapa nomor orang tua dicatat?",
                "Untuk keperluan darurat",
                """
                <div style="font-size:12.5px;color:#475569;line-height:1.65;">
                  Sistem administrasi kos milik pemilik, bukan penghuni. Nomor telepon orang tua
                  membantu pemilik menghubungi keluarga bila diperlukan. Kolom ini opsional,
                  tetapi sangat disarankan untuk diisi.
                  <br><br>
                  Penghuni yang sudah memiliki riwayat sewa <b>tidak bisa dihapus</b> (B10),
                  sehingga riwayat administrasinya tetap utuh.
                </div>
                """,
            )

    # ------------------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------------------
    with tab_detail:
        if not penghuni:
            ui.empty_state("👤", "Belum ada penghuni", "Tambahkan penghuni terlebih dahulu.")
        else:
            opsi = {
                p["id_penghuni"]: f"{p['nama']} · {p['kamar_aktif'] or 'belum menempati kamar'}"
                for p in penghuni
            }
            ui.apply_pending_selection("selected_penghuni", "penghuni_detail_pilih", list(opsi))
            ui.ensure_select(list(opsi), "penghuni_detail_pilih")
            pilih = st.selectbox(
                "Pilih penghuni", list(opsi), format_func=lambda x: opsi[x],
                key="penghuni_detail_pilih",
            )
            p = db.get_penghuni(pilih)
            fin = logic.tenant_financials(pilih)

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 14px;">
                  <div>
                    <div style="font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#0e7490;font-weight:800;">Profil penghuni</div>
                    <div style="font-size:26px;font-weight:800;color:#0f172a;letter-spacing:-.5px;">{ui.esc(p['nama'])}</div>
                    <div style="font-size:12px;color:#64748b;">ID {ui.esc(p['id_penghuni'])} · {ui.esc(p['telepon'])}</div>
                  </div>
                  <div>{ui.status_badge('Aktif') if p['kamar_aktif'] else ui.badge('Tidak menempati', 'slate')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            d1, d2, d3 = st.columns(3)
            with d1:
                ui.stat_card("Total kontrak", str(fin["jumlah_sewa"]), "Riwayat sewa", "📄", "indigo")
            with d2:
                ui.stat_card("Total dibayar", ui.rupiah(fin["total_bayar"]), "Akumulasi pembayaran", "💰", "green")
            with d3:
                ui.stat_card("Tunggakan", ui.rupiah(fin["tunggakan"]), f"Belum bayar {ui.rupiah(fin['belum_bayar'])}", "⏰", "rose")

            st.write("")
            ui.kv_grid(
                [
                    ("Nomor telepon", ui.esc(p["telepon"])),
                    ("Telepon orang tua", ui.esc(p["telepon_ortu"] or "—")),
                    ("Kamar saat ini", ui.esc(p["kamar_aktif"] or "Belum menempati kamar")),
                    ("Alamat", ui.esc(p["alamat"] or "—")),
                ],
                cols=2,
            )

            if p["kamar_aktif"] and p["sewa_aktif"]:
                st.write("")
                sewa = db.get_sewa(p["sewa_aktif"])
                st.markdown(
                    f"""
                    <div class="ks-panel">
                      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">
                        <div>
                          <div class="ks-panel-title">🏠 Sewa aktif</div>
                          <div class="ks-panel-sub">{ui.esc(sewa['id_sewa'])} · kamar {ui.esc(sewa['nomor_kamar'])} ({ui.esc(sewa['tipe'])})</div>
                          <div style="font-size:12px;color:#334155;">
                            {ui.fmt_date(sewa['tanggal_mulai'])} s.d. {ui.fmt_date(sewa['tanggal_selesai'])}
                            · {sewa['durasi']} bulan · {ui.rupiah(sewa['harga_bulanan'])}/bulan
                          </div>
                        </div>
                        <div>{ui.status_badge('Aktif')}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Buka detail sewa", key=f"penghuni_ke_sewa_{p['id_penghuni']}"):
                    ui.goto("Sewa", tab="🔎 Detail & aksi", selected_sewa=p["sewa_aktif"])

            st.write("")
            ui.section("Riwayat sewa", "Semua kontrak yang tercatat untuk penghuni ini")
            if fin["sewa"]:
                rows = [
                    {
                        "ID": s["id_sewa"],
                        "Kamar": s["nomor_kamar"],
                        "Mulai": ui.fmt_date(s["tanggal_mulai"]),
                        "Selesai": ui.fmt_date(s["tanggal_selesai"]),
                        "Durasi": f"{s['durasi']} bln",
                        "Harga/bln": ui.rupiah(s["harga_bulanan"]),
                        "Status": "🟢 Aktif" if s["status_sewa"] == "Aktif" else "⚪ Selesai",
                    }
                    for s in fin["sewa"]
                ]
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("📄", "Belum ada riwayat sewa", "Penghuni ini belum pernah menyewa kamar.")

            st.write("")
            ui.section("Riwayat pembayaran", "Pembayaran yang pernah dilakukan penghuni ini")
            if fin["pembayaran"]:
                rows = [
                    {
                        "ID": b["id_pembayaran"],
                        "Tanggal": ui.fmt_date(b["tanggal_bayar"]),
                        "Kamar": b["nomor_kamar"],
                        "Periode": f"{logic.month_label(b['periode_bulan'])} {b['periode_tahun']}",
                        "Nominal": ui.rupiah(b["nominal"]),
                        "Status": "🟢 Lunas",
                    }
                    for b in fin["pembayaran"]
                ]
                st.dataframe(rows, hide_index=True, width="stretch")
            else:
                ui.empty_state("💳", "Belum ada pembayaran", "Belum ada transaksi untuk penghuni ini.")

            st.write("")
            with st.expander("✏️ Ubah data penghuni"):
                with st.form(f"form_edit_penghuni_{p['id_penghuni']}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        e_nama = st.text_input("Nama lengkap", value=p["nama"])
                        e_telp = st.text_input("Nomor telepon", value=p["telepon"])
                    with e2:
                        e_ortu = st.text_input("Telepon orang tua", value=p["telepon_ortu"] or "")
                        e_alamat = st.text_area("Alamat", value=p["alamat"] or "", height=80)
                    if st.form_submit_button("Simpan perubahan", type="primary"):
                        try:
                            logic.update_penghuni(p["id_penghuni"], e_nama, e_telp, e_ortu, e_alamat)
                            ui.flash("success", f"Data penghuni {e_nama} berhasil diperbarui.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))

            with st.expander("🗑️ Hapus penghuni"):
                if p["total_sewa"]:
                    st.warning(
                        f"Penghuni ini memiliki **{p['total_sewa']} catatan sewa** sehingga tidak bisa "
                        "dihapus (B10). Riwayatnya tetap dapat ditelusuri lewat menu Riwayat."
                    )
                else:
                    konfirmasi = st.checkbox(
                        f"Saya yakin ingin menghapus {p['nama']}.",
                        key=f"hapus_penghuni_cek_{p['id_penghuni']}",
                    )
                    if st.button(
                        "Hapus penghuni permanen", type="primary",
                        disabled=not konfirmasi, key=f"hapus_penghuni_btn_{p['id_penghuni']}",
                    ):
                        try:
                            logic.delete_penghuni(p["id_penghuni"])
                            ui.flash("success", f"Penghuni {p['nama']} berhasil dihapus.")
                            st.rerun()
                        except logic.BusinessError as exc:
                            st.error(str(exc))
