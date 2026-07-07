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