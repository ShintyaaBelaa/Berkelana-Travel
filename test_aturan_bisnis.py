"""
test_aturan_bisnis.py
=====================
Pengujian otomatis aturan bisnis B01–B10 Sistem Administrasi Travel Berkelana.
Setiap pengujian memakai database sementara sehingga data asli tidak berubah.

Jalankan:
    python -m unittest -v test_aturan_bisnis.py
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import database
import services


class AturanBisnisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tmp.name) / "berkelana_test.db"
        database.init_db(seed=True)

        conn = database.get_connection()
        try:
            self.id_rute = conn.execute(
                "SELECT id_rute FROM rute WHERE kode_rute = 'SY001'"
            ).fetchone()["id_rute"]
            self.id_rute_nonaktif = conn.execute(
                "SELECT id_rute FROM rute WHERE kode_rute = 'MG001'"
            ).fetchone()["id_rute"]
            self.id_pelanggan = conn.execute(
                "SELECT id_pelanggan FROM pelanggan WHERE kode_pelanggan = 'P001'"
            ).fetchone()["id_pelanggan"]
            self.id_pelanggan_2 = conn.execute(
                "SELECT id_pelanggan FROM pelanggan WHERE kode_pelanggan = 'P002'"
            ).fetchone()["id_pelanggan"]
            self.id_kursi = {
                row["nomor_kursi"]: row["id_kursi"]
                for row in conn.execute("SELECT * FROM kursi").fetchall()
            }
        finally:
            conn.close()

        self.tanggal = (date.today() + timedelta(days=10)).isoformat()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ------------------------------------------------------------------
    # B01 — data pelanggan wajib diisi
    # ------------------------------------------------------------------
    def test_b01_nama_kosong_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("   ", "081200001111")

    def test_b01_telepon_mengandung_huruf_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("Nama Baru", "0812ABC111")

    def test_b01_telepon_kosong_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("Nama Baru", "")

    def test_b01_telepon_dengan_spasi_atau_tanda_hubung_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("Nama Baru", "0812-0000 1111")

    def test_b01_data_valid_diterima(self):
        hasil = services.tambah_pelanggan("Nama Baru", "081200001111")
        self.assertEqual(hasil["kode_pelanggan"][0], "P")
        self.assertEqual(hasil["nama_pelanggan"], "Nama Baru")

    # ------------------------------------------------------------------
    # B02 — pelanggan tidak boleh ganda
    # ------------------------------------------------------------------
    def test_b02_nama_dan_telepon_sama_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("Andi Pratama", "081234567890")

    def test_b02_nama_sama_telepon_beda_diterima(self):
        hasil = services.tambah_pelanggan("Andi Pratama", "081200009999")
        self.assertNotEqual(hasil["kode_pelanggan"], "P001")

    def test_b02_duplikasi_tidak_peka_huruf_besar_kecil(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_pelanggan("aNDI pRATAMA", "081234567890")

    def test_b02_ubah_pelanggan_menjadi_duplikat_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.ubah_pelanggan(self.id_pelanggan_2, "Andi Pratama", "081234567890")

    # ------------------------------------------------------------------
    # B03 — rute harus benar
    # ------------------------------------------------------------------
    def test_b03_asal_sama_tujuan_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_rute("Solo", "solo", 50_000)

    def test_b03_tarif_nol_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_rute("Semarang", "Pekalongan", 0)

    def test_b03_rute_valid_diterima(self):
        hasil = services.tambah_rute("Semarang", "Pekalongan", 60_000)
        self.assertEqual(hasil["harga_tiket"], 60_000)
        self.assertEqual(hasil["aktif"], 1)

    # ------------------------------------------------------------------
    # B04 — rute yang dipakai tidak boleh dihapus
    # ------------------------------------------------------------------
    def test_b04_rute_dipakai_tidak_bisa_dihapus(self):
        with self.assertRaises(services.AturanBisnisError):
            services.hapus_rute(self.id_rute)

    def test_b04_rute_bisa_dinonaktifkan(self):
        services.atur_status_rute(self.id_rute, False)
        rute = services.ambil_rute(self.id_rute)
        self.assertEqual(rute["aktif"], 0)
        aktif = services.daftar_rute(hanya_aktif=True)
        self.assertNotIn(self.id_rute, [row["id_rute"] for row in aktif])

    def test_b04_rute_belum_dipakai_bisa_dihapus(self):
        baru = services.tambah_rute("Semarang", "Blora", 45_000)
        kode = services.hapus_rute(baru["id_rute"])
        self.assertEqual(kode, baru["kode_rute"])

    # ------------------------------------------------------------------
    # B05 — data harus terdaftar
    # ------------------------------------------------------------------
    def test_b05_rute_nonaktif_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan,
                self.id_rute_nonaktif,
                self.tanggal,
                "10:00",
                [self.id_kursi["K3"]],
            )

    def test_b05_pelanggan_tidak_terdaftar_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                999_999,
                self.id_rute,
                self.tanggal,
                "10:00",
                [self.id_kursi["K3"]],
            )

    # ------------------------------------------------------------------
    # B06 — jadwal belum terlewati
    # ------------------------------------------------------------------
    def test_b06_jadwal_kemarin_ditolak(self):
        kemarin = (date.today() - timedelta(days=1)).isoformat()
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan,
                self.id_rute,
                kemarin,
                "08:00",
                [self.id_kursi["K3"]],
            )

    def test_b06_jadwal_mendatang_diterima(self):
        nota = services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "10:00",
            [self.id_kursi["K3"]],
        )
        self.assertTrue(nota["kode_pemesanan"].startswith("PSN"))

    # ------------------------------------------------------------------
    # B07 — minimal satu kursi dan tidak boleh duplikat
    # ------------------------------------------------------------------
    def test_b07_tanpa_kursi_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan, self.id_rute, self.tanggal, "10:00", []
            )

    def test_b07_kursi_duplikat_dalam_satu_pemesanan_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan,
                self.id_rute,
                self.tanggal,
                "10:00",
                [self.id_kursi["K3"], self.id_kursi["K3"]],
            )

    # ------------------------------------------------------------------
    # B08 — kursi tidak boleh sama pada jadwal yang sama
    # ------------------------------------------------------------------
    def test_b08_kursi_sama_jadwal_sama_ditolak(self):
        services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "12:00",
            [self.id_kursi["K4"]],
        )
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan_2,
                self.id_rute,
                self.tanggal,
                "12:00",
                [self.id_kursi["K4"]],
            )

    def test_b08_kursi_sama_tanggal_beda_diterima(self):
        services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "12:00",
            [self.id_kursi["K4"]],
        )
        besok = (date.today() + timedelta(days=11)).isoformat()
        nota = services.buat_pemesanan(
            self.id_pelanggan_2,
            self.id_rute,
            besok,
            "12:00",
            [self.id_kursi["K4"]],
        )
        self.assertEqual(nota["daftar_kursi"], "K4")

    def test_b08_kursi_nonaktif_ditolak(self):
        services.atur_status_kursi(self.id_kursi["K6"], False)
        with self.assertRaises(services.AturanBisnisError):
            services.buat_pemesanan(
                self.id_pelanggan,
                self.id_rute,
                self.tanggal,
                "16:00",
                [self.id_kursi["K6"]],
            )

    # ------------------------------------------------------------------
    # B09 — harga saat pemesanan
    # ------------------------------------------------------------------
    def test_b09_total_harga_dua_kursi(self):
        nota = services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "14:00",
            [self.id_kursi["K7"], self.id_kursi["K8"]],
        )
        self.assertEqual(nota["jumlah_pesan_tiket"], 2)
        self.assertEqual(nota["harga_per_tiket"], 75_000)
        self.assertEqual(nota["total_harga"], 150_000)

    def test_b09_perubahan_tarif_tidak_mengubah_nota_lama(self):
        nota = services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "15:00",
            [self.id_kursi["K3"]],
        )
        services.ubah_rute(self.id_rute, "Semarang", "Solo", 100_000)

        lama = services.ambil_nota(nota["id_pemesanan"])
        self.assertEqual(lama["harga_per_tiket"], 75_000)
        self.assertEqual(lama["total_harga"], 75_000)

        baru = services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "16:00",
            [self.id_kursi["K4"]],
        )
        self.assertEqual(baru["harga_per_tiket"], 100_000)
        self.assertEqual(baru["total_harga"], 100_000)

    # ------------------------------------------------------------------
    # B10 — pembatalan
    # ------------------------------------------------------------------
    def test_b10_pembatalan_membebaskan_kursi(self):
        nota = services.buat_pemesanan(
            self.id_pelanggan,
            self.id_rute,
            self.tanggal,
            "18:00",
            [self.id_kursi["K5"]],
        )
        hasil = services.batalkan_pemesanan(nota["id_pemesanan"])
        self.assertEqual(hasil["kode_pemesanan"], nota["kode_pemesanan"])

        tersedia = services.ambil_kursi_untuk_jadwal(
            self.id_rute, self.tanggal, "18:00"
        )
        kursi_k5 = next(row for row in tersedia if row["nomor_kursi"] == "K5")
        self.assertEqual(kursi_k5["terisi"], 0)

        with self.assertRaises(services.DataTidakDitemukanError):
            services.batalkan_pemesanan(nota["id_pemesanan"])

    def test_b10_pembatalan_tidak_ditemukan_ditolak(self):
        with self.assertRaises(services.DataTidakDitemukanError):
            services.batalkan_pemesanan(999_999)

    # ------------------------------------------------------------------
    # Integritas data lain
    # ------------------------------------------------------------------
    def test_pelanggan_bertransaksi_tidak_bisa_dihapus(self):
        with self.assertRaises(services.AturanBisnisError):
            services.hapus_pelanggan(self.id_pelanggan)

    def test_kursi_sudah_dipakai_tidak_bisa_dihapus(self):
        with self.assertRaises(services.AturanBisnisError):
            services.hapus_kursi(self.id_kursi["K1"])

    def test_nomor_kursi_ganda_ditolak(self):
        with self.assertRaises(services.AturanBisnisError):
            services.tambah_kursi("K1")

    def test_kursi_baru_dan_unik_diterima(self):
        hasil = services.tambah_kursi("k9")
        self.assertEqual(hasil["nomor_kursi"], "K9")

    def test_pencarian_pemesanan_berdasarkan_nama(self):
        hasil = services.cari_pemesanan(q="Andi")
        self.assertTrue(hasil)
        self.assertTrue(all("Andi" in row["nama_pelanggan"] for row in hasil))

    def test_seed_tidak_dibuat_ulang_saat_inisialisasi_berikutnya(self):
        conn = database.get_connection()
        try:
            jumlah_awal = conn.execute("SELECT COUNT(*) AS n FROM pelanggan").fetchone()["n"]
        finally:
            conn.close()

        database.init_db(seed=True)

        conn = database.get_connection()
        try:
            jumlah_akhir = conn.execute("SELECT COUNT(*) AS n FROM pelanggan").fetchone()["n"]
        finally:
            conn.close()
        self.assertEqual(jumlah_awal, jumlah_akhir)

    def test_kode_pemesanan_berurutan_dan_unik(self):
        nota1 = services.buat_pemesanan(
            self.id_pelanggan, self.id_rute, self.tanggal, "19:00", [self.id_kursi["K7"]]
        )
        nota2 = services.buat_pemesanan(
            self.id_pelanggan, self.id_rute, self.tanggal, "20:00", [self.id_kursi["K8"]]
        )
        self.assertNotEqual(nota1["kode_pemesanan"], nota2["kode_pemesanan"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
