"""Halaman Pengaturan, ekspor data, dan dokumentasi aturan."""

import io
import zipfile

import pandas as pd
import streamlit as st

from .. import db, logic, ui


def _csv(rows: list[dict]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def _zip_semua() -> bytes:
    kamar = [
        {
            "id_kamar": k["id_kamar"], "nomor_kamar": k["nomor_kamar"], "tipe": k["tipe"],
            "harga_bulanan": k["harga_bulanan"], "fasilitas": k["fasilitas"], "status": k["status"],
        }
        for k in db.list_kamar()
    ]
    penghuni = [
        {
            "id_penghuni": p["id_penghuni"], "nama": p["nama"], "telepon": p["telepon"],
            "telepon_ortu": p["telepon_ortu"], "alamat": p["alamat"],
        }
        for p in db.list_penghuni()
    ]
    sewa = [
        {
            "id_sewa": s["id_sewa"], "id_penghuni": s["id_penghuni"], "nama": s["nama"],
            "id_kamar": s["id_kamar"], "nomor_kamar": s["nomor_kamar"],
            "tanggal_mulai": s["tanggal_mulai"], "tanggal_selesai": s["tanggal_selesai"],
            "durasi": s["durasi"], "harga_bulanan": s["harga_bulanan"],
            "status_sewa": s["status_sewa"],
        }
        for s in db.list_sewa()
    ]
    pembayaran = [
        {
            "id_pembayaran": p["id_pembayaran"], "id_sewa": p["id_sewa"],
            "periode_bulan": p["periode_bulan"], "periode_tahun": p["periode_tahun"],
            "tanggal_bayar": p["tanggal_bayar"], "nominal": p["nominal"],
            "status_pembayaran": p["status_pembayaran"],
        }
        for p in db.list_pembayaran()
    ]
    tagihan = [
        {
            "id_sewa": b["id_sewa"], "penghuni": b["nama"], "kamar": b["nomor_kamar"],
            "periode_bulan": b["bulan"], "periode_tahun": b["tahun"],
            "jatuh_tempo": b["jatuh_tempo"], "nominal": b["nominal"], "status": b["status"],
        }
        for b in logic.build_bills()
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as arsip:
        for nama, rows in [
            ("kamar.csv", kamar),
            ("penghuni.csv", penghuni),
            ("sewa.csv", sewa),
            ("pembayaran.csv", pembayaran),
            ("tagihan.csv", tagihan),
        ]:
            arsip.writestr(nama, pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"))
    return buffer.getvalue()


def render() -> None:
    info = db.database_info()
    ui.page_header("⚙️", "Pengaturan", "Database, ekspor data, dan aturan bisnis KOSPACE")
    ui.show_flash()

    st.markdown(
        f"""
        <div style="background:#fff;border:1px solid #e6edf0;border-radius:16px;padding:16px 18px;margin-bottom:14px;
                    display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;align-items:center;">
          <div>
            <div style="font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#0e7490;font-weight:800;">Lokasi database</div>
            <div style="font-family:monospace;font-size:12.5px;color:#334155;margin-top:3px;">{ui.esc(info['path'])}</div>
          </div>
          <div style="font-size:12px;color:#64748b;">SQLite · {info['size_kb']} KB · 4 tabel utama + log</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.stat_card("Kamar", str(info["kamar"]), "Baris pada tabel kamar", "🚪", "teal")
    with c2:
        ui.stat_card("Penghuni", str(info["penghuni"]), "Baris pada tabel penghuni", "👤", "indigo")
    with c3:
        ui.stat_card("Sewa", str(info["sewa"]), "Baris pada tabel sewa", "📄", "amber")
    with c4:
        ui.stat_card("Pembayaran", str(info["pembayaran"]), "Baris pada tabel pembayaran", "💳", "green")

    st.write("")
    tab_db, tab_ekspor, tab_aturan, tab_tentang = ui.tabbed(
        "Pengaturan", ["🗄️ Database", "⬇️ Ekspor data", "📖 Aturan bisnis", "ℹ️ Tentang"]
    )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    with tab_db:
        ui.section("Pemeliharaan database", "Semua tindakan di bawah bersifat permanen")
        kiri, kanan = st.columns(2)

        with kiri:
            with st.container(border=True):
                st.markdown("**🎬 Muat ulang data contoh**")
                st.caption(
                    "Menghapus seluruh sewa, pembayaran, dan penghuni, lalu mengisi ulang data contoh "
                    "yang tanggalnya relatif terhadap hari ini. 25 kamar tetap dipertahankan."
                )
                cek_demo = st.checkbox("Saya memahami data transaksi akan diganti.", key="cek_demo")
                if st.button(
                    "Muat data contoh", type="primary", disabled=not cek_demo, key="btn_demo"
                ):
                    logic.seed_demo()
                    ui.flash("success", "Data contoh berhasil dimuat ulang.")
                    st.rerun()

            with st.container(border=True):
                st.markdown("**🧹 Hapus semua sewa & pembayaran**")
                st.caption(
                    "Kamar dan penghuni tetap disimpan. Berguna untuk memulai administrasi baru "
                    "tanpa menghapus master data."
                )
                cek_trans = st.checkbox("Saya memahami seluruh sewa dan pembayaran akan dihapus.", key="cek_trans")
                if st.button(
                    "Hapus transaksi", disabled=not cek_trans, key="btn_trans"
                ):
                    logic.reset_transactions()
                    ui.flash("success", "Seluruh sewa dan pembayaran telah dihapus.")
                    st.rerun()

        with kanan:
            with st.container(border=True):
                st.markdown("**🧍 Bersihkan penghuni tanpa riwayat**")
                st.caption(
                    "Menghapus penghuni yang belum pernah memiliki sewa. Penghuni dengan riwayat "
                    "sewa tidak akan tersentuh."
                )
                cek_orang = st.checkbox("Saya memahami tindakan ini.", key="cek_orang")
                if st.button(
                    "Bersihkan penghuni", disabled=not cek_orang, key="btn_orang"
                ):
                    logic.clear_tenants()
                    ui.flash("success", "Penghuni tanpa riwayat sewa telah dibersihkan.")
                    st.rerun()

            with st.container(border=True):
                st.markdown("**⚠️ Reset total database**")
                st.caption(
                    "Menghapus **semua** data (kamar, penghuni, sewa, pembayaran, log) lalu membuat "
                    "ulang 25 kamar kosong. Tindakan ini tidak dapat dibatalkan."
                )
                teks = st.text_input("Ketik RESET untuk mengonfirmasi", key="reset_teks")
                if st.button(
                    "Reset total sekarang",
                    type="primary",
                    disabled=teks.strip().upper() != "RESET",
                    key="btn_reset",
                ):
                    logic.reset_all()
                    ui.flash("success", "Database berhasil direset ke 25 kamar kosong.")
                    st.rerun()

        st.write("")
        ui.section("Struktur tabel", "Empat entitas utama sesuai dokumen KOSPACE")
        st.dataframe(
            [
                {"Tabel": "kamar", "Primary Key": "id_kamar", "Atribut": "nomor_kamar, tipe, harga_bulanan, fasilitas, status"},
                {"Tabel": "penghuni", "Primary Key": "id_penghuni", "Atribut": "nama, telepon, telepon_ortu, alamat"},
                {"Tabel": "sewa", "Primary Key": "id_sewa", "Atribut": "id_penghuni (FK), id_kamar (FK), tanggal_mulai, tanggal_selesai, durasi, harga_bulanan, status_sewa"},
                {"Tabel": "pembayaran", "Primary Key": "id_pembayaran", "Atribut": "id_sewa (FK), periode_bulan, periode_tahun, tanggal_bayar, nominal, status_pembayaran"},
            ],
            hide_index=True,
            width="stretch",
        )

    # ------------------------------------------------------------------
    # EKSPOR
    # ------------------------------------------------------------------
    with tab_ekspor:
        ui.section("Ekspor data", "Unduh CSV (UTF-8) untuk diolah di Excel atau alat lain")
        st.download_button(
            "🗂️ Unduh semua data (ZIP berisi 5 CSV)",
            data=_zip_semua(),
            file_name="kospace_export.zip",
            mime="application/zip",
            type="primary",
            key="unduh_zip",
        )
        st.write("")

        kamar_rows = [
            {
                "id_kamar": k["id_kamar"], "nomor_kamar": k["nomor_kamar"], "tipe": k["tipe"],
                "harga_bulanan": k["harga_bulanan"], "fasilitas": k["fasilitas"], "status": k["status"],
            }
            for k in db.list_kamar()
        ]
        penghuni_rows = [
            {
                "id_penghuni": p["id_penghuni"], "nama": p["nama"], "telepon": p["telepon"],
                "telepon_ortu": p["telepon_ortu"], "alamat": p["alamat"],
            }
            for p in db.list_penghuni()
        ]
        sewa_rows = [
            {
                "id_sewa": s["id_sewa"], "id_penghuni": s["id_penghuni"], "nama": s["nama"],
                "id_kamar": s["id_kamar"], "nomor_kamar": s["nomor_kamar"],
                "tanggal_mulai": s["tanggal_mulai"], "tanggal_selesai": s["tanggal_selesai"],
                "durasi": s["durasi"], "harga_bulanan": s["harga_bulanan"],
                "status_sewa": s["status_sewa"],
            }
            for s in db.list_sewa()
        ]
        bayar_rows = [
            {
                "id_pembayaran": p["id_pembayaran"], "id_sewa": p["id_sewa"],
                "periode_bulan": p["periode_bulan"], "periode_tahun": p["periode_tahun"],
                "tanggal_bayar": p["tanggal_bayar"], "nominal": p["nominal"],
                "status_pembayaran": p["status_pembayaran"],
            }
            for p in db.list_pembayaran()
        ]
        tagihan_rows = [
            {
                "id_sewa": b["id_sewa"], "penghuni": b["nama"], "kamar": b["nomor_kamar"],
                "periode_bulan": b["bulan"], "periode_tahun": b["tahun"],
                "jatuh_tempo": b["jatuh_tempo"], "nominal": b["nominal"], "status": b["status"],
            }
            for b in logic.build_bills()
        ]

        e1, e2, e3 = st.columns(3)
        with e1:
            st.download_button(
                "⬇️ Kamar (CSV)", data=_csv(kamar_rows), file_name="kamar.csv",
                mime="text/csv", key="exp_kamar", width="stretch",
            )
            st.download_button(
                "⬇️ Sewa (CSV)", data=_csv(sewa_rows), file_name="sewa.csv",
                mime="text/csv", key="exp_sewa", width="stretch",
            )
        with e2:
            st.download_button(
                "⬇️ Penghuni (CSV)", data=_csv(penghuni_rows), file_name="penghuni.csv",
                mime="text/csv", key="exp_penghuni", width="stretch",
            )
            st.download_button(
                "⬇️ Tagihan (CSV)", data=_csv(tagihan_rows), file_name="tagihan.csv",
                mime="text/csv", key="exp_tagihan", width="stretch",
            )
        with e3:
            st.download_button(
                "⬇️ Pembayaran (CSV)", data=_csv(bayar_rows), file_name="pembayaran.csv",
                mime="text/csv", key="exp_bayar", width="stretch",
            )
            st.download_button(
                "⬇️ Log aktivitas (CSV)",
                data=_csv(
                    [
                        {
                            "waktu": log["waktu"], "aksi": log["aksi"],
                            "entitas": log["entitas"], "keterangan": log["keterangan"],
                        }
                        for log in db.list_log(1000)
                    ]
                ),
                file_name="log_aktivitas.csv", mime="text/csv", key="exp_log", width="stretch",
            )

        st.caption(
            "Tanggal pada CSV tetap menggunakan format database **YYYY-MM-DD** agar mudah diolah. "
            "Tampilan aplikasi menggunakan format DD-MM-YYYY."
        )

    # ------------------------------------------------------------------
    # ATURAN
    # ------------------------------------------------------------------
    with tab_aturan:
        ui.section("Aturan bisnis KOSPACE", "Rujukan lengkap perilaku sistem")
        with st.expander("🔑 B01 — Nomor kamar unik", expanded=True):
            st.markdown(
                "Nomor kamar adalah kode bisnis yang dikenal pemilik (A01, B01, C01) dan "
                "**tidak boleh kembar**. Jika nomor sudah dipakai, sistem menolak kamar baru. "
                "Contoh ditolak: menambah **A01** saat A01 sudah ada."
            )
        with st.expander("📅 B06 — Tanggal selesai harus setelah tanggal mulai"):
            st.markdown(
                "Sistem menolak sewa bila tanggal selesai sama dengan atau sebelum tanggal mulai. "
                "Contoh diterima: 01-01-2027 s.d. 31-03-2027. "
                "Contoh ditolak: 15-12-2026 s.d. 10-12-2026."
            )
        with st.expander("💵 B08 — Nominal pembayaran"):
            st.markdown(
                "Nominal pembayaran harus **lebih dari 0** dan **sama dengan harga_bulanan pada sewa**. "
                "Nominal 0 ditolak. Pembayaran sebagian belum didukung."
            )
        with st.expander("🗑️ B10 — Larangan hapus data yang punya riwayat"):
            st.markdown(
                "- Kamar tidak bisa dihapus jika punya riwayat sewa.\n"
                "- Penghuni tidak bisa dihapus jika punya catatan sewa.\n"
                "- Sewa tidak bisa dihapus jika sudah ada pembayaran.\n"
                "- Pembayaran boleh dihapus untuk memperbaiki salah catat."
            )
        with st.expander("🔁 B14 — Satu periode hanya sekali"):
            st.markdown(
                "Sewa hanya boleh memiliki **satu pembayaran untuk bulan dan tahun yang sama**. "
                "Pembayaran kedua untuk periode yang sama ditolak."
            )
        with st.expander("🚦 Status kamar otomatis"):
            st.markdown(
                "**Ditempati** — kamar punya sewa Aktif dan tanggal hari ini berada di antara tanggal "
                "mulai dan selesai.\n\n"
                "**Tersedia** — tidak ada sewa seperti itu. Sewa yang tanggal selesainya sudah lewat "
                "otomatis menjadi **Selesai**."
            )
        with st.expander("💳 Status pembayaran"):
            st.markdown(
                "**Lunas** — pembayaran untuk periode itu sudah dicatat.\n\n"
                "**Belum Dibayar** — belum membayar dan belum melewati jatuh tempo tanggal 10. "
                "Untuk periode pertama, jatuh tempo tidak mendahului tanggal masuk.\n\n"
                "**Terlambat** — belum membayar dan sudah melewati tanggal 10."
            )
        with st.expander("⚔️ Deteksi jadwal bertabrakan"):
            st.markdown(
                "Bentrok jika **tanggal mulai baru ≤ tanggal selesai lama** DAN "
                "**tanggal selesai baru ≥ tanggal mulai lama**. Contoh: kamar A01 disewa sampai "
                "31-12-2026, calon penghuni baru ingin masuk 15-12-2026 → sewa ditolak. "
                "Penghuni baru bisa mulai 01-01-2027."
            )
        with st.expander("🧮 Harga bulanan & normalisasi"):
            st.markdown(
                "`harga_bulanan` ada di tabel **Kamar** (harga berlaku saat ini, bisa berubah) dan "
                "di tabel **Sewa** (harga yang disepakati, tidak berubah). Harga disalin saat sewa "
                "dibuat agar riwayat pembayaran tidak ikut berubah ketika harga kamar naik/turun.\n\n"
                "**1NF** setiap kolom satu nilai dan setiap tabel punya primary key. "
                "**2NF** primary key satu kolom. **3NF** data penghuni/kamar tidak ditulis ulang di "
                "sewa/pembayaran, kecuali `harga_bulanan` yang disengaja."
            )
        with st.expander("🔢 Format ID otomatis"):
            st.markdown(
                "| Entitas | Format | Contoh |\n|---|---|---|\n"
                "| Kamar | K + 3 digit | K001 |\n"
                "| Penghuni | P + 3 digit | P001 |\n"
                "| Sewa | S + 3 digit | S001 |\n"
                "| Pembayaran | BY + 3 digit | BY001 |\n\n"
                "ID dibuat otomatis oleh Python. Nomor kamar tetap menjadi kode bisnis yang dikenal "
                "pemilik; ID internal hanya dipakai sistem."
            )

    # ------------------------------------------------------------------
    # TENTANG
    # ------------------------------------------------------------------
    with tab_tentang:
        ui.section("Tentang KOSPACE", "Sistem Administrasi Pengelolaan Kos")
        st.markdown(
            """
            <div class="ks-panel" style="margin-bottom:14px;">
              <div class="ks-panel-title" style="font-size:18px;">🏡 KOSPACE</div>
              <div class="ks-panel-sub" style="margin-bottom:10px;">Sistem administrasi kos putri · tanpa login</div>
              <div style="font-size:13px;color:#475569;line-height:1.7;">
                KOSPACE membantu pemilik kos mengelola data kamar, identitas penghuni, masa sewa, dan
                pembayaran dalam satu sistem. Dibangun dengan <b>Python</b>, <b>Streamlit</b>, dan
                <b>SQLite</b> sehingga data lebih terstruktur, mudah dicari, dan riwayatnya dapat
                diperiksa kapan saja.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        a, b = st.columns(2)
        with a:
            ui.panel(
                "Lingkup sistem",
                "Sesuai dokumen perancangan",
                """
                <ul style="font-size:12.5px;color:#475569;line-height:1.8;padding-left:18px;margin:0;">
                  <li>Dashboard ringkasan data kos</li>
                  <li>Tambah, lihat, ubah, hapus kamar</li>
                  <li>Tambah, lihat, ubah, hapus penghuni</li>
                  <li>Pencatatan sewa dan masa sewa</li>
                  <li>Pembayaran per periode + status otomatis</li>
                  <li>Riwayat dan detail transaksi</li>
                  <li>Pencegahan jadwal sewa bertabrakan</li>
                </ul>
                """,
            )
        with b:
            ui.panel(
                "Batasan sistem",
                "Di luar lingkup versi ini",
                """
                <ul style="font-size:12.5px;color:#475569;line-height:1.8;padding-left:18px;margin:0;">
                  <li>Belum ada login dan pemesanan mandiri</li>
                  <li>Belum ada pembayaran online</li>
                  <li>Belum ada deposit dan token listrik</li>
                  <li>Belum ada kuitansi dan pengingat WhatsApp</li>
                  <li>Belum ada deployment ke internet</li>
                </ul>
                <div style="font-size:11px;color:#94a3b8;margin-top:10px;">
                  Aplikasi dijalankan lokal lewat terminal VS Code.
                </div>
                """,
            )

        st.write("")
        ui.section("Tim penyusun", "Kelompok 4 · Pemrograman Bisnis & Perancangan Sistem Administrasi")
        st.dataframe(
            [
                {"Nama": "Alya Nafisah", "NIM": "4.52.24.3.02"},
                {"Nama": "Marensya Aurellya", "NIM": "4.52.24.3.15"},
                {"Nama": "Permata Rayya A. A.", "NIM": "4.52.24.3.21"},
                {"Nama": "Shintia Nova P. A.", "NIM": "4.52.24.3.25"},
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Dosen pengampu: Dwi Budi Santoso, S.Kom., M.Kom. · "
            f"Versi aplikasi 1.0 · Database SQLite · {info['size_kb']} KB"
        )
