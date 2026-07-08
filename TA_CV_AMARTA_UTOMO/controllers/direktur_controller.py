import resend
from flask import Blueprint, flash, redirect, url_for, render_template, session
from models.karyawan_model import get_semua_karyawan, get_karyawan_by_id, update_status_gaji
from models.absensi_model import hitung_potongan_gaji
from functools import wraps
from models.gaji_model import simpan_slip_gaji, is_slip_terkirim, NAMA_BULAN
import datetime

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


def _hitung_rincian_gaji(karyawan):
    """Hitung potongan & gaji bersih 1 karyawan berdasarkan data absensi bulan ini."""
    gaji_pokok = float(karyawan['gaji_pokok'])
    tunjangan = float(karyawan['tunjangan'])
    hasil_potongan = hitung_potongan_gaji(karyawan['username'], gaji_pokok)

    total_penghasilan = gaji_pokok + tunjangan
    total_potongan = hasil_potongan['total_potongan']
    gaji_bersih = total_penghasilan - total_potongan

    today = datetime.date.today()
    sudah_terkirim = is_slip_terkirim(karyawan['id'], today.month, today.year)

    return {
        **karyawan,
        "gaji_pokok": gaji_pokok,
        "tunjangan": tunjangan,
        "total_penghasilan": total_penghasilan,
        "rekap": hasil_potongan['rekap'],
        "jumlah_hari_potong": hasil_potongan['jumlah_hari_potong'],
        "total_potongan": total_potongan,
        "gaji_bersih": gaji_bersih,
        "status_gaji": "Terkirim" if sudah_terkirim else "Belum",
    }


@direktur_bp.route('/direktur/penggajian_data')
@login_required(role='direktur')
def direktur_penggajian():
    daftar_karyawan = get_semua_karyawan()
    data_gaji = [_hitung_rincian_gaji(k) for k in daftar_karyawan]

    total_gaji_bulan_ini = sum(d['gaji_bersih'] for d in data_gaji)
    total_potongan_bulan_ini = sum(d['total_potongan'] for d in data_gaji)
    sudah_terkirim = len([d for d in data_gaji if d['status_gaji'] == 'Terkirim'])
    belum_terkirim = len(data_gaji) - sudah_terkirim

    return render_template(
        'direktur/penggajian.html',
        data_gaji=data_gaji,
        total_gaji_bulan_ini=total_gaji_bulan_ini,
        total_potongan_bulan_ini=total_potongan_bulan_ini,
        sudah_terkirim=sudah_terkirim,
        belum_terkirim=belum_terkirim
    )


@direktur_bp.route('/direktur/slip-detail/<int:id>')
@login_required(role='direktur')
def direktur_slip_detail(id):
    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data karyawan tidak ditemukan!', 'danger')
        return redirect(url_for('direktur_bp.direktur_penggajian'))

    rincian = _hitung_rincian_gaji(karyawan)
    return render_template('direktur/slip_detail.html', k=rincian)


@direktur_bp.route('/direktur/kirim_slip/<int:id>', methods=['POST'])
@login_required(role='direktur')
def kirim_slip(id):
    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data tidak ditemukan!', 'danger')
        return redirect(url_for('direktur_bp.direktur_penggajian'))

    rincian = _hitung_rincian_gaji(karyawan)
    today = datetime.date.today()

    # Simpan snapshot slip gaji bulan ini — INI KUNCI SINKRONNYA
    simpan_slip_gaji(karyawan['id'], today.month, today.year, rincian)

    try:
        params = {
            "from": "onboarding@resend.dev",
            "to": [karyawan['email']],
            "subject": "Slip Gaji Bulanan - CV Amarta Utomo",
            "html": f"""
                <p>Halo {karyawan['nama_lengkap']},</p>
                <p>Berikut rincian gaji Anda bulan {NAMA_BULAN[today.month]} {today.year}:</p>
                <ul>
                    <li>Gaji Pokok: Rp {rincian['gaji_pokok']:,.0f}</li>
                    <li>Tunjangan: Rp {rincian['tunjangan']:,.0f}</li>
                    <li>Potongan: Rp {rincian['total_potongan']:,.0f}</li>
                    <li><strong>Gaji Bersih: Rp {rincian['gaji_bersih']:,.0f}</strong></li>
                </ul>
            """
        }
        resend.Emails.send(params)
        flash(f'Slip gaji berhasil dikirim ke {karyawan["nama_lengkap"]}!', 'success')
    except Exception as e:
        flash(f'Gagal mengirim email: {str(e)}', 'danger')

    return redirect(url_for('direktur_bp.direktur_penggajian'))