import resend
from flask import Blueprint, flash, redirect, url_for, render_template, session, request
from models.karyawan_model import get_semua_karyawan, get_karyawan_by_id, update_status_gaji
from models.absensi_model import hitung_potongan_gaji
from functools import wraps
from models.gaji_model import simpan_slip_gaji, is_slip_terkirim, NAMA_BULAN
import datetime

import os

direktur_bp = Blueprint('direktur_bp', __name__)
resend.api_key = os.getenv("RESEND_API_KEY")

print("KEY AKTIF DI DIREKTUR:", resend.api_key[:15] if resend.api_key else "KOSONG")


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or (role and session['user'].get('role') != role):
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _hitung_rincian_gaji(karyawan, bulan, tahun):
    """Hitung potongan & gaji bersih 1 karyawan untuk BULAN & TAHUN tertentu (bukan selalu bulan berjalan)."""
    gaji_pokok = float(karyawan['gaji_pokok'])
    tunjangan = float(karyawan['tunjangan'])
    hasil_potongan = hitung_potongan_gaji(karyawan['username'], gaji_pokok, bulan=bulan, tahun=tahun)

    total_penghasilan = gaji_pokok + tunjangan
    total_potongan = hasil_potongan['total_potongan']
    gaji_bersih = total_penghasilan - total_potongan

    sudah_terkirim = is_slip_terkirim(karyawan['id'], bulan, tahun)

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
    today = datetime.date.today()
    bulan_dipilih = request.args.get('bulan', type=int, default=today.month)
    tahun_dipilih = request.args.get('tahun', type=int, default=today.year)

    daftar_karyawan = get_semua_karyawan()
    data_gaji = [_hitung_rincian_gaji(k, bulan_dipilih, tahun_dipilih) for k in daftar_karyawan]

    total_gaji_bulan_ini = sum(d['gaji_bersih'] for d in data_gaji)
    total_potongan_bulan_ini = sum(d['total_potongan'] for d in data_gaji)
    sudah_terkirim = len([d for d in data_gaji if d['status_gaji'] == 'Terkirim'])
    belum_terkirim = len(data_gaji) - sudah_terkirim

    bulan_masih_berjalan = (bulan_dipilih == today.month and tahun_dipilih == today.year)

    return render_template(
        'direktur/penggajian.html',
        data_gaji=data_gaji,
        total_gaji_bulan_ini=total_gaji_bulan_ini,
        total_potongan_bulan_ini=total_potongan_bulan_ini,
        sudah_terkirim=sudah_terkirim,
        belum_terkirim=belum_terkirim,
        bulan_dipilih=bulan_dipilih,
        tahun_dipilih=tahun_dipilih,
        nama_bulan=NAMA_BULAN,
        bulan_masih_berjalan=bulan_masih_berjalan,
    )


@direktur_bp.route('/direktur/slip-detail/<int:id>')
@login_required(role='direktur')
def direktur_slip_detail(id):
    today = datetime.date.today()
    bulan_dipilih = request.args.get('bulan', type=int, default=today.month)
    tahun_dipilih = request.args.get('tahun', type=int, default=today.year)

    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data karyawan tidak ditemukan!', 'danger')
        return redirect(url_for('direktur_bp.direktur_penggajian'))

    rincian = _hitung_rincian_gaji(karyawan, bulan_dipilih, tahun_dipilih)
    return render_template(
        'direktur/slip_detail.html',
        k=rincian,
        bulan_dipilih=bulan_dipilih,
        tahun_dipilih=tahun_dipilih,
        nama_bulan=NAMA_BULAN,
    )


@direktur_bp.route('/direktur/kirim_slip/<int:id>', methods=['POST'])
@login_required(role='direktur')
def kirim_slip(id):
    bulan_dipilih = request.form.get('bulan', type=int)
    tahun_dipilih = request.form.get('tahun', type=int)
    if not bulan_dipilih or not tahun_dipilih:
        today = datetime.date.today()
        bulan_dipilih = today.month
        tahun_dipilih = today.year

    karyawan = get_karyawan_by_id(id)
    if not karyawan:
        flash('Data tidak ditemukan!', 'danger')
        return redirect(url_for('direktur_bp.direktur_penggajian'))

    rincian = _hitung_rincian_gaji(karyawan, bulan_dipilih, tahun_dipilih)

    simpan_slip_gaji(karyawan['id'], bulan_dipilih, tahun_dipilih, rincian)

    try:
        rekap = rincian['rekap']
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 650px; margin: auto; color: #2d3748;">
            <h2 style="margin-bottom: 5px;">Slip Gaji - {karyawan['nama_lengkap']} - {NAMA_BULAN[bulan_dipilih]} {tahun_dipilih}</h2>
            <div style="border-bottom: 1px solid #e2e8f0; margin-bottom: 20px; padding-bottom: 10px;">
                <p style="margin: 0;"><strong>CV Amarta Utomo</strong><br>
                Jl. Osamaliki No. 57, Salatiga<br>
                Periode Penggajian: {NAMA_BULAN[bulan_dipilih]} {tahun_dipilih}</p>
            </div>
            <h4 style="margin-bottom: 8px;">INFORMASI KARYAWAN</h4>
            <table style="border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 2px 15px 2px 0; color:#4a5568;">Nama</td><td>: {karyawan['nama_lengkap']}</td></tr>
                <tr><td style="padding: 2px 15px 2px 0; color:#4a5568;">ID Karyawan</td><td>: {karyawan['id_karyawan']}</td></tr>
                <tr><td style="padding: 2px 15px 2px 0; color:#4a5568;">Jabatan</td><td>: {karyawan['jabatan']}</td></tr>
                <tr><td style="padding: 2px 15px 2px 0; color:#4a5568;">Divisi</td><td>: {karyawan['divisi']}</td></tr>
            </table>
            <div style="background:#f8fafc; padding: 12px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.9rem;">
                <strong>Rekap Kehadiran:</strong>
                Hadir {rekap.get('Hadir', 0)} hari &bull;
                Cuti {rekap.get('Cuti', 0)} hari &bull;
                Sakit {rekap.get('Sakit', 0)} hari &bull;
                Izin Lainnya {rekap.get('Izin Lainnya', 0)} hari &bull;
                <span style="color:#e53e3e; font-weight:600;">Tanpa Keterangan (Alpha) {rekap.get('Alpha', 0)} hari</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                <tr style="background:#edf2f7;">
                    <th style="padding: 8px; text-align: left;" colspan="2">PENGHASILAN</th>
                </tr>
                <tr><td style="padding: 5px;">Gaji Pokok</td><td style="text-align: right;">Rp {rincian['gaji_pokok']:,.0f}</td></tr>
                <tr><td style="padding: 5px;">Tunjangan</td><td style="text-align: right;">Rp {rincian['tunjangan']:,.0f}</td></tr>
                <tr style="border-top: 2px solid #cbd5e0; font-weight: bold;">
                    <td style="padding: 5px;">TOTAL PENGHASILAN</td><td style="text-align: right;">Rp {rincian['total_penghasilan']:,.0f}</td>
                </tr>
            </table>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background:#edf2f7;">
                    <th style="padding: 8px; text-align: left;" colspan="2">POTONGAN</th>
                </tr>
                <tr>
                    <td style="padding: 5px;">
                        {"Tanpa Keterangan / Alpha (" + str(rincian['jumlah_hari_potong']) + " hari)" if rincian['jumlah_hari_potong'] > 0 else "Tidak ada potongan"}
                    </td>
                    <td style="text-align: right;">Rp {rincian['total_potongan']:,.0f}</td>
                </tr>
                <tr style="border-top: 2px solid #cbd5e0; font-weight: bold;">
                    <td style="padding: 5px;">TOTAL POTONGAN</td><td style="text-align: right;">Rp {rincian['total_potongan']:,.0f}</td>
                </tr>
            </table>
            <div style="background: #3b82f6; color: white; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 1.1rem; margin-bottom: 30px;">
                TOTAL GAJI BERSIH: Rp {rincian['gaji_bersih']:,.0f}
            </div>
            <div style="text-align: right; margin-top: 40px;">
                <p style="margin-bottom: 0;">Mengetahui,</p>
                <p style="margin-top: 2px; margin-bottom: 40px;">Direktur</p>
                <p style="margin: 0; font-weight: 700; font-style: italic; font-size: 1.2rem;">Gloria Kho</p>
                <p style="margin-top: 2px; padding-top: 4px; border-top: 1px solid #4a5568; display: inline-block; font-size: 0.85rem;">( Gloria Kho )</p>
            </div>
        </div>
        """
        params = {
            "from": "onboarding@resend.dev",
            "to": ["gloriateresa1122@gmail.com"],
            "reply_to": [karyawan['email']],
            "subject": f"Slip Gaji - {karyawan['nama_lengkap']} - {NAMA_BULAN[bulan_dipilih]} {tahun_dipilih}",
            "html": html_body,
        }
        resend.Emails.send(params)
        
        flash(f'Slip gaji {NAMA_BULAN[bulan_dipilih]} {tahun_dipilih} berhasil dikirim ke {karyawan["nama_lengkap"]}!', 'success')
    except Exception as e:
        flash(f'Gagal mengirim email: {str(e)}', 'danger')

    return redirect(url_for('direktur_bp.direktur_penggajian', bulan=bulan_dipilih, tahun=tahun_dipilih))