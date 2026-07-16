import os
from functools import wraps
from flask import session, redirect, url_for


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role and session['user'].get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allowed_file(filename):
    ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def get_jabatan_tampilan(karyawan_id, nama_divisi):
    """Keputusan bisnis: tentukan label jabatan (Kepala Divisi/Anggota Divisi/Direktur).
    Ini logic keputusan, bukan query mentah -> makanya di utils/controller, bukan model."""
    if nama_divisi == 'Direktur':
        return 'Direktur'
    from models.divisi_model import get_kepala_id_by_divisi
    kepala_id = get_kepala_id_by_divisi(nama_divisi)
    if kepala_id is not None and kepala_id == karyawan_id:
        return 'Kepala Divisi'
    return 'Anggota Divisi'


TUGAS_PER_DIVISI = {
    'Arsitektur': [
        'Desain Gambar Kerja Proyek',
        'Review & Revisi Desain',
        'Survey Lokasi Proyek Baru',
    ],
    'Marketing': [
        'Promosi Unit Perumahan',
        'Promosi & Sewa Kos-kosan',
        'Follow Up Klien/Penyewa',
    ],
    'Logistik': [
        'Pengadaan Material Proyek',
        'Distribusi Material ke Lokasi',
        'Maintenance Fasilitas Kos-kosan',
    ],
    'Pengawas Lapangan': [
        'Monitoring Progres Proyek Konstruksi',
        'Pengecekan Kualitas Material/Pekerjaan',
        'Inspeksi Kondisi Kos-kosan',
    ],
}


def build_laporan_progres_dashboard():
    """Gabungkan daftar tugas tetap per divisi dengan progres laporan asli yang sudah masuk."""
    from models.progres_model import get_semua_laporan_admin
    semua_laporan = get_semua_laporan_admin()
    hasil = {}
    for divisi, daftar_tugas in TUGAS_PER_DIVISI.items():
        hasil[divisi] = []
        for tugas in daftar_tugas:
            laporan_terkait = [
                l for l in semua_laporan
                if l['divisi'] == divisi and l['nama_proyek'] == tugas
            ]
            progres = laporan_terkait[0]['progres'] if laporan_terkait else 0
            hasil[divisi].append({'nama_proyek': tugas, 'progres': progres})
    return hasil