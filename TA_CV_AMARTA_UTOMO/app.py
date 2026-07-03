import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join('views', 'templates'),
    static_folder=os.path.join('views', 'static')
)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key_amarta')
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
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        # 1. DATABASE SEMENTARA (Masing-masing Karyawan Punya Data Berbeda)
        data_karyawan = {
            'Rony': {
                'id': 'KRY-0042',
                'jabatan': 'Produksi / Staff Lapangan',
                'hadir': '18 HARI',
                'izin': '2 HARI',
                'progres': '75%',
                'gaji': 'JUNI 2026'
            },
            'Aloy': {
                'id': 'KRY-0015',
                'jabatan': 'Teknik / Surveyor',
                'hadir': '20 HARI',
                'izin': '0 HARI',
                'progres': '90%',
                'gaji': 'MEI 2026'
            },
            'Putri': {
                'id': 'KRY-0089',
                'jabatan': 'Administrasi / Dokumen Kontrol',
                'hadir': '16 HARI',
                'izin': '4 HARI',
                'progres': '60%',
                'gaji': 'JUNI 2026'
            }
        }
        
        # 2. LOGIKA VALIDASI LOGIN
        if 'admin' in username.lower():
            session['user'] = {'username': username, 'role': 'admin'}
            return redirect(url_for('admin_dashboard'))
            
        elif 'direktur' in username.lower():
            session['user'] = {'username': username, 'role': 'direktur'}
            return redirect(url_for('direktur_dashboard'))
            
        # Jika username yang diinput ada di database karyawan kita dan password-nya benar
        elif username in data_karyawan and password == 'karyawan':
            # Simpan semua data spesifik karyawan tersebut ke dalam session
            session['user'] = {
                'username': username,
                'role': 'karyawan',
                'id': data_karyawan[username]['id'],
                'jabatan': data_karyawan[username]['jabatan'],
                'hadir': data_karyawan[username]['hadir'],
                'izin': data_karyawan[username]['izin'],
                'progres': data_karyawan[username]['progres'],
                'gaji': data_karyawan[username]['gaji']
            }
            return redirect(url_for('karyawan_dashboard'))
            
        else:
            flash('Username atau password salah!', 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))

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
    return render_template('karyawan/dashboard.html')

@app.route('/karyawan/absensi')
@login_required(role='karyawan')
def karyawan_absensi():
    return render_template('karyawan/absensi.html')

# --- RUTE DIREKTUR ---
@app.route('/direktur/dashboard')
@login_required(role='direktur')
def direktur_dashboard():
    return render_template('direktur/dashboard.html')

@app.route('/direktur/monitoring')
@login_required(role='direktur')
def direktur_monitoring():
    return render_template('direktur/monitoring.html')

if __name__ == '__main__':
    app.run(debug=debug_mode, port=server_port)