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
    """Dipakai di Dashboard Karyawan untuk ringkasan cepat (statistik dummy, bukan master data)."""
    data_karyawan = {
        "Rony": {"hari_hadir": 29, "izin": 1, "gaji": 4500000, "progres": 90},
        "Aloy": {"hari_hadir": 20, "izin": 2, "gaji": 4200000, "progres": 60},
        "Putri": {"hari_hadir": 10, "izin": 3, "gaji": 4000000, "progres": 30}
    }
    return data_karyawan.get(nama, {"hari_hadir": 0, "izin": 0, "gaji": 0, "progres": 0})