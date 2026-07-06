from models.database import Database


def ajukan_laporan(nama, nama_proyek, deskripsi, status, progres_manual, file_laporan):
    query = """
        INSERT INTO laporan_progres (nama_karyawan, nama_proyek, deskripsi_tugas, status, progres_manual, file_laporan)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    Database.execute_query(query, (nama, nama_proyek, deskripsi, status, progres_manual, file_laporan))


def _hitung_progres(row):
    if row['status'] == 'Selesai':
        return 100
    elif row['status'] == 'Butuh Revisi':
        return 50
    elif row['status'] == 'Sedang Dikerjakan':
        return row['progres_manual'] if row['progres_manual'] is not None else 0
    return 0


def get_semua_laporan(nama):
    query = """
        SELECT id, nama_proyek, deskripsi_tugas, status, progres_manual, file_laporan, tanggal_kirim
        FROM laporan_progres
        WHERE nama_karyawan = %s
        ORDER BY tanggal_kirim DESC
    """
    rows = Database.fetch_all(query, (nama,))
    for row in rows:
        row['progres'] = _hitung_progres(row)
    return rows


def get_ringkasan_laporan(nama):
    semua = get_semua_laporan(nama)
    selesai = [r for r in semua if r['status'] == 'Selesai']
    revisi = [r for r in semua if r['status'] == 'Butuh Revisi']
    return {
        "total": len(semua),
        "semua": semua,
        "selesai": selesai,
        "revisi": revisi,
    }