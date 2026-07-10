from models.database import Database

def get_semua_karyawan():
    query = "SELECT * FROM karyawan ORDER BY id ASC"
    return Database.fetch_all(query)

def get_karyawan_by_id(id):
    query = "SELECT * FROM karyawan WHERE id = %s"
    rows = Database.fetch_all(query, (id,))
    return rows[0] if rows else None

def get_karyawan_by_username(username):
    query = "SELECT * FROM karyawan WHERE username = %s"
    rows = Database.fetch_all(query, (username,))
    return rows[0] if rows else None

def tambah_karyawan(username, nama_lengkap, id_karyawan, divisi, jabatan, gaji_pokok, tunjangan, kontak, tanggal_bergabung, status='Aktif', email=None):
    query = """
        INSERT INTO karyawan (username, nama_lengkap, id_karyawan, divisi, jabatan, gaji_pokok, tunjangan, kontak, tanggal_bergabung, status, email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    Database.execute_query(query, (username, nama_lengkap, id_karyawan, divisi, jabatan, gaji_pokok, tunjangan, kontak, tanggal_bergabung, status, email))

def update_karyawan(id, username, nama_lengkap, id_karyawan, divisi, jabatan, gaji_pokok, tunjangan, kontak, tanggal_bergabung, status, email=None):
    query = """
        UPDATE karyawan SET
            username = %s, nama_lengkap = %s, id_karyawan = %s, divisi = %s, jabatan = %s,
            gaji_pokok = %s, tunjangan = %s, kontak = %s, tanggal_bergabung = %s, status = %s, email = %s
        WHERE id = %s
    """
    Database.execute_query(query, (username, nama_lengkap, id_karyawan, divisi, jabatan, gaji_pokok, tunjangan, kontak, tanggal_bergabung, status, email, id))

def hapus_karyawan(id):
    query = "DELETE FROM karyawan WHERE id = %s"
    Database.execute_query(query, (id,))

def update_status_gaji(id, status_baru):
    query = "UPDATE karyawan SET status_gaji = %s WHERE id = %s"
    Database.execute_query(query, (status_baru, id))

def get_profil_gaji(nama):
    """Dipakai di Slip Gaji & Input Laporan Kerja karyawan."""
    row = get_karyawan_by_username(nama)
    if row:
        return {
            "nama_lengkap": row['nama_lengkap'],
            "id_karyawan": row['id_karyawan'],
            "jabatan": row['jabatan'],
            "divisi": row['divisi'],
            "gaji_pokok": float(row['gaji_pokok']),
            "tunjangan": float(row['tunjangan']),
        }
    return {
        "nama_lengkap": nama,
        "id_karyawan": "-",
        "jabatan": "-",
        "divisi": "-",
        "gaji_pokok": 0,
        "tunjangan": 0,
    }

def get_data_karyawan_by_name(nama):
    """Dipakai di Dashboard Karyawan — ambil data real dari database."""
    row = get_karyawan_by_username(nama)
    if row:
        return {
            "hari_hadir": 0,
            "izin": 0,
            "gaji": float(row['gaji_pokok']),
            "progres": 0
        }
    return {"hari_hadir": 0, "izin": 0, "gaji": 0, "progres": 0}

def get_karyawan_by_divisi_dan_username(divisi, username):
    """Dipakai untuk login karyawan: username = divisi, password = nama depan."""
    query = "SELECT * FROM karyawan WHERE divisi = %s AND username = %s"
    rows = Database.fetch_all(query, (divisi, username))
    return rows[0] if rows else None

def get_total_karyawan_aktif():
    query = "SELECT COUNT(*) AS total FROM karyawan WHERE status = 'Aktif'"
    rows = Database.fetch_all(query)
    return rows[0]['total'] if rows else 0


def get_karyawan_terbaru(limit=3):
    query = "SELECT * FROM karyawan ORDER BY tanggal_bergabung DESC, id DESC LIMIT %s"
    return Database.fetch_all(query, (limit,))