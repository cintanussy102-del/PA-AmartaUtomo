import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from functools import wraps
from controllers.direktur_controller import direktur_bp
from models.gaji_model import get_slip_gaji, get_semua_bulan_tersedia, NAMA_BULAN
from models.karyawan_model import (
    get_data_karyawan_by_name, get_profil_gaji,
    get_semua_karyawan, get_karyawan_by_id,
    tambah_karyawan, update_karyawan, hapus_karyawan,
    get_karyawan_by_username, get_karyawan_by_divisi_dan_username
)
from models.absensi_model import (
    get_absensi_hari_ini_semua, get_riwayat_absensi, get_status_hari_ini,
    catat_absen_masuk, catat_absen_keluar, ajukan_izin,
    hitung_potongan_gaji, get_rekap_absensi_hari_ini,
    hitung_durasi_kerja, get_rekap_bulanan,
    get_absensi_tanggal, get_daftar_tanggal_bulan, reset_absensi_hari_ini
)

from models.progres_model import (
       ajukan_laporan, get_ringkasan_laporan, kirim_ulang_laporan,
       get_semua_laporan_admin, get_laporan_detail, teruskan_ke_direktur,
       get_laporan_untuk_direktur, validasi_laporan
   )
from datetime import datetime
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

import resend

resend.api_key = "re_Q7MAFYLd_7TS5p25pWLK7VQgBcBhAdCVX"

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
                flash('Silakan login terlebih dahulu!', 'danger')
                return redirect(url_for('login'))
            if role and session['user'].get('role') != role:
                flash('Anda tidak memiliki akses ke halaman ini!', 'danger')
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

        if username == 'Admin' and password == 'Glory':
            session['user'] = {'username': 'admin', 'role': 'admin'}
            return redirect(url_for('admin_dashboard'))

        elif username == 'Direktur' and password == 'Gloria':
            session['user'] = {'username': 'direktur', 'role': 'direktur'}
            return redirect(url_for('direktur_dashboard'))

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
                flash('Username atau password salah!', 'danger')
                return redirect(url_for('login'))

        else:
            flash('Username atau password salah!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil keluar.', 'info')
    return redirect(url_for('login'))

# ============================================================
# RUTE ADMIN
# ============================================================

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    rekap_hari_ini = get_rekap_absensi_hari_ini()
    return render_template('admin/dashboard.html', rekap_hari_ini=rekap_hari_ini)

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
    riwayat = get_riwayat_absensi(nama_user)
    status_hari_ini = get_status_hari_ini(nama_user)
    durasi_kerja = hitung_durasi_kerja(
        status_hari_ini['masuk'] if status_hari_ini else None,
        status_hari_ini['keluar'] if status_hari_ini else None
    )
    rekap = get_rekap_bulanan(nama_user)
    return render_template(
        'admin/kelola_absensi.html',
        riwayat=riwayat,
        status_hari_ini=status_hari_ini,
        durasi_kerja=durasi_kerja,
        rekap=rekap
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
    # Ambil semua karyawan dari database lalu kelompokkan per divisi
    semua_karyawan = get_semua_karyawan()
    divisi_names = ['Arsitektur', 'Marketing', 'Logistik', 'Pengawas Lapangan']
    divisi_data = []
    for nama_divisi in divisi_names:
        anggota = [k for k in semua_karyawan if k['divisi'] == nama_divisi]
        kepala = anggota[0]['nama_lengkap'] if anggota else '-'
        divisi_data.append({
            'nama': nama_divisi,
            'karyawan': len(anggota),
            'kepala': kepala,
            'status': 'Aktif'
        })
    return render_template('admin/divisi.html', divisi_list=divisi_data)

@app.route('/admin/rekap-laporan')
@login_required(role='admin')
def admin_rekap_laporan():
    daftar_laporan = get_semua_laporan_admin()
    total = len(daftar_laporan)
    menunggu_admin = len([l for l in daftar_laporan if l['status_validasi'] == 'Menunggu Peninjauan Admin'])
    menunggu_direktur = len([l for l in daftar_laporan if l['status_validasi'] == 'Menunggu Validasi Direktur'])
    disetujui = len([l for l in daftar_laporan if l['status_validasi'] == 'Disetujui'])
    revisi = len([l for l in daftar_laporan if l['status_validasi'] == 'Revisi'])
    return render_template(
        'admin/rekap_laporan.html',
        daftar_laporan=daftar_laporan,
        total=total,
        menunggu_admin=menunggu_admin,
        menunggu_direktur=menunggu_direktur,
        disetujui=disetujui,
        revisi=revisi
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
    admin_data = get_karyawan_by_username('admin')  # sesuaikan kalau username-nya beda
    if not admin_data:
        flash('Data admin tidak ditemukan di database!', 'danger')
        return redirect(url_for('admin_dashboard'))

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
    data = get_data_karyawan_by_name(nama_user)
    riwayat = get_riwayat_absensi(nama_user, limit=3)
    return render_template('karyawan/dashboard.html', data=data, riwayat=riwayat)

@app.route('/karyawan/absensi')
@login_required(role='karyawan')
def karyawan_absensi():
    nama_user = session['user']['username']
    riwayat = get_riwayat_absensi(nama_user)
    status_hari_ini = get_status_hari_ini(nama_user)
    durasi_kerja = hitung_durasi_kerja(
        status_hari_ini['masuk'] if status_hari_ini else None,
        status_hari_ini['keluar'] if status_hari_ini else None
    )
    rekap = get_rekap_bulanan(nama_user)
    return render_template(
        'karyawan/absensi.html',
        riwayat=riwayat,
        status_hari_ini=status_hari_ini,
        durasi_kerja=durasi_kerja,
        rekap=rekap
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

@app.route('/karyawan/input-progres')
@login_required(role='karyawan')
def karyawan_input_progres():
    nama_user = session['user']['username']
    profil = get_profil_gaji(nama_user)
    ringkasan = get_ringkasan_laporan(nama_user)
    return render_template('karyawan/input_progres.html', profil=profil, ringkasan=ringkasan)

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
    return render_template('direktur/dashboard.html')

@app.route('/direktur/monitoring')
@login_required(role='direktur')
def direktur_monitoring():
    return render_template('direktur/monitoring.html')

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