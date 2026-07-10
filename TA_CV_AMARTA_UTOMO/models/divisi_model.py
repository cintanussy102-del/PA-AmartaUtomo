from models.database import Database


def get_semua_divisi_dengan_jumlah():
    """Ambil semua divisi unik dari tabel karyawan + jumlah karyawan aktif per divisi."""
    query = """
        SELECT divisi, COUNT(*) AS jumlah
        FROM karyawan
        WHERE status = 'Aktif'
        GROUP BY divisi
        ORDER BY jumlah DESC
    """
    return Database.fetch_all(query)


def get_jumlah_divisi_aktif():
    """Hitung berapa divisi unik yang punya minimal 1 karyawan aktif."""
    query = """
        SELECT COUNT(DISTINCT divisi) AS total
        FROM karyawan
        WHERE status = 'Aktif'
    """
    rows = Database.fetch_all(query)
    return rows[0]['total'] if rows else 0