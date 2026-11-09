"""Komponen logic-aware yang dipakai di beberapa halaman."""

from datetime import date

import streamlit as st

from . import logic, ui


def payment_form(sewa: dict, key_prefix: str) -> None:
    """Form pencatatan pembayaran untuk satu sewa. Mematuhi B08 dan B14."""
    belum = logic.unpaid_periods(sewa["id_sewa"])
    if not belum:
        st.success("🎉 Semua periode sewa ini sudah lunas. Tidak ada tagihan tersisa.")
        return

    opsi = {f"{b['tahun']}-{b['bulan']:02d}": b for b in belum}
    kunci = list(opsi)
    key_periode = f"{key_prefix}_periode"
    ui.ensure_select(kunci, key_periode, default=kunci[0])
    pilih = st.selectbox(
        "Periode yang dibayar",
        kunci,
        format_func=lambda k: (
            f"{opsi[k]['periode']} · jatuh tempo {ui.fmt_date(opsi[k]['jatuh_tempo'])} · "
            f"{opsi[k]['status']}"
        ),
        key=key_periode,
        help="Hanya periode yang belum lunas yang dapat dipilih.",
    )
    tagihan = opsi[pilih]

    c1, c2 = st.columns(2)
    with c1:
        nominal = st.number_input(
            "Nominal pembayaran (Rp)",
            min_value=0,
            step=50_000,
            value=int(sewa["harga_bulanan"]),
            key=f"{key_prefix}_nominal",
            help="Nominal harus sama dengan harga sewa bulanan (B08).",
        )
    with c2:
        tanggal_bayar = st.date_input(
            "Tanggal pembayaran",
            value=date.today(),
            key=f"{key_prefix}_tanggal",
        )

    if tagihan["status"] == "Terlambat":
        st.warning(
            f"Tagihan ini sudah melewati jatuh tempo selama **{tagihan['hari_telat']} hari**. "
            "Pembayaran tetap dapat dicatat sebagai Lunas."
        )
    else:
        st.caption(
            f"Jatuh tempo {ui.fmt_date(tagihan['jatuh_tempo'])} · "
            f"nominal sewa {ui.rupiah(sewa['harga_bulanan'])}."
        )

    if st.button("💳 Simpan pembayaran", type="primary", key=f"{key_prefix}_submit"):
        try:
            new_id = logic.create_pembayaran(
                sewa["id_sewa"],
                tagihan["bulan"],
                tagihan["tahun"],
                tanggal_bayar,
                nominal,
            )
            ui.flash(
                "success",
                f"Pembayaran {new_id} untuk periode {tagihan['periode']} berhasil dicatat.",
            )
            st.rerun()
        except logic.BusinessError as exc:
            st.error(str(exc))
