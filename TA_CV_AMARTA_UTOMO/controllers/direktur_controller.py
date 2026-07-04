import resend
from flask import Blueprint, flash, redirect, url_for, render_template, session
from models.karyawan_model import get_karyawan_by_id, get_semua_data_gaji
from functools import wraps

direktur_bp = Blueprint('direktur_bp', __name__)
resend.api_key = "re_Q7MAFYLd_7TS5p25pWLK7VQgBcBhAdCVX"
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or (role and session['user'].get('role') != role):
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@direktur_bp.route('/direktur/penggajian_data')
@login_required(role='direktur')
def direktur_penggajian():
    data_gaji = get_semua_data_gaji()
    return render_template('direktur/penggajian.html', data_gaji=data_gaji)

@direktur_bp.route('/direktur/kirim_slip/<int:id>', methods=['POST'])
@login_required(role='direktur')
def kirim_slip(id):
    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data tidak ditemukan!')
        return redirect(url_for('direktur_bp.direktur_penggajian'))

    try:
        params = {
            "from": "onboarding@resend.dev",
            "to": [karyawan['email']],
            "subject": "Slip Gaji Bulanan",
            "html": f"<p>Halo {karyawan['nama']}, gaji Anda: Rp {karyawan['total_gaji']:,}</p>"
        }
        resend.Emails.send(params)
        flash(f'Slip gaji berhasil dikirim ke {karyawan["nama"]}!')
    except Exception as e:
        print(f"Error detail: {e}")
        flash(f'Gagal mengirim email: {str(e)}')
    
    return redirect(url_for('direktur_bp.direktur_penggajian'))