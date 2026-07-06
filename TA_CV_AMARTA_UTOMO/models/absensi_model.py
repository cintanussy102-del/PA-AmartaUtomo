import datetime
from models.database import Database


def get_riwayat_absensi(nama, limit=None):
    query = """
        SELECT tanggal, jam_masuk AS masuk, jam_keluar AS keluar,
               status, keterangan, file_bukti
        FROM absensi
        WHERE nama_karyawan = %s
        ORDER BY tanggal DESC
    """
    if limit:
        query += " LIMIT %s"
        rows = Database.fetch_all(query, (nama, limit))
    else:
        rows = Database.fetch_all(query, (nama,))

    for row in rows:
        row['tanggal'] = format_tanggal_indonesia(row['tanggal'])
        row['masuk'] = row['masuk'] or '-'
        row['keluar'] = row['keluar'] or '-'
    return rows


def get_status_hari_ini(nama):
    query = """
        SELECT tanggal, jam_masuk AS masuk, jam_keluar AS keluar,
               status, keterangan, file_bukti
        FROM absensi
        WHERE nama_karyawan = %s AND tanggal = %s
    """
    hari_ini = datetime.date.today()
    rows = Database.fetch_all(query, (nama, hari_ini))
    if rows:
        row = rows[0]
        row['masuk'] = row['masuk'] or '-'
        row['keluar'] = row['keluar'] or '-'
        return row
    return None


def catat_absen_masuk(nama, lat, lon, alamat):
    hari_ini = datetime.date.today()
    jam = datetime.datetime.now().strftime("%H:%M")

    # SQL ini akan memasukkan data termasuk koordinat dan alamat
    query = """
        INSERT INTO absensi (nama_karyawan, tanggal, jam_masuk, status, status_approval, lat, lon, alamat)
        VALUES (%s, %s, %s, 'Hadir', 'Approved', %s, %s, %s)
    """
    Database.execute_query(query, (nama, hari_ini, jam, lat, lon, alamat))
    return get_status_hari_ini(nama)


def catat_absen_keluar(nama, lat=None, lon=None, alamat=None):
    hari_ini = datetime.date.today()
    jam = datetime.datetime.now().strftime("%H:%M")

    existing = get_status_hari_ini(nama)
    if existing:        
        query = "UPDATE absensi SET jam_keluar = %s, lat = %s, lon = %s, alamat = %s WHERE nama_karyawan = %s AND tanggal = %s"
        Database.execute_query(query, (jam, lat, lon, alamat, nama, hari_ini))
    else:
        query = "INSERT INTO absensi (nama_karyawan, tanggal, jam_keluar, status, status_approval, lat, lon, alamat) VALUES (%s, %s, %s, 'Hadir', 'Approved', %s, %s, %s)"
        Database.execute_query(query, (nama, hari_ini, jam, lat, lon, alamat))

    return get_status_hari_ini(nama)


def ajukan_izin(nama, jenis_izin, tanggal, keterangan, file_bukti=None):
    query = """
        INSERT INTO absensi (nama_karyawan, tanggal, status, keterangan, file_bukti, status_approval)
        VALUES (%s, %s, %s, %s, %s, 'Pending')
        ON DUPLICATE KEY UPDATE
            status = %s, keterangan = %s, file_bukti = %s, status_approval = 'Pending'
    """
    Database.execute_query(
        query,
        (nama, tanggal, jenis_izin, keterangan, file_bukti,
         jenis_izin, keterangan, file_bukti)
    )


def get_semua_pengajuan_izin():
    """Dipakai nanti di halaman direktur/admin untuk approve/tolak izin."""
    query = """
        SELECT id, nama_karyawan, tanggal, status, keterangan, file_bukti, status_approval
        FROM absensi
        WHERE status_approval = 'Pending'
        ORDER BY tanggal DESC
    """
    return Database.fetch_all(query)


def format_tanggal_indonesia(tgl):
    bulan = ["Januari","Februari","Maret","April","Mei","Juni","Juli",
             "Agustus","September","Oktober","November","Desember"]
    if isinstance(tgl, str):
        tgl = datetime.datetime.strptime(tgl, "%Y-%m-%d").date()
    return f"{tgl.day} {bulan[tgl.month - 1]} {tgl.year}"

def get_rekap_bulanan(nama, bulan=None, tahun=None):
    if bulan is None or tahun is None:
        now = datetime.date.today()
        bulan = now.month
        tahun = now.year

    query = """
        SELECT status, COUNT(*) as jumlah
        FROM absensi
        WHERE nama_karyawan = %s AND MONTH(tanggal) = %s AND YEAR(tanggal) = %s
        GROUP BY status
    """
    rows = Database.fetch_all(query, (nama, bulan, tahun))

    rekap = {"Hadir": 0, "Cuti Tahunan": 0, "Sakit": 0, "Izin Penting": 0}
    for row in rows:
        if row['status'] in rekap:
            rekap[row['status']] = row['jumlah']
    return rekap


def hitung_potongan_gaji(nama, gaji_pokok, hari_kerja_per_bulan=25):
    rekap = get_rekap_bulanan(nama)
    jumlah_hari_potong = rekap['Izin Penting']  # hanya Izin Penting yang dipotong
    potongan_per_hari = gaji_pokok / hari_kerja_per_bulan
    total_potongan = round(potongan_per_hari * jumlah_hari_potong)

    return {
        "rekap": rekap,
        "potongan_per_hari": potongan_per_hari,
        "jumlah_hari_potong": jumlah_hari_potong,
        "total_potongan": total_potongan,
    }