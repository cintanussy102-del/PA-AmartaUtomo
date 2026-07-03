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
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin':
            session['user'] = {'username': 'admin', 'role': 'admin'}
            return redirect(url_for('admin_dashboard'))
        elif username == 'karyawan' and password == 'karyawan':
            session['user'] = {'username': 'karyawan', 'role': 'karyawan'}
            return redirect(url_for('karyawan_dashboard'))
        elif username == 'direktur' and password == 'direktur':
            session['user'] = {'username': 'direktur', 'role': 'direktur'}
            return redirect(url_for('direktur_dashboard'))
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

@app.route('/admin/divisi')
@login_required(role='admin')
def admin_divisi():
    return render_template('admin/divisi.html')

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

@app.route('/direktur/absensi')
@login_required(role='direktur')
def direktur_absensi():
    return render_template('direktur/absensi.html')

@app.route('/direktur/penggajian')
@login_required(role='direktur')
def direktur_penggajian():
    return render_template('direktur/penggajian.html')

@app.route('/direktur/laporan')
@login_required(role='direktur')
def direktur_laporan():
    return render_template('direktur/laporan.html')

if __name__ == '__main__':
    app.run(debug=debug_mode, port=server_port)