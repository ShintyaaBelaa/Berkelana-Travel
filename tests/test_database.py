"""Pengujian aturan bisnis inti tanpa antarmuka Streamlit.

Jalankan dari folder proyek:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta, time
from pathlib import Path

_TMP = tempfile.TemporaryDirectory()
os.environ["BERKELANA_DB"] = str(Path(_TMP.name) / "berkelana_test.db")

import database as db  # noqa: E402  (environment harus diset sebelum import)


class BasisUji(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(os.environ["BERKELANA_DB"])
        for suffix in ("", "-wal", "-shm"):
            berkas = Path(str(path) + suffix)
            if berkas.exists():
                berkas.unlink()
        db.init_db(seed=False)
        self.pelanggan = db.tambah_pelanggan("Andi Pratama", "081234567890")
        self.pelanggan2 = db.tambah_pelanggan("Siti Aminah", "081298765432")
        self.rute = db.tambah_rute("Semarang", "Solo", 75_000, True)
        self.rute_nonaktif = db.tambah_rute("Semarang", "Magelang", 85_000, False)

    def kursi(self, nomor: str) -> int:
        return next(k["id_kursi"] for k in db.daftar_kursi() if k["nomor_kursi"] == nomor)

    def jadwal(self, offset: int = 5, jam: int = 7) -> tuple[date, time]:
        return date.today() + timedelta(days=offset), time(jam, 0)

    def jadwal_kode(self, kode: str) -> dict:
        return next(j for j in db.daftar_jadwal() if j["kode_jadwal"] == kode)


class UjiPelanggan(BasisUji):
    def test_tolak_nama_dan_telepon_ganda(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_pelanggan("ANDI PRATAMA", "081234567890")

    def test_tolak_telepon_mengandung_huruf(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_pelanggan("Budi", "0812ABC")
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_pelanggan("Budi", "0812-3456")

    def test_nama_dan_telepon_wajib(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_pelanggan("", "081200000000")
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_pelanggan("Budi", "   ")

    def test_kode_pelanggan_berurutan(self) -> None:
        budi = db.tambah_pelanggan("Budi Santoso", "085712345678")
        self.assertEqual(budi["kode_pelanggan"], "P003")

    def test_tidak_bisa_hapus_pelanggan_yang_punya_transaksi(self) -> None:
        tanggal, jam = self.jadwal()
        db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        with self.assertRaises(db.KesalahanBisnis):
            db.hapus_pelanggan(self.pelanggan["id_pelanggan"])


class UjiRute(BasisUji):
    def test_asal_dan_tujuan_tidak_boleh_sama(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_rute("Solo", "solo", 50_000)

    def test_tarif_harus_positif(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_rute("Solo", "Semarang", 0)
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_rute("Solo", "Semarang", -5)

    def test_rute_terpakai_tidak_bisa_dihapus(self) -> None:
        tanggal, jam = self.jadwal()
        db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        with self.assertRaises(db.KesalahanBisnis):
            db.hapus_rute(self.rute["id_rute"])

    def test_rute_belum_terpakai_bisa_dihapus(self) -> None:
        baru = db.tambah_rute("Solo", "Semarang", 75_000)
        db.hapus_rute(baru["id_rute"])
        self.assertIsNone(db.ambil_rute(baru["id_rute"]))

    def test_rute_nonaktif_tidak_bisa_dipesan(self) -> None:
        tanggal, jam = self.jadwal()
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute_nonaktif["id_rute"],
                tanggal,
                jam,
                [self.kursi("K1")],
            )

    def test_rute_baru_memiliki_tiga_jadwal_dan_kode_bisnis(self) -> None:
        jadwal = db.daftar_jadwal(id_rute=self.rute["id_rute"])
        self.assertEqual(
            [j["kode_jadwal"] for j in jadwal],
            ["SS001", "SS002", "SS003"],
        )
        self.assertEqual(
            [j["jam_keberangkatan"] for j in jadwal],
            ["07:00", "12:00", "17:00"],
        )
        self.assertEqual(
            [j["urut_keberangkatan"] for j in jadwal],
            [1, 2, 3],
        )

    def test_rute_ganda_ditolak(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_rute("semarang", "SOLO", 80_000)


class UjiJadwal(BasisUji):
    def test_nonaktifkan_satu_jam_hanya_menutup_jam_tersebut(self) -> None:
        pagi = self.jadwal_kode("SS001")
        db.atur_status_jadwal(pagi["id_jadwal"], False)

        aktif = [
            j["kode_jadwal"]
            for j in db.daftar_jadwal(id_rute=self.rute["id_rute"], hanya_aktif=True)
        ]
        self.assertEqual(aktif, ["SS002", "SS003"])

        tanggal = date.today() + timedelta(days=5)
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute["id_rute"],
                tanggal,
                time(7, 0),
                [self.kursi("K1")],
            )
        detail = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            time(12, 0),
            [self.kursi("K2")],
        )
        self.assertEqual(detail["kode_jadwal"], "SS002")

    def test_jadwal_nonaktif_bisa_diaktifkan_kembali(self) -> None:
        pagi = self.jadwal_kode("SS001")
        db.atur_status_jadwal(pagi["id_jadwal"], False)
        db.atur_status_jadwal(pagi["id_jadwal"], True)

        tanggal = date.today() + timedelta(days=5)
        detail = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            time(7, 0),
            [self.kursi("K1")],
        )
        self.assertEqual(detail["kode_jadwal"], "SS001")

    def test_status_jadwal_tetap_saat_rute_dinonaktifkan_dan_diaktifkan(self) -> None:
        pagi = self.jadwal_kode("SS001")
        db.atur_status_jadwal(pagi["id_jadwal"], False)
        db.atur_status_rute(self.rute["id_rute"], False)
        db.atur_status_rute(self.rute["id_rute"], True)

        self.assertEqual(db.ambil_jadwal(pagi["id_jadwal"])["aktif"], 0)
        siang = self.jadwal_kode("SS002")
        self.assertEqual(db.ambil_jadwal(siang["id_jadwal"])["aktif"], 1)

    def test_tidak_bisa_aktifkan_jadwal_saat_rute_nonaktif(self) -> None:
        jadwal = db.daftar_jadwal(id_rute=self.rute_nonaktif["id_rute"])[0]
        db.atur_status_jadwal(jadwal["id_jadwal"], False)
        with self.assertRaises(db.KesalahanBisnis):
            db.atur_status_jadwal(jadwal["id_jadwal"], True)
        self.assertEqual(db.ambil_jadwal(jadwal["id_jadwal"])["aktif"], 0)

    def test_jadwal_rute_baru_nonaktif_tetap_siap_diaktifkan(self) -> None:
        baru = db.tambah_rute("Semarang", "Demak", 50_000, False)
        jadwal = db.daftar_jadwal(id_rute=baru["id_rute"])
        self.assertEqual([j["aktif"] for j in jadwal], [1, 1, 1])
        self.assertFalse(jadwal[0]["rute_aktif"])


class UjiKursi(BasisUji):
    def test_kursi_awal_k1_sampai_k8(self) -> None:
        nomor = [k["nomor_kursi"] for k in db.daftar_kursi()]
        self.assertEqual(nomor, [f"K{i}" for i in range(1, 9)])

    def test_nomor_kursi_harus_unik_dan_berpola(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_kursi("K1")
        with self.assertRaises(db.KesalahanBisnis):
            db.tambah_kursi("A1")
        self.assertEqual(db.tambah_kursi("K9")["nomor_kursi"], "K9")

    def test_kursi_terpakai_tidak_bisa_dihapus_atau_diganti_nomor(self) -> None:
        tanggal, jam = self.jadwal()
        db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        with self.assertRaises(db.KesalahanBisnis):
            db.hapus_kursi(self.kursi("K1"))
        with self.assertRaises(db.KesalahanBisnis):
            db.ubah_kursi(self.kursi("K1"), "K9", True)

    def test_kursi_nonaktif_tidak_tersedia(self) -> None:
        db.ubah_kursi(self.kursi("K8"), "K8", False)
        tanggal, jam = self.jadwal()
        tersedia = [k["nomor_kursi"] for k in db.kursi_tersedia(self.rute["id_rute"], tanggal, jam)]
        self.assertNotIn("K8", tersedia)
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute["id_rute"],
                tanggal,
                jam,
                [self.kursi("K8")],
            )


class UjiPemesanan(BasisUji):
    def test_total_dan_snapshot_harga(self) -> None:
        tanggal, jam = self.jadwal()
        detail = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1"), self.kursi("K2")],
        )
        self.assertEqual(detail["jumlah_pesan_tiket"], 2)
        self.assertEqual(detail["harga_saat_pemesanan"], 75_000)
        self.assertEqual(detail["total_harga"], 150_000)
        self.assertEqual(detail["nomor_kursi"], "K1, K2")

        db.ubah_rute(self.rute["id_rute"], "Semarang", "Solo", 99_000, True)
        ulang = db.ambil_pemesanan(detail["id_pemesanan"])
        self.assertEqual(ulang["harga_saat_pemesanan"], 75_000)
        self.assertEqual(ulang["total_harga"], 150_000)

    def test_detail_pemesanan_memuat_kode_jadwal(self) -> None:
        tanggal, jam = self.jadwal()
        detail = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        self.assertEqual(detail["kode_jadwal"], "SS001")

    def test_jadwal_di_luar_tiga_jam_resmi_ditolak(self) -> None:
        tanggal, _ = self.jadwal()
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute["id_rute"],
                tanggal,
                time(8, 0),
                [self.kursi("K1")],
            )

    def test_minimal_satu_kursi(self) -> None:
        tanggal, jam = self.jadwal()
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"], self.rute["id_rute"], tanggal, jam, []
            )

    def test_kursi_ganda_dalam_satu_pemesanan_ditolak(self) -> None:
        tanggal, jam = self.jadwal()
        k1 = self.kursi("K1")
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute["id_rute"],
                tanggal,
                jam,
                [k1, k1],
            )

    def test_kursi_sama_pada_jadwal_sama_ditolak(self) -> None:
        tanggal, jam = self.jadwal()
        db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan2["id_pelanggan"],
                self.rute["id_rute"],
                tanggal,
                jam,
                [self.kursi("K1")],
            )

    def test_kursi_sama_boleh_untuk_tanggal_berbeda(self) -> None:
        db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            *self.jadwal(5),
            [self.kursi("K1")],
        )
        db.buat_pemesanan(
            self.pelanggan2["id_pelanggan"],
            self.rute["id_rute"],
            *self.jadwal(6),
            [self.kursi("K1")],
        )
        self.assertEqual(len(db.daftar_pemesanan()), 2)

    def test_jadwal_masa_lalu_ditolak(self) -> None:
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(
                self.pelanggan["id_pelanggan"],
                self.rute["id_rute"],
                date.today() - timedelta(days=1),
                time(7, 0),
                [self.kursi("K1")],
            )

    def test_pelanggan_harus_terdaftar(self) -> None:
        tanggal, jam = self.jadwal()
        with self.assertRaises(db.KesalahanBisnis):
            db.buat_pemesanan(99999, self.rute["id_rute"], tanggal, jam, [self.kursi("K1")])

    def test_pembatalan_menghapus_transaksi_dan_mengembalikan_kursi(self) -> None:
        tanggal, jam = self.jadwal()
        detail = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1"), self.kursi("K2")],
        )
        db.batalkan_pemesanan(detail["id_pemesanan"])
        self.assertEqual(db.daftar_pemesanan(), [])
        tersedia = [k["nomor_kursi"] for k in db.kursi_tersedia(self.rute["id_rute"], tanggal, jam)]
        self.assertIn("K1", tersedia)
        self.assertIn("K2", tersedia)
        with self.assertRaises(db.KesalahanBisnis):
            db.batalkan_pemesanan(detail["id_pemesanan"])

    def test_kode_pemesanan_tidak_digunakan_ulang_setelah_batal(self) -> None:
        tanggal, jam = self.jadwal()
        pertama = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        db.batalkan_pemesanan(pertama["id_pemesanan"])
        kedua = db.buat_pemesanan(
            self.pelanggan2["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        self.assertNotEqual(pertama["kode_pemesanan"], kedua["kode_pemesanan"])

    def test_trigger_database_menolak_kursi_ganda(self) -> None:
        tanggal, jam = self.jadwal()
        pertama = db.buat_pemesanan(
            self.pelanggan["id_pelanggan"],
            self.rute["id_rute"],
            tanggal,
            jam,
            [self.kursi("K1")],
        )
        with db.koneksi() as conn:
            harga = 75_000
            cur = conn.execute(
                "INSERT INTO pemesanan (kode_pemesanan, id_pelanggan, id_rute, "
                "tanggal_keberangkatan, jam_keberangkatan, jumlah_pesan_tiket, "
                "harga_saat_pemesanan, total_harga) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (
                    "PSNX",
                    self.pelanggan2["id_pelanggan"],
                    self.rute["id_rute"],
                    tanggal.isoformat(),
                    jam.strftime("%H:%M"),
                    harga,
                    harga,
                ),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO detail_pemesanan (id_pemesanan, id_kursi, harga_satuan) "
                    "VALUES (?, ?, ?)",
                    (cur.lastrowid, self.kursi("K1"), harga),
                )
            conn.rollback()
        self.assertEqual(len(db.daftar_pemesanan()), 1)


class UjiDataContoh(unittest.TestCase):
    def test_inisialisasi_data_contoh(self) -> None:
        path = Path(os.environ["BERKELANA_DB"])
        for suffix in ("", "-wal", "-shm"):
            berkas = Path(str(path) + suffix)
            if berkas.exists():
                berkas.unlink()
        db.init_db(seed=True)
        ringkasan = db.ringkasan_dashboard()
        self.assertEqual(ringkasan["total_pelanggan"], 6)
        self.assertEqual(ringkasan["total_rute"], 5)
        self.assertEqual(ringkasan["total_jadwal"], 15)
        self.assertEqual(ringkasan["total_kursi"], 8)
        self.assertEqual(ringkasan["total_pemesanan"], 14)
        self.assertGreater(ringkasan["total_pendapatan"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
