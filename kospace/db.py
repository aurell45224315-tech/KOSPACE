"""KOSPACE - Lapisan database SQLite.

Berisi skema, koneksi, seed kamar, serta fungsi baca yang dipakai bersama
oleh seluruh halaman aplikasi.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "kospace.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS kamar (
    id_kamar       TEXT PRIMARY KEY,
    nomor_kamar    TEXT NOT NULL UNIQUE,
    tipe           TEXT NOT NULL,
    harga_bulanan  INTEGER NOT NULL CHECK (harga_bulanan > 0),
    fasilitas      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Tersedia'
                   CHECK (status IN ('Tersedia', 'Ditempati'))
);

CREATE TABLE IF NOT EXISTS penghuni (
    id_penghuni   TEXT PRIMARY KEY,
    nama          TEXT NOT NULL,
    telepon       TEXT NOT NULL,
    telepon_ortu  TEXT,
    alamat        TEXT
);

CREATE TABLE IF NOT EXISTS sewa (
    id_sewa         TEXT PRIMARY KEY,
    id_penghuni     TEXT NOT NULL,
    id_kamar        TEXT NOT NULL,
    tanggal_mulai   TEXT NOT NULL,
    tanggal_selesai TEXT NOT NULL,
    durasi          INTEGER NOT NULL CHECK (durasi > 0),
    harga_bulanan   INTEGER NOT NULL CHECK (harga_bulanan > 0),
    status_sewa     TEXT NOT NULL DEFAULT 'Aktif'
                    CHECK (status_sewa IN ('Aktif', 'Selesai')),
    CHECK (tanggal_selesai > tanggal_mulai),
    FOREIGN KEY (id_penghuni) REFERENCES penghuni(id_penghuni)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (id_kamar) REFERENCES kamar(id_kamar)
        ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS pembayaran (
    id_pembayaran      TEXT PRIMARY KEY,
    id_sewa            TEXT NOT NULL,
    periode_bulan      INTEGER NOT NULL CHECK (periode_bulan BETWEEN 1 AND 12),
    periode_tahun      INTEGER NOT NULL CHECK (periode_tahun BETWEEN 2000 AND 2100),
    tanggal_bayar      TEXT NOT NULL,
    nominal            INTEGER NOT NULL CHECK (nominal > 0),
    status_pembayaran  TEXT NOT NULL DEFAULT 'Lunas'
                       CHECK (status_pembayaran IN ('Lunas', 'Belum Dibayar', 'Terlambat')),
    UNIQUE (id_sewa, periode_bulan, periode_tahun),
    FOREIGN KEY (id_sewa) REFERENCES sewa(id_sewa)
        ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS log_aktivitas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    waktu       TEXT NOT NULL,
    aksi        TEXT NOT NULL,
    entitas     TEXT NOT NULL,
    keterangan  TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    kunci  TEXT PRIMARY KEY,
    nilai  TEXT
);

CREATE INDEX IF NOT EXISTS idx_sewa_kamar      ON sewa(id_kamar);
CREATE INDEX IF NOT EXISTS idx_sewa_penghuni   ON sewa(id_penghuni);
CREATE INDEX IF NOT EXISTS idx_sewa_status     ON sewa(status_sewa);
CREATE INDEX IF NOT EXISTS idx_bayar_sewa      ON pembayaran(id_sewa);
CREATE INDEX IF NOT EXISTS idx_bayar_periode   ON pembayaran(periode_tahun, periode_bulan);
CREATE INDEX IF NOT EXISTS idx_kamar_status    ON kamar(status);
"""


# ---------------------------------------------------------------------------
# Koneksi
# ---------------------------------------------------------------------------
@contextmanager
def connection():
    """Buka koneksi baru dengan foreign key aktif dan commit otomatis."""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO meta (kunci, nilai) VALUES ('versi', '1.0')"
        )
        total = conn.execute("SELECT COUNT(*) FROM kamar").fetchone()[0]
        if total == 0:
            _seed_rooms(conn)
            conn.execute(
                "INSERT OR REPLACE INTO meta (kunci, nilai) VALUES ('rooms_seeded', '1')"
            )


def _seed_rooms(conn: sqlite3.Connection) -> None:
    """25 kamar: A01-A05, B01-B10, C01-C10 sesuai dokumen KOSPACE."""
    tipe_data = [
        ("Tipe A", "A", 5, 1_300_000, "AC, Wi-Fi, kamar mandi dalam"),
        ("Tipe B", "B", 10, 950_000, "AC, Wi-Fi, kamar mandi luar"),
        ("Tipe C", "C", 10, 700_000, "Kipas angin, Wi-Fi, kamar mandi luar"),
    ]
    counter = 1
    for tipe, prefix, jumlah, harga, fasilitas in tipe_data:
        for nomor in range(1, jumlah + 1):
            conn.execute(
                "INSERT INTO kamar (id_kamar, nomor_kamar, tipe, harga_bulanan, fasilitas, status) "
                "VALUES (?, ?, ?, ?, ?, 'Tersedia')",
                (
                    f"K{counter:03d}",
                    f"{prefix}{nomor:02d}",
                    tipe,
                    harga,
                    fasilitas,
                ),
            )
            counter += 1


# ---------------------------------------------------------------------------
# Primitif
# ---------------------------------------------------------------------------
def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with connection() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def scalar(sql: str, params: tuple = ()):
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else None


def next_id(conn: sqlite3.Connection, table: str, pk: str, prefix: str) -> str:
    rows = conn.execute(
        f"SELECT {pk} FROM {table} WHERE {pk} LIKE ?", (f"{prefix}%",)
    ).fetchall()
    maks = 0
    for row in rows:
        suffix = str(row[0])[len(prefix):]
        if suffix.isdigit():
            maks = max(maks, int(suffix))
    return f"{prefix}{maks + 1:03d}"


def log(conn: sqlite3.Connection, aksi: str, entitas: str, keterangan: str) -> None:
    conn.execute(
        "INSERT INTO log_aktivitas (waktu, aksi, entitas, keterangan) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), aksi, entitas, keterangan),
    )


def get_meta(kunci: str, default: str | None = None) -> str | None:
    row = fetch_one("SELECT nilai FROM meta WHERE kunci = ?", (kunci,))
    return row["nilai"] if row else default


def set_meta(kunci: str, nilai: str) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (kunci, nilai) VALUES (?, ?)", (kunci, nilai)
        )


# ---------------------------------------------------------------------------
# Query baca - Kamar
# ---------------------------------------------------------------------------
def _today_iso() -> str:
    return date.today().isoformat()


def list_kamar() -> list[dict]:
    today = _today_iso()
    return fetch_all(
        """
        SELECT k.*,
               (SELECT p.nama
                  FROM sewa s JOIN penghuni p ON p.id_penghuni = s.id_penghuni
                 WHERE s.id_kamar = k.id_kamar
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS penghuni_aktif,
               (SELECT s.id_sewa
                  FROM sewa s
                 WHERE s.id_kamar = k.id_kamar
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS sewa_aktif
          FROM kamar k
         ORDER BY k.nomor_kamar
        """,
        (today, today, today, today),
    )


def get_kamar(id_kamar: str) -> dict | None:
    today = _today_iso()
    return fetch_one(
        """
        SELECT k.*,
               (SELECT p.nama
                  FROM sewa s JOIN penghuni p ON p.id_penghuni = s.id_penghuni
                 WHERE s.id_kamar = k.id_kamar
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS penghuni_aktif,
               (SELECT s.id_sewa
                  FROM sewa s
                 WHERE s.id_kamar = k.id_kamar
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS sewa_aktif,
               (SELECT COUNT(*) FROM sewa s WHERE s.id_kamar = k.id_kamar) AS total_sewa
          FROM kamar k
         WHERE k.id_kamar = ?
        """,
        (today, today, today, today, id_kamar),
    )


# ---------------------------------------------------------------------------
# Query baca - Penghuni
# ---------------------------------------------------------------------------
def list_penghuni() -> list[dict]:
    today = _today_iso()
    return fetch_all(
        """
        SELECT p.*,
               (SELECT k.nomor_kamar
                  FROM sewa s JOIN kamar k ON k.id_kamar = s.id_kamar
                 WHERE s.id_penghuni = p.id_penghuni
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS kamar_aktif,
               (SELECT s.id_sewa
                  FROM sewa s
                 WHERE s.id_penghuni = p.id_penghuni
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS sewa_aktif,
               (SELECT COUNT(*) FROM sewa s WHERE s.id_penghuni = p.id_penghuni) AS total_sewa
          FROM penghuni p
         ORDER BY p.nama
        """,
        (today, today, today, today),
    )


def get_penghuni(id_penghuni: str) -> dict | None:
    today = _today_iso()
    return fetch_one(
        """
        SELECT p.*,
               (SELECT k.nomor_kamar
                  FROM sewa s JOIN kamar k ON k.id_kamar = s.id_kamar
                 WHERE s.id_penghuni = p.id_penghuni
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS kamar_aktif,
               (SELECT s.id_sewa
                  FROM sewa s
                 WHERE s.id_penghuni = p.id_penghuni
                   AND s.status_sewa = 'Aktif'
                   AND s.tanggal_mulai <= ? AND s.tanggal_selesai >= ?
                 ORDER BY s.tanggal_mulai DESC LIMIT 1) AS sewa_aktif,
               (SELECT COUNT(*) FROM sewa s WHERE s.id_penghuni = p.id_penghuni) AS total_sewa
          FROM penghuni p
         WHERE p.id_penghuni = ?
        """,
        (today, today, today, today, id_penghuni),
    )


# ---------------------------------------------------------------------------
# Query baca - Sewa
# ---------------------------------------------------------------------------
def list_sewa() -> list[dict]:
    return fetch_all(
        """
        SELECT s.*, p.nama, p.telepon, p.telepon_ortu,
               k.nomor_kamar, k.tipe, k.fasilitas,
               (SELECT COUNT(*) FROM pembayaran b WHERE b.id_sewa = s.id_sewa) AS jml_bayar,
               (SELECT COALESCE(SUM(b.nominal), 0) FROM pembayaran b
                 WHERE b.id_sewa = s.id_sewa) AS total_bayar
          FROM sewa s
          JOIN penghuni p ON p.id_penghuni = s.id_penghuni
          JOIN kamar k ON k.id_kamar = s.id_kamar
         ORDER BY s.tanggal_mulai DESC, s.id_sewa DESC
        """
    )


def get_sewa(id_sewa: str) -> dict | None:
    return fetch_one(
        """
        SELECT s.*, p.nama, p.telepon, p.telepon_ortu, p.alamat,
               k.nomor_kamar, k.tipe, k.fasilitas,
               (SELECT COUNT(*) FROM pembayaran b WHERE b.id_sewa = s.id_sewa) AS jml_bayar,
               (SELECT COALESCE(SUM(b.nominal), 0) FROM pembayaran b
                 WHERE b.id_sewa = s.id_sewa) AS total_bayar
          FROM sewa s
          JOIN penghuni p ON p.id_penghuni = s.id_penghuni
          JOIN kamar k ON k.id_kamar = s.id_kamar
         WHERE s.id_sewa = ?
        """,
        (id_sewa,),
    )


def sewa_for_penghuni(id_penghuni: str) -> list[dict]:
    return [
        row for row in list_sewa() if row["id_penghuni"] == id_penghuni
    ]


def sewa_for_kamar(id_kamar: str) -> list[dict]:
    return [row for row in list_sewa() if row["id_kamar"] == id_kamar]


# ---------------------------------------------------------------------------
# Query baca - Pembayaran
# ---------------------------------------------------------------------------
def list_pembayaran() -> list[dict]:
    return fetch_all(
        """
        SELECT b.*, s.id_penghuni, s.id_kamar, s.harga_bulanan AS harga_sewa,
               s.status_sewa, p.nama, p.telepon, k.nomor_kamar, k.tipe
          FROM pembayaran b
          JOIN sewa s ON s.id_sewa = b.id_sewa
          JOIN penghuni p ON p.id_penghuni = s.id_penghuni
          JOIN kamar k ON k.id_kamar = s.id_kamar
         ORDER BY b.tanggal_bayar DESC, b.id_pembayaran DESC
        """
    )


def get_pembayaran(id_pembayaran: str) -> dict | None:
    return fetch_one(
        """
        SELECT b.*, s.id_penghuni, s.id_kamar, s.harga_bulanan AS harga_sewa,
               s.status_sewa, s.tanggal_mulai, s.tanggal_selesai,
               p.nama, p.telepon, k.nomor_kamar, k.tipe
          FROM pembayaran b
          JOIN sewa s ON s.id_sewa = b.id_sewa
          JOIN penghuni p ON p.id_penghuni = s.id_penghuni
          JOIN kamar k ON k.id_kamar = s.id_kamar
         WHERE b.id_pembayaran = ?
        """,
        (id_pembayaran,),
    )


def pembayaran_for_sewa(id_sewa: str) -> list[dict]:
    return [
        row for row in list_pembayaran() if row["id_sewa"] == id_sewa
    ]


def pembayaran_for_penghuni(id_penghuni: str) -> list[dict]:
    return [
        row for row in list_pembayaran() if row["id_penghuni"] == id_penghuni
    ]


def pembayaran_for_kamar(id_kamar: str) -> list[dict]:
    return [row for row in list_pembayaran() if row["id_kamar"] == id_kamar]


def payments_map() -> dict[tuple[str, int, int], dict]:
    data = {}
    for row in list_pembayaran():
        data[(row["id_sewa"], row["periode_tahun"], row["periode_bulan"])] = row
    return data


# ---------------------------------------------------------------------------
# Query baca - Log & statistik
# ---------------------------------------------------------------------------
def list_log(limit: int = 30) -> list[dict]:
    return fetch_all(
        "SELECT * FROM log_aktivitas ORDER BY id DESC LIMIT ?", (limit,)
    )


def count_table(table: str) -> int:
    allowed = {"kamar", "penghuni", "sewa", "pembayaran", "log_aktivitas"}
    if table not in allowed:
        raise ValueError("Tabel tidak dikenal")
    return int(scalar(f"SELECT COUNT(*) FROM {table}") or 0)


def database_info() -> dict:
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "path": str(DB_PATH),
        "size_kb": round(size / 1024, 1),
        "kamar": count_table("kamar"),
        "penghuni": count_table("penghuni"),
        "sewa": count_table("sewa"),
        "pembayaran": count_table("pembayaran"),
    }
