from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
import datetime
from models.karyawan_model import get_karyawan_by_username
from models.gaji_model import get_slip_gaji, get_semua_bulan_tersedia, NAMA_BULAN

karyawan_bp = Blueprint('karyawan_bp', __name__)


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or (role and session['user'].get('role') != role):
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@karyawan_bp.route('/karyawan/slip-gaji')
@login_required(role='karyawan')
def karyawan_slip_gaji():
    username = session['user']['username']
    karyawan = get_karyawan_by_username(username)
    if not karyawan:
        flash_msg = "Data karyawan tidak ditemukan"
        return render_template('karyawan/slip_gaji.html', error=flash_msg)

    today = datetime.date.today()
    bulan = request.args.get('bulan', default=today.month, type=int)
    tahun = request.args.get('tahun', default=today.year, type=int)

    slip = get_slip_gaji(karyawan['id'], bulan, tahun)
    daftar_bulan = get_semua_bulan_tersedia(karyawan['id'])

    return render_template(
        'karyawan/slip_gaji.html',
        profil=karyawan,
        slip=slip,
        bulan_dipilih=bulan,
        tahun_dipilih=tahun,
        daftar_bulan=daftar_bulan,
        nama_bulan=NAMA_BULAN
    )