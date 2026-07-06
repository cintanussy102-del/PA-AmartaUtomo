import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from functools import wraps
from controllers.direktur_controller import direktur_bp
from models.karyawan_model import get_data_karyawan_by_name, get_profil_gaji
from models.absensi_model import (
    get_riwayat_absensi, get_status_hari_ini,
    catat_absen_masuk, catat_absen_keluar, ajukan_izin,
    hitung_potongan_gaji
)
from datetime import datetime
from werkzeug.utils import secure_filename


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

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Di dalam app.route('/login')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
    
    # Logika Admin & Direktur
        if username == 'admin' and password == 'admin':
            session['user'] = {'username': 'admin', 'role': 'admin'}
            return redirect(url_for('admin_dashboard'))
        elif username == 'direktur' and password == 'direktur':
            session['user'] = {'username': 'direktur', 'role': 'direktur'}
            return redirect(url_for('direktur_dashboard'))
        
        # Logika Karyawan (Data dinamis berdasarkan nama)
        elif username == 'karyawan' and (password == 'Rony' or password == 'Aloy' or password == 'Putri'):
            session['user'] = {
                'username': password, # Menggunakan nama sebagai username
                'role': 'karyawan'
            }
            return redirect(url_for('karyawan_dashboard'))
        else:
            flash('Username atau password salah!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil keluar.', 'info') # Opsional: menampilkan pesan
    return redirect(url_for('login')) # <--- Diubah ke 'login'

# --- RUTE ADMIN ---
@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/data-karyawan')
@login_required(role='admin')
def admin_data_karyawan():
    return render_template('admin/data_karyawan.html')

@app.route('/admin/absensi')
@login_required(role='admin')
def admin_absensi():
    return render_template('admin/kelola_absensi.html')

@app.route('/admin/divisi')
@login_required(role='admin')
def admin_divisi():
    # Mengambil data dari database (asumsi kamu sudah punya model Divisi)
    # Jika belum, kamu bisa menggunakan list of dictionaries sementara
    divisi_data = [
        {'nama': 'Arsitek', 'karyawan': 32, 'kepala': 'Ahmad Fauzi', 'status': 'Aktif'},
        {'nama': 'Desain', 'karyawan': 18, 'kepala': 'Agus Setiawan', 'status': 'Aktif'},
        # ... dan seterusnya
    ]
    return render_template('admin/divisi.html', divisi_list=divisi_data)

@app.route('/admin/rekap-laporan')
@login_required(role='admin')
def admin_rekap_laporan():
    return render_template('admin/rekap_laporan.html')

@app.route('/admin/slip-gaji')
@login_required(role='admin')
def admin_slip_gaji():
    return render_template('admin/slip_gaji.html')

# --- RUTE KARYAWAN ---
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
    return render_template('karyawan/absensi.html', riwayat=riwayat, status_hari_ini=status_hari_ini)

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

    wajib_upload = jenis_izin in ['Sakit', 'Izin Penting', 'Cuti Tahunan']
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
    return render_template('karyawan/input_progres.html')

@app.route('/karyawan/slip-gaji')
@login_required(role='karyawan')
def karyawan_slip_gaji():
    nama_user = session['user']['username']
    profil = get_profil_gaji(nama_user)
    hasil_potongan = hitung_potongan_gaji(nama_user, profil['gaji_pokok'])

    total_penghasilan = profil['gaji_pokok'] + profil['tunjangan']
    total_potongan = hasil_potongan['total_potongan']
    gaji_bersih = total_penghasilan - total_potongan

    return render_template(
        'karyawan/slip_gaji.html',
        profil=profil,
        hasil_potongan=hasil_potongan,
        total_penghasilan=total_penghasilan,
        total_potongan=total_potongan,
        gaji_bersih=gaji_bersih
    )

# --- RUTE DIREKTUR ---
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
    return render_template('direktur/absensi.html')

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
    return render_template('direktur/laporan.html')

@app.route('/proses-absen-masuk', methods=['POST'])
@login_required(role='karyawan')
def proses_absen_masuk():
    data = request.json
    nama = session['user']['username']
    catat_absen_masuk(nama, data.get('lat'), data.get('lon'), data.get('alamat'))
    
    return jsonify({"status": "sukses", "message": "Absen berhasil!"})



import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from functools import wraps
from controllers.direktur_controller import direktur_bp
from models.karyawan_model import get_data_karyawan_by_name, get_profil_gaji
from models.absensi_model import (
    get_riwayat_absensi, get_status_hari_ini,
    catat_absen_masuk, catat_absen_keluar, ajukan_izin,
    hitung_potongan_gaji
)
from datetime import datetime
from werkzeug.utils import secure_filename


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

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Di dalam app.route('/login')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
    
    # Logika Admin & Direktur
        if username == 'admin' and password == 'admin':
            session['user'] = {'username': 'admin', 'role': 'admin'}
            return redirect(url_for('admin_dashboard'))
        elif username == 'direktur' and password == 'direktur':
            session['user'] = {'username': 'direktur', 'role': 'direktur'}
            return redirect(url_for('direktur_dashboard'))
        
        # Logika Karyawan (Data dinamis berdasarkan nama)
        elif username == 'karyawan' and (password == 'Rony' or password == 'Aloy' or password == 'Putri'):
            session['user'] = {
                'username': password, # Menggunakan nama sebagai username
                'role': 'karyawan'
            }
            return redirect(url_for('karyawan_dashboard'))
        else:
            flash('Username atau password salah!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil keluar.', 'info') # Opsional: menampilkan pesan
    return redirect(url_for('login')) # <--- Diubah ke 'login'

# --- RUTE ADMIN ---
@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/data-karyawan')
@login_required(role='admin')
def admin_data_karyawan():
    return render_template('admin/data_karyawan.html')

@app.route('/admin/absensi')
@login_required(role='admin')
def admin_absensi():
    return render_template('admin/kelola_absensi.html')

@app.route('/admin/divisi')
@login_required(role='admin')
def admin_divisi():
    # Mengambil data dari database (asumsi kamu sudah punya model Divisi)
    # Jika belum, kamu bisa menggunakan list of dictionaries sementara
    divisi_data = [
        {'nama': 'Arsitek', 'karyawan': 32, 'kepala': 'Ahmad Fauzi', 'status': 'Aktif'},
        {'nama': 'Desain', 'karyawan': 18, 'kepala': 'Agus Setiawan', 'status': 'Aktif'},
        # ... dan seterusnya
    ]
    return render_template('admin/divisi.html', divisi_list=divisi_data)

@app.route('/admin/rekap-laporan')
@login_required(role='admin')
def admin_rekap_laporan():
    return render_template('admin/rekap_laporan.html')

@app.route('/admin/slip-gaji')
@login_required(role='admin')
def admin_slip_gaji():
    return render_template('admin/slip_gaji.html')

# --- RUTE KARYAWAN ---
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
    return render_template('karyawan/absensi.html', riwayat=riwayat, status_hari_ini=status_hari_ini)

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
    return render_template('karyawan/input_progres.html')

@app.route('/karyawan/slip-gaji')
@login_required(role='karyawan')
def karyawan_slip_gaji():
    nama_user = session['user']['username']
    profil = get_profil_gaji(nama_user)
    hasil_potongan = hitung_potongan_gaji(nama_user, profil['gaji_pokok'])

    total_penghasilan = profil['gaji_pokok'] + profil['tunjangan']
    total_potongan = hasil_potongan['total_potongan']
    gaji_bersih = total_penghasilan - total_potongan

    return render_template(
        'karyawan/slip_gaji.html',
        profil=profil,
        hasil_potongan=hasil_potongan,
        total_penghasilan=total_penghasilan,
        total_potongan=total_potongan,
        gaji_bersih=gaji_bersih
    )

# --- RUTE DIREKTUR ---
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
    return render_template('direktur/absensi.html')

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
    return render_template('direktur/laporan.html')

@app.route('/proses-absen-masuk', methods=['POST'])
@login_required(role='karyawan')
def proses_absen_masuk():
    data = request.json
    nama = session['user']['username']
    catat_absen_masuk(nama, data.get('lat'), data.get('lon'), data.get('alamat'))
    
    return jsonify({"status": "sukses", "message": "Absen berhasil!"})

if __name__ == '__main__':
    app.run(debug=debug_mode, port=server_port)