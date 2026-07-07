import datetime
import calendar

from arrow import now
from models.database import Database
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

def waktu_sekarang():
    return datetime.datetime.now(WIB)

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
    hari_ini = waktu_sekarang().date()
    rows = Database.fetch_all(query, (nama, hari_ini))
    if rows:
        row = rows[0]
        row['masuk'] = row['masuk'] or '-'
        row['keluar'] = row['keluar'] or '-'
        return row
    return None


def catat_absen_masuk(nama, lat=None, lon=None, alamat=None):
    hari_ini = waktu_sekarang().date()
    jam = waktu_sekarang().strftime("%H:%M")

    existing = get_status_hari_ini(nama)
    if existing:
        query = """
            UPDATE absensi SET jam_masuk = %s, status = 'Hadir', latitude = %s, longitude = %s, alamat_absen = %s
            WHERE nama_karyawan = %s AND tanggal = %s
        """
        Database.execute_query(query, (jam, lat, lon, alamat, nama, hari_ini))
    else:
        query = """
            INSERT INTO absensi (nama_karyawan, tanggal, jam_masuk, status, status_approval, latitude, longitude, alamat_absen)
            VALUES (%s, %s, %s, 'Hadir', 'Approved', %s, %s, %s)
        """
        Database.execute_query(query, (nama, hari_ini, jam, lat, lon, alamat))

    hasil = get_status_hari_ini(nama)
    return {
        "tanggal": format_tanggal_indonesia(hari_ini),
        "jam_masuk": jam,
        "status": hasil['status'] if hasil else 'Hadir',
    }


def catat_absen_keluar(nama):
    hari_ini = waktu_sekarang().date()
    jam = waktu_sekarang().strftime("%H:%M")

    existing = get_status_hari_ini(nama)
    if existing:
        query = "UPDATE absensi SET jam_keluar = %s WHERE nama_karyawan = %s AND tanggal = %s"
        Database.execute_query(query, (jam, nama, hari_ini))
    else:
        query = """
            INSERT INTO absensi (nama_karyawan, tanggal, jam_keluar, status, status_approval)
            VALUES (%s, %s, %s, 'Hadir', 'Approved')
        """
        Database.execute_query(query, (nama, hari_ini, jam))

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

    rekap = {"Hadir": 0, "Cuti": 0, "Sakit": 0, "Izin Lainnya": 0}
    for row in rows:
        if row['status'] in rekap:
            rekap[row['status']] = row['jumlah']

    rekap["Alpha"] = hitung_hari_alpha(nama, bulan, tahun)
    return rekap


def hitung_hari_alpha(nama, bulan=None, tahun=None):
    """
    Menghitung hari kerja (Senin-Sabtu) yang SAMA SEKALI tidak ada
    record-nya di database (tidak absen & tidak mengajukan izin/cuti/sakit).
    Hanya menghitung sampai hari ini (hari di masa depan tidak dihitung).
    """
    if bulan is None or tahun is None:
        today = waktu_sekarang().date()
        bulan = now.month
        tahun = now.year

    query = """
        SELECT tanggal FROM absensi
        WHERE nama_karyawan = %s AND MONTH(tanggal) = %s AND YEAR(tanggal) = %s
    """
    rows = Database.fetch_all(query, (nama, bulan, tahun))
    tanggal_tercatat = set()
    for row in rows:
        t = row['tanggal']
        if isinstance(t, str):
            t = datetime.datetime.strptime(t, "%Y-%m-%d").date()
        tanggal_tercatat.add(t)

    today = datetime.date.today()
    if tahun == today.year and bulan == today.month:
        hari_terakhir = today.day
    else:
        hari_terakhir = calendar.monthrange(tahun, bulan)[1]

    jumlah_alpha = 0
    for hari in range(1, hari_terakhir + 1):
        tgl = datetime.date(tahun, bulan, hari)
        if tgl.weekday() == 6:  # Minggu = libur, skip
            continue
        if tgl > today:  # hari di masa depan, skip
            continue
        if tgl not in tanggal_tercatat:
            jumlah_alpha += 1

    return jumlah_alpha


def hitung_potongan_gaji(nama, gaji_pokok, hari_kerja_per_bulan=25):
    rekap = get_rekap_bulanan(nama)
    jumlah_hari_potong = rekap['Alpha']  # hanya hari Alpha (tanpa keterangan) yang dipotong
    potongan_per_hari = gaji_pokok / hari_kerja_per_bulan
    total_potongan = round(potongan_per_hari * jumlah_hari_potong)

    return {
        "rekap": rekap,
        "potongan_per_hari": potongan_per_hari,
        "jumlah_hari_potong": jumlah_hari_potong,
        "total_potongan": total_potongan,
    }

DAFTAR_KARYAWAN = ["Rony", "Aloy", "Putri"]


def get_rekap_absensi_hari_ini():
    hari_ini = waktu_sekarang().date()
    hadir = 0
    izin_cuti = 0
    sakit = 0
    alpha = 0

    for nama in DAFTAR_KARYAWAN:
        query = "SELECT status FROM absensi WHERE nama_karyawan = %s AND tanggal = %s"
        rows = Database.fetch_all(query, (nama, hari_ini))

        if not rows:
            alpha += 1
        else:
            status = rows[0]['status']
            if status == 'Hadir':
                hadir += 1
            elif status == 'Sakit':
                sakit += 1
            elif status in ('Cuti', 'Izin Lainnya'):
                izin_cuti += 1
            else:
                alpha += 1

    return {
        "hadir": hadir,
        "izin_cuti": izin_cuti,
        "sakit": sakit,
        "alpha": alpha,
        "total_karyawan": len(DAFTAR_KARYAWAN),
    }

def format_tanggal_indonesia(tgl):
    bulan = ["Januari","Februari","Maret","April","Mei","Juni","Juli",
             "Agustus","September","Oktober","November","Desember"]
    if isinstance(tgl, str):
        tgl = datetime.datetime.strptime(tgl, "%Y-%m-%d").date()
    return f"{tgl.day} {bulan[tgl.month - 1]} {tgl.year}"

def hitung_durasi_kerja(masuk, keluar):
    if not masuk or not keluar or masuk == '-' or keluar == '-':
        return '-'
    try:
        fmt = "%H:%M"
        t_masuk = datetime.datetime.strptime(masuk, fmt)
        t_keluar = datetime.datetime.strptime(keluar, fmt)
        selisih = t_keluar - t_masuk
        total_menit = int(selisih.total_seconds() // 60)
        if total_menit < 0:
            return '-'
        jam = total_menit // 60
        menit = total_menit % 60
        return f"{jam} jam {menit} menit"
    except Exception:
        return '-'
    
def get_absensi_hari_ini_semua():
    """Untuk halaman Direktur - Absensi. Menggabungkan admin + semua karyawan."""
    from models.karyawan_model import get_semua_karyawan

    daftar = [{"username": "admin", "nama_lengkap": "Admin", "divisi": "Manajemen"}]
    for k in get_semua_karyawan():
        daftar.append({"username": k['username'], "nama_lengkap": k['nama_lengkap'], "divisi": k['divisi']})

    hari_ini = waktu_sekarang().date()
    hasil = []
    for orang in daftar:
        query = "SELECT * FROM absensi WHERE nama_karyawan = %s AND tanggal = %s"
        rows = Database.fetch_all(query, (orang['username'], hari_ini))
        if rows:
            row = rows[0]
            hasil.append({
                "nama_lengkap": orang['nama_lengkap'],
                "divisi": orang['divisi'],
                "username": orang['username'],
                "tanggal": format_tanggal_indonesia(hari_ini),
                "masuk": row['jam_masuk'] or '-',
                "keluar": row['jam_keluar'] or '-',
                "status": row['status'],
                "keterangan": row['keterangan'] or '-',
            })
        else:
            hasil.append({
                "nama_lengkap": orang['nama_lengkap'],
                "divisi": orang['divisi'],
                "username": orang['username'],
                "tanggal": format_tanggal_indonesia(hari_ini),
                "masuk": '-',
                "keluar": '-',
                "status": 'Alpha',
                "keterangan": 'Tanpa keterangan',
            })
    return hasil


def reset_absensi_hari_ini(nama=None):
    """Hapus data absensi hari ini. Kalau nama=None, hapus untuk SEMUA orang (dipakai sebelum demo/presentasi)."""
    hari_ini = waktu_sekarang().date()
    if nama:
        query = "DELETE FROM absensi WHERE nama_karyawan = %s AND tanggal = %s"
        Database.execute_query(query, (nama, hari_ini))
    else:
        query = "DELETE FROM absensi WHERE tanggal = %s"
        Database.execute_query(query, (hari_ini,))