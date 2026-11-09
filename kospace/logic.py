"""KOSPACE - Aturan bisnis, validasi, status otomatis, dan laporan.

Seluruh aturan pada dokumen KOSPACE diterapkan di lapisan ini agar halaman
Streamlit hanya berfokus pada tampilan.
"""

from __future__ import annotations

import calendar
import re
import sqlite3
from datetime import date, datetime, timedelta

from . import db

# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------
BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
BULAN_SINGKAT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                 "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

ROOM_TYPES = ["Tipe A", "Tipe B", "Tipe C"]
ROOM_DEFAULTS = {
    "Tipe A": {"harga": 1_300_000, "fasilitas": "AC, Wi-Fi, kamar mandi dalam"},
    "Tipe B": {"harga": 950_000, "fasilitas": "AC, Wi-Fi, kamar mandi luar"},
    "Tipe C": {"harga": 700_000, "fasilitas": "Kipas angin, Wi-Fi, kamar mandi luar"},
}

STATUS_SEWA = ["Aktif", "Selesai"]
STATUS_PEMBAYARAN = ["Lunas", "Belum Dibayar", "Terlambat"]


class BusinessError(Exception):
    """Kesalahan yang ramah dibaca pengguna."""


# ---------------------------------------------------------------------------
# Utilitas tanggal
# ---------------------------------------------------------------------------
def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise BusinessError("Format tanggal tidak valid.")


def add_months(d: date, months: int) -> date:
    """Tambahkan bulan dengan kliping akhir bulan (31 Jan + 1 bln = 28 Feb)."""
    total = d.month - 1 + months
    tahun = d.year + total // 12
    bulan = total % 12 + 1
    hari = min(d.day, calendar.monthrange(tahun, bulan)[1])
    return date(tahun, bulan, hari)


def rental_end_date(start: date, durasi: int) -> date:
    """Tanggal selesai = awal bulan ke-N dikurangi satu hari (inklusif)."""
    return add_months(start, durasi) - timedelta(days=1)


def duration_months(start: date, end: date) -> int:
    """Perkiraan jumlah bulan inklusif antara dua tanggal."""
    if end < start:
        return 0
    bulan = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= start.day:
        bulan += 1
    return max(1, bulan)


def month_range(start: date, end: date) -> list[tuple[int, int]]:
    """Daftar (tahun, bulan) dari bulan mulai sampai bulan selesai."""
    if end < start:
        return []
    hasil = []
    tahun, bulan = start.year, start.month
    while (tahun, bulan) <= (end.year, end.month):
        hasil.append((tahun, bulan))
        bulan += 1
        if bulan > 12:
            bulan = 1
            tahun += 1
    return hasil


def due_date_for_period(start: date, tahun: int, bulan: int) -> date:
    """Jatuh tempo tanggal 10. Periode pertama tidak mendahului tanggal masuk."""
    jatuh_tempo = date(tahun, bulan, 10)
    if (tahun, bulan) == (start.year, start.month) and start > jatuh_tempo:
        return start
    return jatuh_tempo


def _rp(value) -> str:
    return "Rp" + f"{int(value):,}".replace(",", ".")


def today_iso() -> str:
    return date.today().isoformat()


def today_label() -> str:
    d = date.today()
    return f"{HARI[d.weekday()]}, {d.day} {BULAN[d.month - 1]} {d.year}"


def month_label(bulan: int) -> str:
    return BULAN[bulan - 1]


def period_label(bulan: int, tahun: int) -> str:
    return f"{BULAN[bulan - 1]} {tahun}"


# ---------------------------------------------------------------------------
# Validasi umum
# ---------------------------------------------------------------------------
def _teks_wajib(value, label: str, maks: int = 120) -> str:
    hasil = (str(value) if value is not None else "").strip()
    if not hasil:
        raise BusinessError(f"{label} wajib diisi.")
    if len(hasil) > maks:
        raise BusinessError(f"{label} maksimal {maks} karakter.")
    return hasil


def _angka_positif(value, label: str) -> int:
    try:
        angka = int(value)
    except (TypeError, ValueError):
        raise BusinessError(f"{label} harus berupa angka bulat.")
    if angka <= 0:
        raise BusinessError(f"{label} harus lebih dari 0 (B08).")
    return angka


def _validasi_telepon(value, label: str, wajib: bool = True) -> str:
    teks = (str(value) if value is not None else "").strip()
    if not teks:
        if wajib:
            raise BusinessError(f"{label} wajib diisi.")
        return ""
    bersih = re.sub(r"[\s\-]", "", teks)
    if not re.fullmatch(r"\+?\d{8,18}", bersih):
        raise BusinessError(
            f"{label} tidak valid. Gunakan 8-18 digit angka (boleh diawali +)."
        )
    return teks


def _normalisasi_nomor(value) -> str:
    return str(value or "").strip().upper().replace(" ", "")


def _validasi_nomor_kamar(nomor: str) -> str:
    if not nomor:
        raise BusinessError("Nomor kamar wajib diisi (B01).")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{0,9}", nomor):
        raise BusinessError(
            "Nomor kamar hanya boleh huruf/angka/tanda hubung, maksimal 10 karakter."
        )
    return nomor


def _pastikan_unik_nomor(conn: sqlite3.Connection, nomor: str, kecuali: str | None = None) -> None:
    if kecuali:
        row = conn.execute(
            "SELECT id_kamar FROM kamar WHERE nomor_kamar = ? AND id_kamar <> ?",
            (nomor, kecuali),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id_kamar FROM kamar WHERE nomor_kamar = ?", (nomor,)
        ).fetchone()
    if row:
        raise BusinessError(
            f"Nomor kamar {nomor} sudah dipakai kamar lain. Nomor kamar harus unik (B01)."
        )


def _pastikan_ada(conn: sqlite3.Connection, table: str, pk: str, value: str, label: str) -> dict:
    row = conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (value,)).fetchone()
    if not row:
        raise BusinessError(f"{label} tidak ditemukan.")
    return dict(row)


def _konversi_integrity_error(exc: sqlite3.IntegrityError) -> BusinessError:
    pesan = str(exc)
    if "kamar.nomor_kamar" in pesan:
        return BusinessError("Nomor kamar sudah dipakai. Nomor kamar harus unik (B01).")
    if "pembayaran.id_sewa" in pesan or "UNIQUE constraint failed: pembayaran" in pesan:
        return BusinessError(
            "Sewa ini sudah memiliki pembayaran untuk periode tersebut (B14)."
        )
    if "FOREIGN KEY" in pesan:
        return BusinessError(
            "Data masih terhubung dengan data lain sehingga tidak bisa diproses (FK RESTRICT)."
        )
    return BusinessError(f"Data bertentangan dengan aturan database: {pesan}")


# ---------------------------------------------------------------------------
# Status otomatis
# ---------------------------------------------------------------------------
def refresh_statuses() -> None:
    """Selesaikan sewa yang sudah lewat dan sinkronkan status kamar."""
    hari_ini = today_iso()
    with db.connection() as conn:
        conn.execute(
            "UPDATE sewa SET status_sewa = 'Selesai' "
            "WHERE status_sewa = 'Aktif' AND tanggal_selesai < ?",
            (hari_ini,),
        )
        conn.execute(
            """
            UPDATE kamar
               SET status = CASE WHEN EXISTS (
                     SELECT 1 FROM sewa s
                      WHERE s.id_kamar = kamar.id_kamar
                        AND s.status_sewa = 'Aktif'
                        AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                   ) THEN 'Ditempati' ELSE 'Tersedia' END
            """,
            (hari_ini, hari_ini),
        )


def bootstrap() -> None:
    db.init_db()
    if db.get_meta("initialized") is None:
        seed_demo()
        db.set_meta("initialized", "1")
    refresh_statuses()


# ---------------------------------------------------------------------------
# Kamar
# ---------------------------------------------------------------------------
def create_kamar(nomor_kamar, tipe, harga_bulanan, fasilitas) -> str:
    nomor = _validasi_nomor_kamar(_normalisasi_nomor(nomor_kamar))
    tipe = (tipe or "").strip()
    if tipe not in ROOM_TYPES:
        raise BusinessError("Tipe kamar tidak dikenal.")
    harga = _angka_positif(harga_bulanan, "Harga bulanan")
    fas = _teks_wajib(fasilitas, "Fasilitas", 250)
    try:
        with db.connection() as conn:
            _pastikan_unik_nomor(conn, nomor)
            new_id = db.next_id(conn, "kamar", "id_kamar", "K")
            conn.execute(
                "INSERT INTO kamar (id_kamar, nomor_kamar, tipe, harga_bulanan, fasilitas, status) "
                "VALUES (?, ?, ?, ?, ?, 'Tersedia')",
                (new_id, nomor, tipe, harga, fas),
            )
            db.log(conn, "Tambah", "Kamar", f"{new_id} · {nomor} ({tipe})")
    except sqlite3.IntegrityError as exc:
        raise _konversi_integrity_error(exc)
    refresh_statuses()
    return new_id


def update_kamar(id_kamar, nomor_kamar, tipe, harga_bulanan, fasilitas) -> None:
    nomor = _validasi_nomor_kamar(_normalisasi_nomor(nomor_kamar))
    tipe = (tipe or "").strip()
    if tipe not in ROOM_TYPES:
        raise BusinessError("Tipe kamar tidak dikenal.")
    harga = _angka_positif(harga_bulanan, "Harga bulanan")
    fas = _teks_wajib(fasilitas, "Fasilitas", 250)
    try:
        with db.connection() as conn:
            lama = _pastikan_ada(conn, "kamar", "id_kamar", id_kamar, "Kamar")
            _pastikan_unik_nomor(conn, nomor, kecuali=id_kamar)
            conn.execute(
                "UPDATE kamar SET nomor_kamar = ?, tipe = ?, harga_bulanan = ?, fasilitas = ? "
                "WHERE id_kamar = ?",
                (nomor, tipe, harga, fas, id_kamar),
            )
            db.log(conn, "Ubah", "Kamar", f"{id_kamar} · {lama['nomor_kamar']} → {nomor}")
    except sqlite3.IntegrityError as exc:
        raise _konversi_integrity_error(exc)
    refresh_statuses()


def delete_kamar(id_kamar) -> None:
    with db.connection() as conn:
        kamar = _pastikan_ada(conn, "kamar", "id_kamar", id_kamar, "Kamar")
        jumlah = conn.execute(
            "SELECT COUNT(*) FROM sewa WHERE id_kamar = ?", (id_kamar,)
        ).fetchone()[0]
        if jumlah:
            raise BusinessError(
                f"Kamar {kamar['nomor_kamar']} tidak bisa dihapus karena sudah memiliki "
                f"{jumlah} riwayat sewa. Hanya kamar tanpa riwayat sewa yang boleh dihapus (B10)."
            )
        conn.execute("DELETE FROM kamar WHERE id_kamar = ?", (id_kamar,))
        db.log(conn, "Hapus", "Kamar", f"{id_kamar} · {kamar['nomor_kamar']}")
    refresh_statuses()


# ---------------------------------------------------------------------------
# Penghuni
# ---------------------------------------------------------------------------
def create_penghuni(nama, telepon, telepon_ortu, alamat) -> str:
    nama = _teks_wajib(nama, "Nama penghuni", 80)
    telepon = _validasi_telepon(telepon, "Nomor telepon")
    telepon_ortu = _validasi_telepon(telepon_ortu, "Nomor telepon orang tua", wajib=False)
    alamat = (str(alamat) if alamat is not None else "").strip()
    if len(alamat) > 250:
        raise BusinessError("Alamat maksimal 250 karakter.")
    with db.connection() as conn:
        new_id = db.next_id(conn, "penghuni", "id_penghuni", "P")
        conn.execute(
            "INSERT INTO penghuni (id_penghuni, nama, telepon, telepon_ortu, alamat) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_id, nama, telepon, telepon_ortu or None, alamat or None),
        )
        db.log(conn, "Tambah", "Penghuni", f"{new_id} · {nama}")
    return new_id


def update_penghuni(id_penghuni, nama, telepon, telepon_ortu, alamat) -> None:
    nama = _teks_wajib(nama, "Nama penghuni", 80)
    telepon = _validasi_telepon(telepon, "Nomor telepon")
    telepon_ortu = _validasi_telepon(telepon_ortu, "Nomor telepon orang tua", wajib=False)
    alamat = (str(alamat) if alamat is not None else "").strip()
    if len(alamat) > 250:
        raise BusinessError("Alamat maksimal 250 karakter.")
    with db.connection() as conn:
        lama = _pastikan_ada(conn, "penghuni", "id_penghuni", id_penghuni, "Penghuni")
        conn.execute(
            "UPDATE penghuni SET nama = ?, telepon = ?, telepon_ortu = ?, alamat = ? "
            "WHERE id_penghuni = ?",
            (nama, telepon, telepon_ortu or None, alamat or None, id_penghuni),
        )
        db.log(conn, "Ubah", "Penghuni", f"{id_penghuni} · {lama['nama']} → {nama}")


def delete_penghuni(id_penghuni) -> None:
    with db.connection() as conn:
        orang = _pastikan_ada(conn, "penghuni", "id_penghuni", id_penghuni, "Penghuni")
        jumlah = conn.execute(
            "SELECT COUNT(*) FROM sewa WHERE id_penghuni = ?", (id_penghuni,)
        ).fetchone()[0]
        if jumlah:
            raise BusinessError(
                f"Penghuni {orang['nama']} tidak bisa dihapus karena sudah memiliki "
                f"{jumlah} catatan sewa. Riwayatnya tetap dapat ditelusuri lewat filter (B10)."
            )
        conn.execute("DELETE FROM penghuni WHERE id_penghuni = ?", (id_penghuni,))
        db.log(conn, "Hapus", "Penghuni", f"{id_penghuni} · {orang['nama']}")


# ---------------------------------------------------------------------------
# Sewa & jadwal
# ---------------------------------------------------------------------------
def check_room_conflict(id_kamar: str, tanggal_mulai, tanggal_selesai,
                        exclude_sewa: str | None = None) -> list[dict]:
    """Bentrok jika mulai_baru <= selesai_lama DAN selesai_baru >= mulai_lama."""
    start = parse_date(tanggal_mulai).isoformat()
    end = parse_date(tanggal_selesai).isoformat()
    return db.fetch_all(
        """
        SELECT s.*, p.nama
          FROM sewa s
          JOIN penghuni p ON p.id_penghuni = s.id_penghuni
         WHERE s.id_kamar = ?
           AND (? IS NULL OR s.id_sewa <> ?)
           AND ? <= s.tanggal_selesai
           AND ? >= s.tanggal_mulai
         ORDER BY s.tanggal_mulai
        """,
        (id_kamar, exclude_sewa, exclude_sewa, start, end),
    )


def create_sewa(id_penghuni, id_kamar, tanggal_mulai, tanggal_selesai, harga_bulanan,
                durasi: int | None = None) -> str:
    start = parse_date(tanggal_mulai)
    end = parse_date(tanggal_selesai)
    if end <= start:
        raise BusinessError(
            "Tanggal selesai harus setelah tanggal mulai. Sewa ditolak (B06)."
        )
    harga = _angka_positif(harga_bulanan, "Harga sewa bulanan")
    durasi_final = int(durasi) if durasi else duration_months(start, end)
    if durasi_final <= 0:
        raise BusinessError("Durasi sewa harus lebih dari 0.")
    try:
        with db.connection() as conn:
            orang = _pastikan_ada(conn, "penghuni", "id_penghuni", id_penghuni, "Penghuni")
            kamar = _pastikan_ada(conn, "kamar", "id_kamar", id_kamar, "Kamar")

            bentrok = conn.execute(
                """
                SELECT s.id_sewa, s.tanggal_mulai, s.tanggal_selesai, p.nama
                  FROM sewa s JOIN penghuni p ON p.id_penghuni = s.id_penghuni
                 WHERE s.id_kamar = ?
                   AND ? <= s.tanggal_selesai
                   AND ? >= s.tanggal_mulai
                 ORDER BY s.tanggal_mulai
                """,
                (id_kamar, start.isoformat(), end.isoformat()),
            ).fetchall()
            if bentrok:
                detail = "; ".join(
                    f"{r['id_sewa']} ({r['nama']}, {r['tanggal_mulai']} s.d. {r['tanggal_selesai']})"
                    for r in bentrok
                )
                raise BusinessError(
                    f"Jadwal bertabrakan dengan sewa lain di kamar {kamar['nomor_kamar']}: "
                    f"{detail}. Pilih tanggal setelah {bentrok[-1]['tanggal_selesai']}."
                )

            new_id = db.next_id(conn, "sewa", "id_sewa", "S")
            status = "Aktif" if end >= date.today() else "Selesai"
            conn.execute(
                "INSERT INTO sewa (id_sewa, id_penghuni, id_kamar, tanggal_mulai, "
                "tanggal_selesai, durasi, harga_bulanan, status_sewa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, id_penghuni, id_kamar, start.isoformat(), end.isoformat(),
                 durasi_final, harga, status),
            )
            db.log(
                conn, "Tambah", "Sewa",
                f"{new_id} · {orang['nama']} → {kamar['nomor_kamar']} "
                f"({start.isoformat()} s.d. {end.isoformat()})",
            )
    except sqlite3.IntegrityError as exc:
        raise _konversi_integrity_error(exc)
    refresh_statuses()
    return new_id


def update_sewa(id_sewa, tanggal_mulai, tanggal_selesai, harga_bulanan,
                durasi: int | None = None) -> None:
    start = parse_date(tanggal_mulai)
    end = parse_date(tanggal_selesai)
    if end <= start:
        raise BusinessError(
            "Tanggal selesai harus setelah tanggal mulai. Perubahan ditolak (B06)."
        )
    harga = _angka_positif(harga_bulanan, "Harga sewa bulanan")
    durasi_final = int(durasi) if durasi else duration_months(start, end)
    with db.connection() as conn:
        sewa = _pastikan_ada(conn, "sewa", "id_sewa", id_sewa, "Sewa")
        kamar = _pastikan_ada(conn, "kamar", "id_kamar", sewa["id_kamar"], "Kamar")

        jumlah_bayar = conn.execute(
            "SELECT COUNT(*) FROM pembayaran WHERE id_sewa = ?", (id_sewa,)
        ).fetchone()[0]
        if jumlah_bayar:
            if start.isoformat() != sewa["tanggal_mulai"]:
                raise BusinessError(
                    "Tanggal mulai tidak dapat diubah karena sewa sudah memiliki pembayaran."
                )
            if harga != sewa["harga_bulanan"]:
                raise BusinessError(
                    "Harga sewa tidak dapat diubah karena sudah ada pembayaran. "
                    "Harga tersalin saat sewa dibuat agar riwayat tidak berubah."
                )
            terakhir = conn.execute(
                "SELECT MAX(periode_tahun * 100 + periode_bulan) AS kode "
                "FROM pembayaran WHERE id_sewa = ?", (id_sewa,)
            ).fetchone()[0]
            if terakhir:
                tahun, bulan = divmod(int(terakhir), 100)
                akhir_bulan = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
                if end < akhir_bulan:
                    raise BusinessError(
                        f"Tanggal selesai tidak boleh lebih awal dari periode yang sudah dibayar "
                        f"({period_label(bulan, tahun)})."
                    )

        bentrok = conn.execute(
            """
            SELECT s.id_sewa, s.tanggal_mulai, s.tanggal_selesai, p.nama
              FROM sewa s JOIN penghuni p ON p.id_penghuni = s.id_penghuni
             WHERE s.id_kamar = ? AND s.id_sewa <> ?
               AND ? <= s.tanggal_selesai
               AND ? >= s.tanggal_mulai
             ORDER BY s.tanggal_mulai
            """,
            (sewa["id_kamar"], id_sewa, start.isoformat(), end.isoformat()),
        ).fetchall()
        if bentrok:
            detail = "; ".join(
                f"{r['id_sewa']} ({r['nama']}, {r['tanggal_mulai']} s.d. {r['tanggal_selesai']})"
                for r in bentrok
            )
            raise BusinessError(
                f"Jadwal bertabrakan dengan sewa lain di kamar {kamar['nomor_kamar']}: {detail}."
            )

        status = "Aktif" if end >= date.today() else "Selesai"
        conn.execute(
            "UPDATE sewa SET tanggal_mulai = ?, tanggal_selesai = ?, durasi = ?, "
            "harga_bulanan = ?, status_sewa = ? WHERE id_sewa = ?",
            (start.isoformat(), end.isoformat(), durasi_final, harga, status, id_sewa),
        )
        db.log(
            conn, "Ubah", "Sewa",
            f"{id_sewa} · {start.isoformat()} s.d. {end.isoformat()} @ {_rp(harga)}",
        )
    refresh_statuses()


def end_sewa(id_sewa, tanggal_selesai=None) -> None:
    akhir = parse_date(tanggal_selesai) if tanggal_selesai else date.today()
    with db.connection() as conn:
        sewa = _pastikan_ada(conn, "sewa", "id_sewa", id_sewa, "Sewa")
        start = parse_date(sewa["tanggal_mulai"])
        if akhir < start:
            raise BusinessError("Tanggal berhenti sewa tidak boleh sebelum tanggal mulai.")
        if sewa["status_sewa"] == "Selesai":
            raise BusinessError("Sewa ini sudah berstatus Selesai.")
        terakhir = conn.execute(
            "SELECT MAX(periode_tahun * 100 + periode_bulan) AS kode "
            "FROM pembayaran WHERE id_sewa = ?", (id_sewa,)
        ).fetchone()[0]
        if terakhir:
            tahun, bulan = divmod(int(terakhir), 100)
            if (akhir.year, akhir.month) < (tahun, bulan):
                raise BusinessError(
                    f"Sewa sudah dibayar sampai {period_label(bulan, tahun)}. "
                    "Tanggal berhenti tidak boleh sebelum periode tersebut."
                )
        durasi = duration_months(start, akhir)
        conn.execute(
            "UPDATE sewa SET tanggal_selesai = ?, durasi = ?, status_sewa = 'Selesai' "
            "WHERE id_sewa = ?",
            (akhir.isoformat(), durasi, id_sewa),
        )
        db.log(
            conn, "Selesai", "Sewa",
            f"{id_sewa} diakhiri pada {akhir.isoformat()} (durasi {durasi} bulan)",
        )
    refresh_statuses()


def delete_sewa(id_sewa) -> None:
    with db.connection() as conn:
        sewa = _pastikan_ada(conn, "sewa", "id_sewa", id_sewa, "Sewa")
        jumlah = conn.execute(
            "SELECT COUNT(*) FROM pembayaran WHERE id_sewa = ?", (id_sewa,)
        ).fetchone()[0]
        if jumlah:
            raise BusinessError(
                f"Sewa {id_sewa} tidak bisa dihapus karena sudah memiliki {jumlah} "
                "pembayaran. Hapus pembayaran terlebih dahulu jika memang salah catat."
            )
        conn.execute("DELETE FROM sewa WHERE id_sewa = ?", (id_sewa,))
        db.log(conn, "Hapus", "Sewa", f"{id_sewa} · {sewa['tanggal_mulai']} s.d. {sewa['tanggal_selesai']}")
    refresh_statuses()


# ---------------------------------------------------------------------------
# Pembayaran
# ---------------------------------------------------------------------------
def create_pembayaran(id_sewa, periode_bulan, periode_tahun, tanggal_bayar, nominal) -> str:
    try:
        bulan = int(periode_bulan)
        tahun = int(periode_tahun)
    except (TypeError, ValueError):
        raise BusinessError("Periode pembayaran tidak valid.")
    if not 1 <= bulan <= 12:
        raise BusinessError("Bulan periode harus antara 1 sampai 12.")
    if not 2000 <= tahun <= 2100:
        raise BusinessError("Tahun periode tidak valid.")
    nominal_int = _angka_positif(nominal, "Nominal pembayaran")
    tanggal = parse_date(tanggal_bayar)

    try:
        with db.connection() as conn:
            sewa = _pastikan_ada(conn, "sewa", "id_sewa", id_sewa, "Sewa")
            start = parse_date(sewa["tanggal_mulai"])
            end = parse_date(sewa["tanggal_selesai"])
            if not ((start.year, start.month) <= (tahun, bulan) <= (end.year, end.month)):
                raise BusinessError(
                    f"Periode {period_label(bulan, tahun)} berada di luar masa sewa "
                    f"({start.isoformat()} s.d. {end.isoformat()})."
                )
            if nominal_int != int(sewa["harga_bulanan"]):
                raise BusinessError(
                    f"Nominal pembayaran harus sama dengan harga sewa bulanan "
                    f"({_rp(sewa['harga_bulanan'])}). Nominal {_rp(nominal_int)} ditolak (B08)."
                )
            sudah = conn.execute(
                "SELECT id_pembayaran FROM pembayaran "
                "WHERE id_sewa = ? AND periode_bulan = ? AND periode_tahun = ?",
                (id_sewa, bulan, tahun),
            ).fetchone()
            if sudah:
                raise BusinessError(
                    f"Sewa {id_sewa} sudah memiliki pembayaran untuk periode "
                    f"{period_label(bulan, tahun)} (B14). Satu periode hanya boleh dibayar sekali."
                )
            new_id = db.next_id(conn, "pembayaran", "id_pembayaran", "BY")
            conn.execute(
                "INSERT INTO pembayaran (id_pembayaran, id_sewa, periode_bulan, "
                "periode_tahun, tanggal_bayar, nominal, status_pembayaran) "
                "VALUES (?, ?, ?, ?, ?, ?, 'Lunas')",
                (new_id, id_sewa, bulan, tahun, tanggal.isoformat(), nominal_int),
            )
            db.log(
                conn, "Bayar", "Pembayaran",
                f"{new_id} · {id_sewa} periode {month_label(bulan)} {tahun} "
                f"{_rp(nominal_int)}",
            )
    except sqlite3.IntegrityError as exc:
        raise _konversi_integrity_error(exc)
    return new_id


def delete_pembayaran(id_pembayaran) -> None:
    with db.connection() as conn:
        bayar = _pastikan_ada(conn, "pembayaran", "id_pembayaran", id_pembayaran, "Pembayaran")
        conn.execute("DELETE FROM pembayaran WHERE id_pembayaran = ?", (id_pembayaran,))
        db.log(
            conn, "Hapus", "Pembayaran",
            f"{id_pembayaran} · {bayar['id_sewa']} periode "
            f"{month_label(bayar['periode_bulan'])} {bayar['periode_tahun']}",
        )


# ---------------------------------------------------------------------------
# Tagihan, status pembayaran, dan ringkasan
# ---------------------------------------------------------------------------
def build_bills() -> list[dict]:
    """Bangun seluruh periode sewa beserta status pembayarannya."""
    hari_ini = date.today()
    pay_map = db.payments_map()
    hasil: list[dict] = []
    for sewa in db.list_sewa():
        start = parse_date(sewa["tanggal_mulai"])
        end = parse_date(sewa["tanggal_selesai"])
        for tahun, bulan in month_range(start, end):
            jatuh_tempo = due_date_for_period(start, tahun, bulan)
            bayar = pay_map.get((sewa["id_sewa"], tahun, bulan))
            if bayar:
                status = "Lunas"
                hari_telat = 0
            elif hari_ini > jatuh_tempo:
                status = "Terlambat"
                hari_telat = (hari_ini - jatuh_tempo).days
            else:
                status = "Belum Dibayar"
                hari_telat = 0
            hasil.append(
                {
                    "id_sewa": sewa["id_sewa"],
                    "id_penghuni": sewa["id_penghuni"],
                    "id_kamar": sewa["id_kamar"],
                    "nama": sewa["nama"],
                    "telepon": sewa["telepon"],
                    "nomor_kamar": sewa["nomor_kamar"],
                    "tipe": sewa["tipe"],
                    "status_sewa": sewa["status_sewa"],
                    "bulan": bulan,
                    "tahun": tahun,
                    "periode": period_label(bulan, tahun),
                    "tanggal_mulai_sewa": sewa["tanggal_mulai"],
                    "tanggal_selesai_sewa": sewa["tanggal_selesai"],
                    "jatuh_tempo": jatuh_tempo.isoformat(),
                    "nominal": int(sewa["harga_bulanan"]),
                    "status": status,
                    "hari_telat": hari_telat,
                    "id_pembayaran": bayar["id_pembayaran"] if bayar else None,
                    "tanggal_bayar": bayar["tanggal_bayar"] if bayar else None,
                }
            )
    hasil.sort(key=lambda b: (b["tahun"], b["bulan"], b["id_sewa"]))
    return hasil


def unpaid_periods(id_sewa: str) -> list[dict]:
    return [
        b for b in build_bills()
        if b["id_sewa"] == id_sewa and b["status"] != "Lunas"
    ]


def bills_for_sewa(id_sewa: str) -> list[dict]:
    return [b for b in build_bills() if b["id_sewa"] == id_sewa]


def payment_progress(id_sewa: str) -> dict:
    bills = bills_for_sewa(id_sewa)
    total = len(bills)
    lunas = sum(1 for b in bills if b["status"] == "Lunas")
    return {
        "total": total,
        "lunas": lunas,
        "belum": total - lunas,
        "persen": (lunas / total * 100) if total else 0,
    }


def revenue_series(bulan_terakhir: int = 6) -> list[dict]:
    hari_ini = date.today()
    kunci = []
    tahun, bulan = hari_ini.year, hari_ini.month
    for _ in range(bulan_terakhir):
        kunci.append((tahun, bulan))
        bulan -= 1
        if bulan == 0:
            bulan = 12
            tahun -= 1
    kunci.reverse()

    pembayaran = db.list_pembayaran()
    peta: dict[tuple[int, int], int] = {}
    for p in pembayaran:
        tgl = parse_date(p["tanggal_bayar"])
        peta[(tgl.year, tgl.month)] = peta.get((tgl.year, tgl.month), 0) + int(p["nominal"])

    return [
        {
            "Bulan": f"{BULAN_SINGKAT[b - 1]} {str(t)[2:]}",
            "Pendapatan": peta.get((t, b), 0),
            "kunci": f"{t}-{b:02d}",
        }
        for t, b in kunci
    ]


def room_type_breakdown() -> list[dict]:
    kamar = db.list_kamar()
    hasil = []
    for tipe in ROOM_TYPES:
        subset = [k for k in kamar if k["tipe"] == tipe]
        hasil.append(
            {
                "Tipe": tipe,
                "Tersedia": sum(1 for k in subset if k["status"] == "Tersedia"),
                "Ditempati": sum(1 for k in subset if k["status"] == "Ditempati"),
                "Total": len(subset),
            }
        )
    return hasil


def dashboard_metrics() -> dict:
    hari_ini = date.today()
    kamar = db.list_kamar()
    penghuni = db.list_penghuni()
    sewa = db.list_sewa()
    pembayaran = db.list_pembayaran()
    bills = build_bills()

    total_kamar = len(kamar)
    ditempati = sum(1 for k in kamar if k["status"] == "Ditempati")
    tersedia = total_kamar - ditempati

    aktif = [s for s in sewa if s["status_sewa"] == "Aktif"]
    selesai = [s for s in sewa if s["status_sewa"] == "Selesai"]

    penerimaan_bulan_ini = sum(
        int(p["nominal"]) for p in pembayaran
        if (parse_date(p["tanggal_bayar"]).year, parse_date(p["tanggal_bayar"]).month)
        == (hari_ini.year, hari_ini.month)
    )
    transaksi_bulan_ini = sum(
        1 for p in pembayaran
        if (parse_date(p["tanggal_bayar"]).year, parse_date(p["tanggal_bayar"]).month)
        == (hari_ini.year, hari_ini.month)
    )
    telat = [b for b in bills if b["status"] == "Terlambat"]
    belum = [b for b in bills if b["status"] != "Lunas"]
    jatuh_tempo = sorted(
        [b for b in belum],
        key=lambda b: (b["status"] != "Terlambat", b["jatuh_tempo"], b["id_sewa"]),
    )

    progres = {}
    for s in aktif:
        progres[s["id_sewa"]] = payment_progress(s["id_sewa"])

    return {
        "total_kamar": total_kamar,
        "tersedia": tersedia,
        "ditempati": ditempati,
        "okupansi": (ditempati / total_kamar * 100) if total_kamar else 0,
        "total_penghuni": len(penghuni),
        "penghuni_aktif": sum(1 for p in penghuni if p["kamar_aktif"]),
        "sewa_aktif": len(aktif),
        "sewa_selesai": len(selesai),
        "penerimaan_bulan_ini": penerimaan_bulan_ini,
        "transaksi_bulan_ini": transaksi_bulan_ini,
        "tunggakan_count": len(telat),
        "tunggakan_nominal": sum(int(b["nominal"]) for b in telat),
        "belum_bayar_count": len(belum),
        "belum_bayar_nominal": sum(int(b["nominal"]) for b in belum),
        "jatuh_tempo": jatuh_tempo,
        "recent_payments": pembayaran[:6],
        "active_rentals": aktif,
        "progress": progres,
        "revenue": revenue_series(),
        "breakdown": room_type_breakdown(),
        "logs": db.list_log(8),
        "is_demo": db.get_meta("demo_data") == "1",
    }


def tenant_financials(id_penghuni: str) -> dict:
    sewa = [s for s in db.list_sewa() if s["id_penghuni"] == id_penghuni]
    pembayaran = [p for p in db.list_pembayaran() if p["id_penghuni"] == id_penghuni]
    bills = [b for b in build_bills() if b["id_penghuni"] == id_penghuni]
    return {
        "jumlah_sewa": len(sewa),
        "total_kontrak": sum(int(s["harga_bulanan"]) * int(s["durasi"]) for s in sewa),
        "total_bayar": sum(int(p["nominal"]) for p in pembayaran),
        "tunggakan": sum(int(b["nominal"]) for b in bills if b["status"] == "Terlambat"),
        "belum_bayar": sum(int(b["nominal"]) for b in bills if b["status"] != "Lunas"),
        "sewa": sewa,
        "pembayaran": pembayaran,
        "tagihan": bills,
    }


def room_financials(id_kamar: str) -> dict:
    sewa = [s for s in db.list_sewa() if s["id_kamar"] == id_kamar]
    pembayaran = [p for p in db.list_pembayaran() if p["id_kamar"] == id_kamar]
    bills = [b for b in build_bills() if b["id_kamar"] == id_kamar]
    return {
        "jumlah_sewa": len(sewa),
        "total_pendapatan": sum(int(p["nominal"]) for p in pembayaran),
        "tunggakan": sum(int(b["nominal"]) for b in bills if b["status"] == "Terlambat"),
        "sewa": sewa,
        "pembayaran": pembayaran,
        "tagihan": bills,
    }


def timeline_events() -> list[dict]:
    events: list[dict] = []
    for s in db.list_sewa():
        events.append(
            {
                "tanggal": s["tanggal_mulai"],
                "jenis": "Sewa mulai",
                "keterangan": f"{s['id_sewa']} · {s['nama']} menempati {s['nomor_kamar']}",
                "nominal": int(s["harga_bulanan"]),
                "id": s["id_sewa"],
            }
        )
        if s["status_sewa"] == "Selesai":
            events.append(
                {
                    "tanggal": s["tanggal_selesai"],
                    "jenis": "Sewa selesai",
                    "keterangan": f"{s['id_sewa']} · {s['nama']} · kamar {s['nomor_kamar']}",
                    "nominal": 0,
                    "id": s["id_sewa"],
                }
            )
    for p in db.list_pembayaran():
        events.append(
            {
                "tanggal": p["tanggal_bayar"],
                "jenis": "Pembayaran",
                "keterangan": (
                    f"{p['id_pembayaran']} · {p['nama']} · {p['nomor_kamar']} · "
                    f"periode {month_label(p['periode_bulan'])} {p['periode_tahun']}"
                ),
                "nominal": int(p["nominal"]),
                "id": p["id_pembayaran"],
            }
        )
    events.sort(key=lambda e: (e["tanggal"], e["id"]), reverse=True)
    return events


# ---------------------------------------------------------------------------
# Data contoh & reset
# ---------------------------------------------------------------------------
def _first_of_month(offset: int) -> date:
    hari_ini = date.today()
    return add_months(date(hari_ini.year, hari_ini.month, 1), offset)


def _pastikan_kamar_standar(conn: sqlite3.Connection) -> None:
    """Pastikan 25 kamar standar tersedia sebelum memuat data contoh."""
    ada = {row["nomor_kamar"] for row in conn.execute("SELECT nomor_kamar FROM kamar").fetchall()}
    standar = [
        ("Tipe A", "A", 5, 1_300_000, "AC, Wi-Fi, kamar mandi dalam"),
        ("Tipe B", "B", 10, 950_000, "AC, Wi-Fi, kamar mandi luar"),
        ("Tipe C", "C", 10, 700_000, "Kipas angin, Wi-Fi, kamar mandi luar"),
    ]
    for tipe, prefix, jumlah, harga, fasilitas in standar:
        for nomor_urut in range(1, jumlah + 1):
            nomor = f"{prefix}{nomor_urut:02d}"
            if nomor in ada:
                continue
            new_id = db.next_id(conn, "kamar", "id_kamar", "K")
            conn.execute(
                "INSERT INTO kamar (id_kamar, nomor_kamar, tipe, harga_bulanan, fasilitas, status) "
                "VALUES (?, ?, ?, ?, ?, 'Tersedia')",
                (new_id, nomor, tipe, harga, fasilitas),
            )


def seed_demo() -> None:
    """Muat data contoh yang realistis (relatif terhadap tanggal hari ini)."""
    hari_ini = date.today()
    with db.connection() as conn:
        conn.execute("DELETE FROM pembayaran")
        conn.execute("DELETE FROM sewa")
        conn.execute("DELETE FROM penghuni")
        conn.execute("DELETE FROM log_aktivitas")
        _pastikan_kamar_standar(conn)

        kamar_rows = conn.execute("SELECT * FROM kamar").fetchall()
        kamar = {row["nomor_kamar"]: dict(row) for row in kamar_rows}

        penghuni = [
            ("Salsabila Putri", "081234567801", "081298765401", "Jl. Melati No. 12, Bandung"),
            ("Nadia Rahma", "081234567802", "081298765402", "Jl. Kenanga No. 8, Bandung"),
            ("Intan Permata", "081234567803", "081298765403", "Jl. Anggrek No. 21, Cimahi"),
            ("Rani Anggraini", "081234567804", "081298765404", "Jl. Dahlia No. 5, Bandung"),
            ("Zahra Aulia", "081234567805", "081298765405", "Jl. Mawar No. 17, Bandung Barat"),
            ("Melati Ayu", "081234567806", "081298765406", "Jl. Cempaka No. 3, Bandung"),
        ]
        ids_penghuni = []
        for index, (nama, telepon, ortu, alamat) in enumerate(penghuni, start=1):
            pid = f"P{index:03d}"
            conn.execute(
                "INSERT INTO penghuni (id_penghuni, nama, telepon, telepon_ortu, alamat) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, nama, telepon, ortu, alamat),
            )
            ids_penghuni.append(pid)

        # (penghuni, kamar, offset mulai bulan, durasi, bayar_bulan_ini, bulan_dilewati)
        rencana = [
            (ids_penghuni[0], "A01", -2, 12, True, set()),
            (ids_penghuni[1], "A02", -5, 6, False, set()),
            (ids_penghuni[2], "B01", -1, 12, True, set()),
            (ids_penghuni[3], "B02", -10, 3, False, set()),
            (ids_penghuni[4], "C01", -3, 6, False, {tuple(_first_of_month(-1).timetuple()[:2])}),
            (ids_penghuni[5], "C02", 0, 6, True, set()),
        ]

        counter_bayar = 0
        for index, (pid, nomor, offset, durasi, bayar_sekarang, lewati) in enumerate(rencana, start=1):
            start = _first_of_month(offset)
            end = rental_end_date(start, durasi)
            status = "Aktif" if end >= hari_ini else "Selesai"
            sid = f"S{index:03d}"
            kamar_ini = kamar[nomor]
            conn.execute(
                "INSERT INTO sewa (id_sewa, id_penghuni, id_kamar, tanggal_mulai, "
                "tanggal_selesai, durasi, harga_bulanan, status_sewa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, pid, kamar_ini["id_kamar"], start.isoformat(), end.isoformat(),
                 durasi, int(kamar_ini["harga_bulanan"]), status),
            )
            for tahun, bulan in month_range(start, end):
                adalah_bulan_ini = (tahun, bulan) == (hari_ini.year, hari_ini.month)
                sudah_lewat = (tahun, bulan) < (hari_ini.year, hari_ini.month)
                if (tahun, bulan) in lewati:
                    continue
                if adalah_bulan_ini:
                    if not bayar_sekarang:
                        continue
                    tanggal_bayar = hari_ini
                elif sudah_lewat:
                    tanggal_bayar = date(tahun, bulan, 5)
                else:
                    continue
                counter_bayar += 1
                byid = f"BY{counter_bayar:03d}"
                conn.execute(
                    "INSERT INTO pembayaran (id_pembayaran, id_sewa, periode_bulan, "
                    "periode_tahun, tanggal_bayar, nominal, status_pembayaran) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'Lunas')",
                    (byid, sid, bulan, tahun, tanggal_bayar.isoformat(),
                     int(kamar_ini["harga_bulanan"])),
                )
        db.log(conn, "Sistem", "Data contoh", "Data contoh KOSPACE dimuat ulang")
    refresh_statuses()
    db.set_meta("demo_data", "1")


def reset_transactions() -> None:
    """Hapus sewa & pembayaran, pertahankan kamar dan penghuni."""
    with db.connection() as conn:
        conn.execute("DELETE FROM pembayaran")
        conn.execute("DELETE FROM sewa")
        db.log(conn, "Sistem", "Reset", "Seluruh data sewa dan pembayaran dihapus")
    refresh_statuses()
    db.set_meta("demo_data", "0")


def reset_all() -> None:
    """Kosongkan semua data lalu buat ulang 25 kamar."""
    with db.connection() as conn:
        conn.execute("DELETE FROM pembayaran")
        conn.execute("DELETE FROM sewa")
        conn.execute("DELETE FROM penghuni")
        conn.execute("DELETE FROM kamar")
        conn.execute("DELETE FROM log_aktivitas")
        db._seed_rooms(conn)
        db.log(conn, "Sistem", "Reset", "Database direset ke 25 kamar kosong")
    refresh_statuses()
    db.set_meta("demo_data", "0")


def clear_tenants() -> None:
    """Hapus penghuni yang belum punya riwayat sewa (dipakai untuk bersih-bersih)."""
    with db.connection() as conn:
        conn.execute(
            "DELETE FROM penghuni WHERE id_penghuni NOT IN (SELECT id_penghuni FROM sewa)"
        )
        db.log(conn, "Sistem", "Reset", "Penghuni tanpa riwayat sewa dibersihkan")
