from models.database import Database
from models.absensi_model import get_rekap_bulanan

def get_detail_gaji_karyawan(nama):
    # 1. Ambil Gaji Pokok & Tunjangan dari database (asumsi ada tabel karyawan)
    query_karyawan = "SELECT gaji_pokok, tunjangan FROM karyawan WHERE nama = %s"
    data_karyawan = Database.fetch_one(query_karyawan, (nama,))
    
    if not data_karyawan:
        return None

    pokok = data_karyawan['gaji_pokok']
    tunjangan = data_karyawan['tunjangan']
    
    # 2. Ambil data absensi (Alpha) untuk potongan
    rekap = get_rekap_bulanan(nama)
    jumlah_alpha = rekap['Alpha']
    
    # 3. Hitung potongan (asumsi 25 hari kerja)
    potongan_per_hari = pokok / 25
    total_potongan = potongan_per_hari * jumlah_alpha
    
    # 4. Hitung Gaji Bersih
    total_bersih = (pokok + tunjangan) - total_potongan
    
    return {
        "nama": nama,
        "pokok": pokok,
        "tunjangan": tunjangan,
        "jumlah_alpha": jumlah_alpha,
        "total_potongan": total_potongan,
        "total_bersih": total_bersih
    }

# ============================================================
# BARU: Sistem Slip Gaji Tersimpan (snapshot per bulan)
# Dipakai supaya data gaji Direktur & Karyawan/Admin selalu sinkron,
# dan supaya karyawan bisa lihat riwayat gaji bulan-bulan sebelumnya.
# ============================================================

NAMA_BULAN = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}


def simpan_slip_gaji(karyawan_id, bulan, tahun, data):
    """
    Simpan snapshot gaji (dipanggil saat direktur klik 'Kirim Slip').
    Kalau slip bulan itu sudah pernah ada, akan di-update (bukan dobel).
    `data` adalah dict hasil dari _hitung_rincian_gaji() di direktur_controller.
    """
    query = """
        INSERT INTO slip_gaji
            (karyawan_id, bulan, tahun, gaji_pokok, tunjangan, total_penghasilan,
             hadir, cuti, sakit, izin_lainnya, alpha, jumlah_hari_potong,
             total_potongan, gaji_bersih, tanggal_kirim)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            gaji_pokok = VALUES(gaji_pokok),
            tunjangan = VALUES(tunjangan),
            total_penghasilan = VALUES(total_penghasilan),
            hadir = VALUES(hadir),
            cuti = VALUES(cuti),
            sakit = VALUES(sakit),
            izin_lainnya = VALUES(izin_lainnya),
            alpha = VALUES(alpha),
            jumlah_hari_potong = VALUES(jumlah_hari_potong),
            total_potongan = VALUES(total_potongan),
            gaji_bersih = VALUES(gaji_bersih),
            tanggal_kirim = NOW()
    """
    rekap = data['rekap']
    Database.execute_query(query, (
        karyawan_id, bulan, tahun,
        data['gaji_pokok'], data['tunjangan'], data['total_penghasilan'],
        rekap.get('Hadir', 0), rekap.get('Cuti', 0), rekap.get('Sakit', 0),
        rekap.get('Izin Lainnya', 0), rekap.get('Alpha', 0),
        data['jumlah_hari_potong'], data['total_potongan'], data['gaji_bersih']
    ))


def get_slip_gaji(karyawan_id, bulan, tahun):
    """Ambil 1 snapshot slip gaji spesifik. None kalau belum pernah dikirim di bulan itu."""
    query = """
        SELECT * FROM slip_gaji
        WHERE karyawan_id = %s AND bulan = %s AND tahun = %s
    """
    rows = Database.fetch_all(query, (karyawan_id, bulan, tahun))
    if not rows:
        return None
    row = rows[0]
    row['rekap'] = {
        "Hadir": row['hadir'],
        "Cuti": row['cuti'],
        "Sakit": row['sakit'],
        "Izin Lainnya": row['izin_lainnya'],
        "Alpha": row['alpha'],
    }
    return row


def is_slip_terkirim(karyawan_id, bulan, tahun):
    return get_slip_gaji(karyawan_id, bulan, tahun) is not None


def get_semua_bulan_tersedia(karyawan_id):
    """Daftar bulan-tahun yang punya slip gaji, terbaru duluan. Buat isi dropdown riwayat."""
    query = """
        SELECT DISTINCT bulan, tahun FROM slip_gaji
        WHERE karyawan_id = %s
        ORDER BY tahun DESC, bulan DESC
    """
    return Database.fetch_all(query, (karyawan_id,))