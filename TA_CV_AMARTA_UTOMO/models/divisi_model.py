from models.database import Database


def get_semua_divisi():
    """Semua divisi (termasuk yang 0 karyawan) + jumlah karyawan aktif & nama kepala."""
    query = """
        SELECT d.id, d.nama, d.deskripsi, d.status, d.kepala_id,
               k.nama_lengkap AS nama_kepala,
               (SELECT COUNT(*) FROM karyawan WHERE divisi = d.nama AND status = 'Aktif') AS jumlah_karyawan
        FROM divisi d
        LEFT JOIN karyawan k ON d.kepala_id = k.id
        ORDER BY jumlah_karyawan DESC
    """
    return Database.fetch_all(query)


def get_divisi_by_id(id):
    query = "SELECT * FROM divisi WHERE id = %s"
    rows = Database.fetch_all(query, (id,))
    return rows[0] if rows else None


def get_anggota_divisi(nama_divisi):
    query = """
        SELECT id, nama_lengkap, id_karyawan, jabatan, status
        FROM karyawan
        WHERE divisi = %s
        ORDER BY nama_lengkap ASC
    """
    return Database.fetch_all(query, (nama_divisi,))


def tambah_divisi(nama, deskripsi, status='Aktif'):
    query = "INSERT INTO divisi (nama, deskripsi, status) VALUES (%s, %s, %s)"
    Database.execute_query(query, (nama, deskripsi, status))


def update_divisi(id, nama, deskripsi, kepala_id, status):
    """Kalau nama divisi berubah, semua karyawan di divisi lama ikut ganti nama divisinya."""
    divisi_lama = get_divisi_by_id(id)
    if divisi_lama and divisi_lama['nama'] != nama:
        Database.execute_query(
            "UPDATE karyawan SET divisi = %s WHERE divisi = %s",
            (nama, divisi_lama['nama'])
        )

    query = """
        UPDATE divisi SET nama = %s, deskripsi = %s, kepala_id = %s, status = %s
        WHERE id = %s
    """
    Database.execute_query(query, (nama, deskripsi, kepala_id or None, status, id))


def hapus_divisi(id):
    """Hanya bisa dihapus kalau sudah tidak ada karyawan aktif di divisi itu."""
    divisi = get_divisi_by_id(id)
    if not divisi:
        return False, "Divisi tidak ditemukan."

    anggota = get_anggota_divisi(divisi['nama'])
    if anggota:
        return False, f"Divisi '{divisi['nama']}' masih punya {len(anggota)} karyawan. Pindahkan karyawan itu ke divisi lain dulu sebelum menghapus."

    Database.execute_query("DELETE FROM divisi WHERE id = %s", (id,))
    return True, "Divisi berhasil dihapus."


def get_jumlah_divisi_aktif():
    query = "SELECT COUNT(*) AS total FROM divisi WHERE status = 'Aktif'"
    rows = Database.fetch_all(query)
    return rows[0]['total'] if rows else 0


def get_semua_divisi_dengan_jumlah():
    """Dipertahankan untuk kompatibilitas admin_dashboard yang sudah ada."""
    query = """
        SELECT divisi, COUNT(*) AS jumlah
        FROM karyawan
        WHERE status = 'Aktif'
        GROUP BY divisi
        ORDER BY jumlah DESC
    """
    return Database.fetch_all(query)

def get_jabatan_tampilan(karyawan_id, nama_divisi):
    """Tentukan label jabatan untuk slip gaji: Kepala Divisi / Anggota Divisi / Direktur."""
    if nama_divisi == 'Direktur':
        return 'Direktur'

    query = "SELECT kepala_id FROM divisi WHERE nama = %s"
    rows = Database.fetch_all(query, (nama_divisi,))
    if rows and rows[0]['kepala_id'] is not None and rows[0]['kepala_id'] == karyawan_id:
        return 'Kepala Divisi'
    return 'Anggota Divisi'