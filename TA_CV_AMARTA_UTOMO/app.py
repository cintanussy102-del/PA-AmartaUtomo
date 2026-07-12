import os
from dotenv import load_dotenv
load_dotenv()                       

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from controllers.direktur_controller import direktur_bp
from models.gaji_model import get_slip_gaji, get_semua_bulan_tersedia, NAMA_BULAN
from models.divisi_model import get_jabatan_tampilan

from models.karyawan_model import (
    get_data_karyawan_by_name, get_profil_gaji,
    get_semua_karyawan, get_karyawan_by_id,
    tambah_karyawan, update_karyawan, hapus_karyawan,
    get_karyawan_by_username, get_karyawan_by_divisi_dan_username,
    get_total_karyawan_aktif, get_karyawan_terbaru,
    get_karyawan_per_divisi  
)
from models.absensi_model import (
    get_absensi_hari_ini_semua, get_riwayat_absensi, get_status_hari_ini,
    catat_absen_masuk, catat_absen_keluar, ajukan_izin,
    hitung_potongan_gaji, get_rekap_absensi_hari_ini,
    hitung_durasi_kerja, get_rekap_bulanan,
    get_absensi_tanggal, get_daftar_tanggal_bulan, reset_absensi_hari_ini,
    get_tingkat_kehadiran_hari_ini, get_semua_pengajuan_izin,
    get_riwayat_absensi_bulan   
)
from models.progres_model import (
       ajukan_laporan, get_ringkasan_laporan, kirim_ulang_laporan,
       get_semua_laporan_admin, get_laporan_detail, teruskan_ke_direktur,
       get_laporan_untuk_direktur, validasi_laporan,
       get_rata_rata_progres, get_laporan_progres_terbaru,
       get_laporan_progres_per_divisi,
       get_progres_per_proyek,
       get_progres_tugas_karyawan   
)
from models.divisi_model import (
    get_semua_divisi_dengan_jumlah, get_jumlah_divisi_aktif,
    get_semua_divisi, get_anggota_divisi, tambah_divisi, update_divisi, hapus_divisi
)

from datetime import datetime
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta


load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join('views', 'templates'),
    static_folder=os.path.join('views', 'static')
)

@app.template_filter('rupiah')
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

app.register_blueprint(direktur_bp)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key_amarta')

UPLOAD_FOLDER = os.path.join('views', 'static', 'uploads', 'bukti_izin')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

UPLOAD_FOLDER_LAPORAN = os.path.join('views', 'static', 'uploads', 'laporan_kerja')
os.makedirs(UPLOAD_FOLDER_LAPORAN, exist_ok=True)
app.config['UPLOAD_FOLDER_LAPORAN'] = UPLOAD_FOLDER_LAPORAN

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
server_port = int(os.getenv('FLASK_PORT', 5000))

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

@app.route('/')
def welcome():
    return render_template('welcome.html')

DIVISI_LOGIN_MAP = {
    'Arsitektur': 'Arsitektur',
    'Marketing': 'Marketing',
    'Logistik': 'Logistik',
    'Pengawas': 'Pengawas Lapangan',
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Login Admin
        if username == 'Admin':
            if password == 'Glory':
                session['user'] = {'username': 'admin', 'role': 'admin'}
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Password salah', 'danger')
                return redirect(url_for('login'))

        # Login Direktur
        elif username == 'Direktur':
            if password == 'Gloria':
                session['user'] = {'username': 'direktur', 'role': 'direktur'}
                return redirect(url_for('direktur_dashboard'))
            else:
                flash('Password salah', 'danger')
                return redirect(url_for('login'))

        # Login Karyawan
        elif username in DIVISI_LOGIN_MAP:
            divisi_asli = DIVISI_LOGIN_MAP[username]
            karyawan = get_karyawan_by_divisi_dan_username(divisi_asli, password)

            if karyawan:
                session['user'] = {
                    'username': karyawan['username'],
                    'nama_lengkap': karyawan['nama_lengkap'],
                    'role': 'karyawan'
                }
                return redirect(url_for('karyawan_dashboard'))
            else:
                flash('Password salah', 'danger')
                return redirect(url_for('login'))

        else:
            flash('Username salah', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================================
# RUTE ADMIN
# ============================================================

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    total_karyawan = get_total_karyawan_aktif()
    divisi_list = get_semua_divisi_dengan_jumlah()
    jumlah_divisi_aktif = get_jumlah_divisi_aktif()
    laporan_per_divisi = build_laporan_progres_dashboard()
    karyawan_terbaru = get_karyawan_terbaru(3)

    semua_laporan = get_semua_laporan_admin()
    laporan_disetujui = len([l for l in semua_laporan if l['status_validasi'] == 'Disetujui'])
    laporan_menunggu = len([l for l in semua_laporan if l['status_validasi'] == 'Menunggu Validasi Direktur'])

    bulan_ini = datetime.now().month
    tahun_ini = datetime.now().year
    karyawan_baru_bulan_ini = len([
        k for k in get_semua_karyawan()
        if k.get('tanggal_bergabung') and k['tanggal_bergabung'].month == bulan_ini and k['tanggal_bergabung'].year == tahun_ini
    ])

    return render_template(
        'admin/dashboard.html',
        total_karyawan=total_karyawan,
        divisi_list=divisi_list,
        jumlah_divisi_aktif=jumlah_divisi_aktif,
        laporan_per_divisi=laporan_per_divisi,
        karyawan_terbaru=karyawan_terbaru,
        laporan_disetujui=laporan_disetujui,
        laporan_menunggu=laporan_menunggu,
        karyawan_baru_bulan_ini=karyawan_baru_bulan_ini,
    )

@app.route('/admin/data-karyawan')
@login_required(role='admin')
def admin_data_karyawan():
    daftar_karyawan = get_semua_karyawan()
    total = len(daftar_karyawan)
    aktif = len([k for k in daftar_karyawan if k['status'] == 'Aktif'])
    izin_cuti = len([k for k in daftar_karyawan if k['status'] != 'Aktif'])
    return render_template('admin/data_karyawan.html', daftar_karyawan=daftar_karyawan, total=total, aktif=aktif, izin_cuti=izin_cuti)

@app.route('/admin/data-karyawan/tambah', methods=['POST'])
@login_required(role='admin')
def admin_tambah_karyawan():
    tambah_karyawan(
        username=request.form.get('username'),
        nama_lengkap=request.form.get('nama_lengkap'),
        id_karyawan=request.form.get('id_karyawan'),
        divisi=request.form.get('divisi'),
        jabatan=request.form.get('jabatan'),
        gaji_pokok=request.form.get('gaji_pokok'),
        tunjangan=request.form.get('tunjangan'),
        kontak=request.form.get('kontak'),
        tanggal_bergabung=request.form.get('tanggal_bergabung'),
        status=request.form.get('status', 'Aktif'),
        email=request.form.get('email')
    )
    flash('Karyawan baru berhasil ditambahkan!', 'success')
    return redirect(url_for('admin_data_karyawan'))

@app.route('/admin/data-karyawan/edit/<int:id>', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_edit_karyawan(id):
    if request.method == 'POST':
        update_karyawan(
            id=id,
            username=request.form.get('username'),
            nama_lengkap=request.form.get('nama_lengkap'),
            id_karyawan=request.form.get('id_karyawan'),
            divisi=request.form.get('divisi'),
            jabatan=request.form.get('jabatan'),
            gaji_pokok=request.form.get('gaji_pokok'),
            tunjangan=request.form.get('tunjangan'),
            kontak=request.form.get('kontak'),
            tanggal_bergabung=request.form.get('tanggal_bergabung'),
            status=request.form.get('status'),
            email=request.form.get('email')
        )
        flash('Data karyawan berhasil diperbarui!', 'success')
        return redirect(url_for('admin_data_karyawan'))

    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data karyawan tidak ditemukan!', 'danger')
        return redirect(url_for('admin_data_karyawan'))
    return render_template('admin/edit_karyawan.html', karyawan=karyawan)

@app.route('/admin/data-karyawan/hapus/<int:id>', methods=['POST'])
@login_required(role='admin')
def admin_hapus_karyawan(id):
    hapus_karyawan(id)
    flash('Data karyawan berhasil dihapus!', 'success')
    return redirect(url_for('admin_data_karyawan'))

@app.route('/admin/absensi')
@login_required(role='admin')
def admin_absensi():
    nama_user = session['user']['username']

    today = datetime.now()
    bulan_pilih = int(request.args.get('bulan', today.month))
    tahun_pilih = int(request.args.get('tahun', today.year))

    riwayat = get_riwayat_absensi_bulan(nama_user, bulan_pilih, tahun_pilih)
    status_hari_ini = get_status_hari_ini(nama_user)
    durasi_kerja = hitung_durasi_kerja(
        status_hari_ini['masuk'] if status_hari_ini else None,
        status_hari_ini['keluar'] if status_hari_ini else None
    )
    rekap = get_rekap_bulanan(nama_user, bulan_pilih, tahun_pilih)

    return render_template(
        'admin/kelola_absensi.html',
        riwayat=riwayat,
        status_hari_ini=status_hari_ini,
        durasi_kerja=durasi_kerja,
        rekap=rekap,
        bulan_pilih=bulan_pilih,
        tahun_pilih=tahun_pilih,
        nama_bulan=NAMA_BULAN
    )

@app.route('/admin/ajukan-izin', methods=['POST'])
@login_required(role='admin')
def admin_ajukan_izin():
    nama_user = session['user']['username']
    jenis_izin = request.form.get('jenis_izin')
    tanggal = request.form.get('pilih_tanggal')
    keterangan = request.form.get('keterangan')

    wajib_upload = jenis_izin in ['Sakit', 'Izin Lainnya', 'Cuti']
    file_bukti_path = None

    if wajib_upload:
        file_bukti = request.files.get('file_bukti')
        if not file_bukti or file_bukti.filename == '':
            flash('Untuk jenis izin ini, bukti (foto/dokumen) wajib diunggah!', 'danger')
            return redirect(url_for('admin_absensi'))
        if not allowed_file(file_bukti.filename):
            flash('Format file tidak didukung. Gunakan JPG, PNG, atau PDF.', 'danger')
            return redirect(url_for('admin_absensi'))

        filename = secure_filename(f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_bukti.filename}")
        file_bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_bukti_path = f"uploads/bukti_izin/{filename}"

    ajukan_izin(nama_user, jenis_izin, tanggal, keterangan, file_bukti_path)
    flash('Pengajuan izin/cuti berhasil dikirim!', 'success')
    return redirect(url_for('admin_absensi'))
    
@app.route('/admin/divisi')
@login_required(role='admin')
def admin_divisi():
    divisi_list = get_semua_divisi()
    for d in divisi_list:
        d['anggota'] = get_anggota_divisi(d['nama'])
    total_karyawan = sum(d['jumlah_karyawan'] for d in divisi_list)
    semua_karyawan = get_semua_karyawan()
    return render_template(
        'admin/divisi.html',
        divisi_list=divisi_list,
        total_karyawan=total_karyawan,
        semua_karyawan=semua_karyawan
    )


@app.route('/admin/divisi/tambah', methods=['POST'])
@login_required(role='admin')
def admin_tambah_divisi():
    nama = request.form.get('nama')
    deskripsi = request.form.get('deskripsi')
    tambah_divisi(nama, deskripsi)
    flash('Divisi baru berhasil ditambahkan!', 'success')
    return redirect(url_for('admin_divisi'))


@app.route('/admin/divisi/edit/<int:id>', methods=['POST'])
@login_required(role='admin')
def admin_edit_divisi(id):
    nama = request.form.get('nama')
    deskripsi = request.form.get('deskripsi')
    kepala_id = request.form.get('kepala_id') or None
    status = request.form.get('status', 'Aktif')
    update_divisi(id, nama, deskripsi, kepala_id, status)
    flash('Data divisi berhasil diperbarui!', 'success')
    return redirect(url_for('admin_divisi'))


@app.route('/admin/divisi/hapus/<int:id>', methods=['POST'])
@login_required(role='admin')
def admin_hapus_divisi(id):
    berhasil, pesan = hapus_divisi(id)
    flash(pesan, 'success' if berhasil else 'danger')
    return redirect(url_for('admin_divisi'))

@app.route('/admin/rekap-laporan')
@login_required(role='admin')
def admin_rekap_laporan():
    semua = get_semua_laporan_admin()
    disetujui = [l for l in semua if l['status_validasi'] == 'Disetujui']

    bulan_pilih = request.args.get('bulan', type=int)
    tahun_pilih = request.args.get('tahun', type=int)

    if bulan_pilih and tahun_pilih:
        disetujui = [
            l for l in disetujui
            if l['tanggal_validasi'] and l['tanggal_validasi'].month == bulan_pilih and l['tanggal_validasi'].year == tahun_pilih
        ]

    per_divisi = {}
    for l in disetujui:
        divisi = l['divisi'] or 'Tanpa Divisi'
        per_divisi.setdefault(divisi, []).append(l)

    total_laporan = len(disetujui)
    total_divisi = len(per_divisi)

    tahun_tersedia = sorted({l['tanggal_validasi'].year for l in semua if l['status_validasi'] == 'Disetujui' and l['tanggal_validasi']}, reverse=True)
    if not tahun_tersedia:
        tahun_tersedia = [datetime.now().year]

    return render_template(
        'admin/rekap_laporan.html',
        per_divisi=per_divisi,
        total_laporan=total_laporan,
        total_divisi=total_divisi,
        bulan_pilih=bulan_pilih,
        tahun_pilih=tahun_pilih,
        tahun_tersedia=tahun_tersedia,
        nama_bulan=NAMA_BULAN,
    )

@app.route('/admin/teruskan-laporan/<int:id>', methods=['POST'])
@login_required(role='admin')
def admin_teruskan_laporan(id):
    teruskan_ke_direktur(id)
    flash('Laporan berhasil diteruskan ke Direktur untuk divalidasi.', 'success')
    return redirect(url_for('admin_rekap_laporan'))

@app.route('/admin/slip-gaji')
@login_required(role='admin')
def admin_slip_gaji():
    admin_data = get_karyawan_by_username('admin')
    if not admin_data:
        flash('Data admin tidak ditemukan di database!', 'danger')
        return redirect(url_for('admin_dashboard'))

    admin_data['jabatan'] = get_jabatan_tampilan(admin_data['id'], admin_data['divisi'])

    today = datetime.now()
    bulan_dipilih = int(request.args.get('bulan', today.month))
    tahun_dipilih = int(request.args.get('tahun', today.year))

    slip = get_slip_gaji(admin_data['id'], bulan_dipilih, tahun_dipilih)
    daftar_bulan = get_semua_bulan_tersedia(admin_data['id'])

    return render_template(
        'admin/slip_gaji.html',
        profil=admin_data,
        slip=slip,
        bulan_dipilih=bulan_dipilih,
        tahun_dipilih=tahun_dipilih,
        daftar_bulan=daftar_bulan,
        nama_bulan=NAMA_BULAN
    )

# ============================================================
# RUTE KARYAWAN
# ============================================================

@app.route('/karyawan/dashboard')
@login_required(role='karyawan')
def karyawan_dashboard():
    nama_user = session['user']['username']
    karyawan = get_karyawan_by_username(nama_user)
    riwayat = get_riwayat_absensi(nama_user, limit=3)
    rekap = get_rekap_bulanan(nama_user)

    daftar_tugas = TUGAS_PER_DIVISI.get(karyawan['divisi'], []) if karyawan else []
    progres_tugas = get_progres_tugas_karyawan(nama_user, daftar_tugas)

    progres_rata = round(sum(t['progres'] for t in progres_tugas) / len(progres_tugas)) if progres_tugas else 0

    data = {
        "hari_hadir": rekap.get('Hadir', 0),
        "izin": rekap.get('Cuti', 0) + rekap.get('Izin Lainnya', 0) + rekap.get('Sakit', 0),
        "gaji": float(karyawan['gaji_pokok']) if karyawan else 0,
        "progres": progres_rata,
    }

    return render_template(
        'karyawan/dashboard.html',
        data=data,
        riwayat=riwayat,
        progres_tugas=progres_tugas
    )

@app.route('/karyawan/absensi')
@login_required(role='karyawan')
def karyawan_absensi():
    nama_user = session['user']['username']

    today = datetime.now()
    bulan_pilih = int(request.args.get('bulan', today.month))
    tahun_pilih = int(request.args.get('tahun', today.year))

    riwayat = get_riwayat_absensi_bulan(nama_user, bulan_pilih, tahun_pilih)
    status_hari_ini = get_status_hari_ini(nama_user)
    durasi_kerja = hitung_durasi_kerja(
        status_hari_ini['masuk'] if status_hari_ini else None,
        status_hari_ini['keluar'] if status_hari_ini else None
    )
    rekap = get_rekap_bulanan(nama_user, bulan_pilih, tahun_pilih)

    return render_template(
        'karyawan/absensi.html',
        riwayat=riwayat,
        status_hari_ini=status_hari_ini,
        durasi_kerja=durasi_kerja,
        rekap=rekap,
        bulan_pilih=bulan_pilih,
        tahun_pilih=tahun_pilih,
        nama_bulan=NAMA_BULAN
    )

@app.route('/karyawan/absen-masuk', methods=['POST'])
@login_required(role='karyawan')
def karyawan_absen_masuk():
    catat_absen_masuk(session['user']['username'])
    flash('Absen masuk berhasil dicatat!', 'success')
    return redirect(url_for('karyawan_absensi'))

@app.route('/karyawan/absen-keluar', methods=['POST'])
@login_required(role='karyawan')
def karyawan_absen_keluar():
    catat_absen_keluar(session['user']['username'])
    flash('Absen keluar berhasil dicatat!', 'success')
    return redirect(url_for('karyawan_absensi'))

@app.route('/karyawan/ajukan-izin', methods=['POST'])
@login_required(role='karyawan')
def karyawan_ajukan_izin():
    nama_user = session['user']['username']
    jenis_izin = request.form.get('jenis_izin')
    tanggal = request.form.get('pilih_tanggal')
    keterangan = request.form.get('keterangan')

    wajib_upload = jenis_izin in ['Sakit', 'Izin Lainnya', 'Cuti']
    file_bukti_path = None

    if wajib_upload:
        file_bukti = request.files.get('file_bukti')
        if not file_bukti or file_bukti.filename == '':
            flash('Untuk jenis izin ini, bukti (foto/dokumen) wajib diunggah!', 'danger')
            return redirect(url_for('karyawan_absensi'))
        if not allowed_file(file_bukti.filename):
            flash('Format file tidak didukung. Gunakan JPG, PNG, atau PDF.', 'danger')
            return redirect(url_for('karyawan_absensi'))

        filename = secure_filename(f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_bukti.filename}")
        file_bukti.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_bukti_path = f"uploads/bukti_izin/{filename}"

    ajukan_izin(nama_user, jenis_izin, tanggal, keterangan, file_bukti_path)
    flash('Pengajuan izin/cuti berhasil dikirim!', 'success')
    return redirect(url_for('karyawan_absensi'))

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
    semua_laporan = get_semua_laporan_admin()
    hasil = {}
    for divisi, daftar_tugas in TUGAS_PER_DIVISI.items():
        hasil[divisi] = []
        for tugas in daftar_tugas:
            laporan_terkait = [
                l for l in semua_laporan
                if l['divisi'] == divisi and l['nama_proyek'] == tugas
            ]
            if laporan_terkait:
                progres = laporan_terkait[0]['progres']
            else:
                progres = 0
            hasil[divisi].append({
                'nama_proyek': tugas,
                'progres': progres
            })
    return hasil

@app.route('/karyawan/input-progres')
@login_required(role='karyawan')
def karyawan_input_progres():
    nama_user = session['user']['username']
    profil = get_profil_gaji(nama_user)
    ringkasan = get_ringkasan_laporan(nama_user)
    daftar_tugas = TUGAS_PER_DIVISI.get(profil['divisi'], [])
    return render_template('karyawan/input_progres.html', profil=profil, ringkasan=ringkasan, daftar_tugas=daftar_tugas)

@app.route('/karyawan/kirim-laporan', methods=['POST'])
@login_required(role='karyawan')
def karyawan_kirim_laporan():
    nama_user = session['user']['username']
    nama_proyek = request.form.get('id_pekerjaan')
    deskripsi = request.form.get('tugas_pekerjaan')
    status = request.form.get('status_tugas')
    progres_manual = request.form.get('progres_manual')
    progres_manual = int(progres_manual) if progres_manual else None

    file_laporan = request.files.get('file_laporan')
    if not file_laporan or file_laporan.filename == '':
        flash('File laporan (PDF) wajib diunggah!', 'danger')
        return redirect(url_for('karyawan_input_progres'))
    if not file_laporan.filename.lower().endswith('.pdf'):
        flash('File laporan harus berformat PDF.', 'danger')
        return redirect(url_for('karyawan_input_progres'))

    filename = secure_filename(f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_laporan.filename}")
    file_laporan.save(os.path.join(app.config['UPLOAD_FOLDER_LAPORAN'], filename))
    file_path = f"uploads/laporan_kerja/{filename}"

    ajukan_laporan(nama_user, nama_proyek, deskripsi, status, progres_manual, file_path)
    flash('Laporan kerja berhasil dikirim!', 'success')
    return redirect(url_for('karyawan_input_progres'))

@app.route('/karyawan/kirim-ulang-laporan/<int:id>', methods=['POST'])
@login_required(role='karyawan')
def karyawan_kirim_ulang_laporan(id):
    nama_user = session['user']['username']
    deskripsi = request.form.get('tugas_pekerjaan')
    status = request.form.get('status_tugas')
    progres_manual = request.form.get('progres_manual')
    progres_manual = int(progres_manual) if progres_manual else None

    file_laporan = request.files.get('file_laporan')
    if not file_laporan or file_laporan.filename == '':
        flash('File laporan revisi wajib diunggah!', 'danger')
        return redirect(url_for('karyawan_input_progres'))
    if not file_laporan.filename.lower().endswith('.pdf'):
        flash('File laporan harus berformat PDF.', 'danger')
        return redirect(url_for('karyawan_input_progres'))

    filename = secure_filename(f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_laporan.filename}")
    file_laporan.save(os.path.join(app.config['UPLOAD_FOLDER_LAPORAN'], filename))
    file_path = f"uploads/laporan_kerja/{filename}"

    kirim_ulang_laporan(id, nama_user, deskripsi, status, progres_manual, file_path)
    flash('Laporan revisi berhasil dikirim ulang untuk ditinjau!', 'success')
    return redirect(url_for('karyawan_input_progres'))

@app.route('/karyawan/slip-gaji')
@login_required(role='karyawan')
def karyawan_slip_gaji():
    nama_user = session['user']['username']
    karyawan = get_karyawan_by_username(nama_user)
    if not karyawan:
        flash('Data karyawan tidak ditemukan!', 'danger')
        return redirect(url_for('karyawan_dashboard'))

    karyawan['jabatan'] = get_jabatan_tampilan(karyawan['id'], karyawan['divisi'])

    today = datetime.now()
    bulan_dipilih = int(request.args.get('bulan', today.month))
    tahun_dipilih = int(request.args.get('tahun', today.year))

    slip = get_slip_gaji(karyawan['id'], bulan_dipilih, tahun_dipilih)
    daftar_bulan = get_semua_bulan_tersedia(karyawan['id'])

    return render_template(
        'karyawan/slip_gaji.html',
        profil=karyawan,
        slip=slip,
        bulan_dipilih=bulan_dipilih,
        tahun_dipilih=tahun_dipilih,
        daftar_bulan=daftar_bulan,
        nama_bulan=NAMA_BULAN
    )

# ============================================================
# RUTE DIREKTUR
# ============================================================

@app.route('/direktur/dashboard')
@login_required(role='direktur')
def direktur_dashboard():
    karyawan_per_divisi = get_karyawan_per_divisi()
    total_karyawan = get_total_karyawan_aktif()

    progres_proyek = get_progres_per_proyek()
    proyek_aktif = len([p for p in progres_proyek.values() if p < 100])

    tingkat_kehadiran = get_tingkat_kehadiran_hari_ini()

    progres_per_divisi = build_laporan_progres_dashboard()

    laporan_terbaru = []
    for row in get_semua_laporan_admin()[:5]:
        laporan_terbaru.append({
            "tanggal": row['tanggal_kirim'],
            "nama": row['nama_lengkap'] or row['nama_karyawan'],
            "aktivitas": f"Submit laporan progres {row['nama_proyek']}",
            "status": "Selesai" if row['status_validasi'] == 'Disetujui' else "Pending",
        })

    izin_terbaru = []
    for izin in get_semua_pengajuan_izin()[:5]:
        k = get_karyawan_by_username(izin['nama_karyawan'])
        izin_terbaru.append({
            "tanggal": izin['tanggal'],
            "nama": k['nama_lengkap'] if k else izin['nama_karyawan'],
            "aktivitas": f"Pengajuan {izin['status']}",
            "status": izin['status_approval'],
        })

    return render_template(
        'direktur/dashboard.html',
        total_karyawan=total_karyawan,
        proyek_aktif=proyek_aktif,
        tingkat_kehadiran=tingkat_kehadiran,
        progres_per_divisi=progres_per_divisi,
        karyawan_per_divisi=karyawan_per_divisi,
        laporan_terbaru=laporan_terbaru,
        izin_terbaru=izin_terbaru,
    )

@app.route('/direktur/monitoring')
@login_required(role='direktur')
def direktur_monitoring():
    semua_laporan = get_semua_laporan_admin()  

    proyek_map = {}
    for row in semua_laporan:
        nama = row['nama_proyek']
        if nama not in proyek_map:
            proyek_map[nama] = row
    daftar_proyek = list(proyek_map.values())

    for p in daftar_proyek:
        progres = p['progres']
        if progres >= 70:
            p['kondisi'] = 'On Track'
            p['kondisi_class'] = 'status-on-track'
            p['warna_progres'] = 'fill-green'
        elif progres >= 30:
            p['kondisi'] = 'Delayed'
            p['kondisi_class'] = 'status-delayed'
            p['warna_progres'] = 'fill-orange'
        else:
            p['kondisi'] = 'Critical'
            p['kondisi_class'] = 'status-critical'
            p['warna_progres'] = 'fill-red'

    total_proyek = len(daftar_proyek)
    sudah_selesai = len([p for p in daftar_proyek if p['progres'] == 100])
    perlu_perhatian = len([p for p in daftar_proyek if 30 <= p['progres'] < 70])
    terhambat = len([p for p in daftar_proyek if p['progres'] < 30])

    return render_template(
        'direktur/monitoring.html',
        daftar_proyek=daftar_proyek,
        total_proyek=total_proyek,
        sudah_selesai=sudah_selesai,
        perlu_perhatian=perlu_perhatian,
        terhambat=terhambat,
    )

@app.route('/direktur/absensi')
@login_required(role='direktur')
def direktur_absensi():
    tanggal_str = request.args.get('tanggal')
    if tanggal_str:
        tanggal_pilih = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
    else:
        tanggal_pilih = datetime.now().date()

    bulan_pilih = int(request.args.get('bulan', tanggal_pilih.month))
    tahun_pilih = int(request.args.get('tahun', tanggal_pilih.year))
    page = int(request.args.get('page', 1))

    data_absensi = get_absensi_tanggal(tanggal_pilih)
    total_karyawan = len(data_absensi)
    hadir = len([d for d in data_absensi if d['status'] == 'Hadir'])
    izin_cuti = len([d for d in data_absensi if d['status'] in ('Cuti', 'Izin Lainnya')])
    sakit = len([d for d in data_absensi if d['status'] == 'Sakit'])
    alpha = len([d for d in data_absensi if d['status'] == 'Alpha'])

    daftar_tanggal_bulan = get_daftar_tanggal_bulan(bulan_pilih, tahun_pilih)
    per_page = 10
    total_pages = max(1, (len(daftar_tanggal_bulan) + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    tanggal_halaman = daftar_tanggal_bulan[start:start + per_page]

    tanggal_kemarin = tanggal_pilih - timedelta(days=1)
    tanggal_besok = tanggal_pilih + timedelta(days=1)
    bisa_maju = tanggal_besok <= datetime.now().date()

    return render_template(
        'direktur/absensi.html',
        data_absensi=data_absensi,
        total_karyawan=total_karyawan,
        hadir=hadir,
        izin_cuti=izin_cuti,
        sakit=sakit,
        alpha=alpha,
        tanggal_pilih=tanggal_pilih,
        tanggal_pilih_str=tanggal_pilih.strftime('%Y-%m-%d'),
        tanggal_kemarin=tanggal_kemarin.strftime('%Y-%m-%d'),
        tanggal_besok=tanggal_besok.strftime('%Y-%m-%d'),
        bisa_maju=bisa_maju,
        bulan_pilih=bulan_pilih,
        tahun_pilih=tahun_pilih,
        tanggal_halaman=tanggal_halaman,
        page=page,
        total_pages=total_pages,
    )

@app.route('/direktur/reset-absensi', methods=['POST'])
@login_required(role='direktur')
def direktur_reset_absensi():
    nama = request.form.get('nama')
    if nama == 'semua':
        reset_absensi_hari_ini()
        flash('Absensi hari ini untuk SEMUA orang berhasil direset!', 'success')
    else:
        reset_absensi_hari_ini(nama)
        flash(f'Absensi hari ini untuk {nama} berhasil direset!', 'success')
    return redirect(url_for('direktur_absensi'))

@app.route('/direktur/penggajian')
@login_required(role='direktur')
def direktur_penggajian():
    return redirect(url_for('direktur_bp.direktur_penggajian'))

@app.route('/direktur/validasi-gaji')
@login_required(role='direktur')
def direktur_validasi_gaji():
    return redirect(url_for('direktur_bp.direktur_penggajian'))

@app.route('/direktur/laporan')
@login_required(role='direktur')
def direktur_laporan():
    daftar_laporan = get_laporan_untuk_direktur()
    total_revisi = len([l for l in daftar_laporan if l['status_validasi'] == 'Revisi'])
    total_selesai = len([l for l in daftar_laporan if l['status_validasi'] == 'Disetujui'])
    total_proses = len([l for l in daftar_laporan if l['status_validasi'] == 'Menunggu Validasi Direktur'])
    return render_template(
        'direktur/laporan.html',
        daftar_laporan=daftar_laporan,
        total_revisi=total_revisi,
        total_selesai=total_selesai,
        total_proses=total_proses
    )


@app.route('/direktur/validasi-laporan/<int:id>', methods=['POST'])
@login_required(role='direktur')
def direktur_validasi_laporan(id):
    aksi = request.form.get('aksi')
    catatan = (request.form.get('catatan_revisi') or '').strip()

    if aksi == 'setuju':
        validasi_laporan(id, 'Disetujui', None)
        flash('Laporan berhasil disetujui!', 'success')
    elif aksi == 'revisi':
        if not catatan:
            flash('Catatan revisi wajib diisi supaya karyawan tahu apa yang perlu diperbaiki!', 'danger')
            return redirect(url_for('direktur_laporan'))
        validasi_laporan(id, 'Revisi', catatan)
        flash('Laporan dikembalikan untuk direvisi.', 'success')

    return redirect(url_for('direktur_laporan'))

# ============================================================
# RUTE API ABSENSI (JSON)
# ============================================================

@app.route('/proses-absen-masuk', methods=['POST'])
def proses_absen_masuk():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    nama = session['user']['username']
    hasil = catat_absen_masuk(nama, data.get('lat'), data.get('lon'), data.get('alamat'))
    return jsonify(hasil)

@app.route('/proses-absen-keluar', methods=['POST'])
def proses_absen_keluar():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"}), 401
    nama = session['user']['username']
    catat_absen_keluar(nama)
    status = get_status_hari_ini(nama)
    durasi = hitung_durasi_kerja(status['masuk'], status['keluar']) if status else '-'
    return jsonify({
        "jam_keluar": status['keluar'] if status else '-',
        "durasi_kerja": durasi
    })

if __name__ == '__main__':
    app.run(debug=debug_mode, port=server_port)