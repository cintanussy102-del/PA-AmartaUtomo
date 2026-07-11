from models.database import Database


def ajukan_laporan(nama, nama_proyek, deskripsi, status, progres_manual, file_laporan):
    """Karyawan submit laporan baru. Langsung masuk antrian validasi Direktur."""
    query = """
        INSERT INTO laporan_progres (nama_karyawan, nama_proyek, deskripsi_tugas, status, progres_manual, file_laporan, status_validasi)
        VALUES (%s, %s, %s, %s, %s, %s, 'Menunggu Validasi Direktur')
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


# ============================================================
# UNTUK KARYAWAN — lihat laporan miliknya sendiri
# ============================================================

def get_semua_laporan(nama):
    query = """
        SELECT id, nama_proyek, deskripsi_tugas, status, progres_manual, file_laporan, tanggal_kirim,
               status_validasi, catatan_revisi, tanggal_validasi
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
    selesai = [r for r in semua if r['status_validasi'] == 'Disetujui']
    revisi = [r for r in semua if r['status_validasi'] == 'Revisi']
    return {
        "total": len(semua),
        "semua": semua,
        "selesai": selesai,
        "revisi": revisi,
    }


# ============================================================
# UNTUK ADMIN — terima, simpan, lihat detail, teruskan ke Direktur
# ============================================================

def get_semua_laporan_admin():
    """Semua laporan masuk (semua status), digabung data karyawan. Dipakai Admin buat rekap & kelola."""
    query = """
        SELECT lp.id, lp.nama_karyawan, lp.nama_proyek, lp.deskripsi_tugas, lp.status,
               lp.progres_manual, lp.file_laporan, lp.tanggal_kirim,
               lp.status_validasi, lp.catatan_revisi, lp.tanggal_diteruskan, lp.tanggal_validasi,
               k.nama_lengkap, k.divisi, k.jabatan
        FROM laporan_progres lp
        LEFT JOIN karyawan k ON lp.nama_karyawan = k.username
        ORDER BY lp.tanggal_kirim DESC
    """
    rows = Database.fetch_all(query)
    for row in rows:
        row['progres'] = _hitung_progres(row)
    return rows


def get_laporan_detail(id):
    """Detail 1 laporan spesifik — dipakai Admin & Direktur buat halaman detail."""
    query = """
        SELECT lp.*, k.nama_lengkap, k.divisi, k.jabatan
        FROM laporan_progres lp
        LEFT JOIN karyawan k ON lp.nama_karyawan = k.username
        WHERE lp.id = %s
    """
    rows = Database.fetch_all(query, (id,))
    if not rows:
        return None
    row = rows[0]
    row['progres'] = _hitung_progres(row)
    return row


def teruskan_ke_direktur(id):
    """Admin meneruskan 1 laporan ke Direktur untuk divalidasi."""
    query = """
        UPDATE laporan_progres
        SET status_validasi = 'Menunggu Validasi Direktur', tanggal_diteruskan = NOW()
        WHERE id = %s
    """
    Database.execute_query(query, (id,))


# ============================================================
# UNTUK DIREKTUR — validasi laporan yang sudah diteruskan Admin
# ============================================================

def get_laporan_untuk_direktur():
    """Direktur cuma lihat laporan yang statusnya sudah 'Menunggu Validasi Direktur' atau sudah pernah divalidasi (riwayat)."""
    query = """
        SELECT lp.id, lp.nama_karyawan, lp.nama_proyek, lp.deskripsi_tugas, lp.status,
               lp.progres_manual, lp.file_laporan, lp.tanggal_kirim,
               lp.status_validasi, lp.catatan_revisi, lp.tanggal_diteruskan, lp.tanggal_validasi,
               k.nama_lengkap, k.divisi, k.jabatan
        FROM laporan_progres lp
        LEFT JOIN karyawan k ON lp.nama_karyawan = k.username
        WHERE lp.status_validasi IN ('Menunggu Validasi Direktur', 'Disetujui', 'Revisi')
        ORDER BY
            CASE lp.status_validasi WHEN 'Menunggu Validasi Direktur' THEN 0 ELSE 1 END,
            lp.tanggal_kirim DESC
    """
    rows = Database.fetch_all(query)
    for row in rows:
        row['progres'] = _hitung_progres(row)
    return rows


def validasi_laporan(id, status_validasi, catatan_revisi=None):
    query = """
        UPDATE laporan_progres
        SET status_validasi = %s, catatan_revisi = %s, tanggal_validasi = NOW()
        WHERE id = %s
    """
    Database.execute_query(query, (status_validasi, catatan_revisi, id))

def kirim_ulang_laporan(id, nama_karyawan, deskripsi, status, progres_manual, file_laporan):
    """Karyawan kirim ulang laporan revisi. Langsung balik ke antrian Direktur (bukan Admin lagi)."""
    query = """
        UPDATE laporan_progres
        SET deskripsi_tugas = %s, status = %s, progres_manual = %s, file_laporan = %s,
            status_validasi = 'Menunggu Validasi Direktur', catatan_revisi = NULL,
            tanggal_validasi = NULL, tanggal_kirim = NOW()
        WHERE id = %s AND nama_karyawan = %s
    """
    Database.execute_query(query, (deskripsi, status, progres_manual, file_laporan, id, nama_karyawan))

def get_rata_rata_progres():
    """Rata-rata progres dari semua laporan yang masuk — dipakai buat kartu 'Progres Kerja Kelompok'."""
    semua = get_semua_laporan_admin()
    if not semua:
        return 0
    total = sum(row['progres'] for row in semua)
    return round(total / len(semua))


def get_laporan_progres_terbaru(limit=4):
    """Beberapa laporan progres terbaru untuk ditampilkan di dashboard admin."""
    semua = get_semua_laporan_admin()
    return semua[:limit]

def get_laporan_progres_per_divisi():
    """Kelompokkan semua laporan progres berdasarkan divisi, dipakai di Dashboard Admin."""
    semua = get_semua_laporan_admin()
    hasil = {}
    for row in semua:
        divisi = row['divisi'] if row['divisi'] else 'Tanpa Divisi'
        if divisi not in hasil:
            hasil[divisi] = []
        hasil[divisi].append(row)
    return hasil

def get_progres_per_proyek():
    """Kelompokkan laporan berdasarkan NAMA PROYEK (bukan divisi), ambil progres terbaru tiap proyek."""
    semua = get_semua_laporan_admin()
    proyek = {}
    for row in semua:
        nama = row['nama_proyek']
        if nama not in proyek:
            proyek[nama] = row['progres']
    return proyek

def get_progres_per_proyek():
    """Kelompokkan laporan berdasarkan NAMA PROYEK (bukan divisi), ambil progres terbaru tiap proyek."""
    semua = get_semua_laporan_admin()
    proyek = {}
    for row in semua:
        nama = row['nama_proyek']
        if nama not in proyek:
            proyek[nama] = row['progres']
    return proyek

def get_progres_tugas_karyawan(nama_user, daftar_tugas):
    """Ambil progres TERBARU milik karyawan ini sendiri, untuk tiap tugas tetap di divisinya."""
    semua = get_semua_laporan(nama_user)  # sudah urut DESC by tanggal_kirim
    hasil = []
    for tugas in daftar_tugas:
        laporan_terkait = [l for l in semua if l['nama_proyek'] == tugas]
        progres = laporan_terkait[0]['progres'] if laporan_terkait else 0
        hasil.append({'nama_proyek': tugas, 'progres': progres})
    return hasil