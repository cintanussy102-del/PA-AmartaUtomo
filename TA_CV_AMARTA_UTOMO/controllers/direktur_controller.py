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

from utils import build_laporan_progres_dashboard
from models.karyawan_model import get_karyawan_per_divisi, get_total_karyawan_aktif
from models.absensi_model import (
    get_tingkat_kehadiran_hari_ini, get_semua_pengajuan_izin, get_absensi_tanggal,
    get_daftar_tanggal_bulan, reset_absensi_hari_ini
)
from models.progres_model import (
    get_progres_per_proyek, get_laporan_untuk_direktur, validasi_laporan, get_semua_laporan_admin
)
from datetime import datetime, timedelta


def direktur_dashboard():
    karyawan_per_divisi = get_karyawan_per_divisi()
    total_karyawan = get_total_karyawan_aktif()

    from utils import TUGAS_PER_DIVISI
    proyek_aktif = sum(len(tugas) for tugas in TUGAS_PER_DIVISI.values())
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
        k = get_karyawan_by_id_by_username_helper(izin['nama_karyawan'])
        izin_terbaru.append({
            "tanggal": izin['tanggal'],
            "nama": k['nama_lengkap'] if k else izin['nama_karyawan'],
            "aktivitas": f"Pengajuan {izin['status']}",
            "status": izin['status_approval'],
        })

    return render_template(
        'direktur/dashboard.html', total_karyawan=total_karyawan, proyek_aktif=proyek_aktif,
        tingkat_kehadiran=tingkat_kehadiran, progres_per_divisi=progres_per_divisi,
        karyawan_per_divisi=karyawan_per_divisi, laporan_terbaru=laporan_terbaru, izin_terbaru=izin_terbaru,
    )


def get_karyawan_by_id_by_username_helper(username):
    from models.karyawan_model import get_karyawan_by_username
    return get_karyawan_by_username(username)


def direktur_monitoring():
    semua_laporan = get_semua_laporan_admin()
    proyek_map = {}
    for row in semua_laporan:
        if row['nama_proyek'] not in proyek_map:
            proyek_map[row['nama_proyek']] = row
    daftar_proyek = list(proyek_map.values())

    for p in daftar_proyek:
        progres = p['progres']
        if progres >= 70:
            p['kondisi'], p['kondisi_class'], p['warna_progres'] = 'On Track', 'status-on-track', 'fill-green'
        elif progres >= 30:
            p['kondisi'], p['kondisi_class'], p['warna_progres'] = 'Delayed', 'status-delayed', 'fill-orange'
        else:
            p['kondisi'], p['kondisi_class'], p['warna_progres'] = 'Critical', 'status-critical', 'fill-red'

    proyek_per_divisi = {}
    for p in daftar_proyek:
        divisi = p['divisi'] or 'Tanpa Divisi'
        proyek_per_divisi.setdefault(divisi, []).append(p)

    return render_template(
        'direktur/monitoring.html', proyek_per_divisi=proyek_per_divisi,
        total_proyek=len(daftar_proyek),
        sudah_selesai=len([p for p in daftar_proyek if p['progres'] == 100]),
        perlu_perhatian=len([p for p in daftar_proyek if 30 <= p['progres'] < 70]),
        terhambat=len([p for p in daftar_proyek if p['progres'] < 30]),
    )


def direktur_absensi():
    tanggal_str = request.args.get('tanggal')
    tanggal_pilih = datetime.strptime(tanggal_str, '%Y-%m-%d').date() if tanggal_str else datetime.now().date()
    bulan_pilih = int(request.args.get('bulan', tanggal_pilih.month))
    tahun_pilih = int(request.args.get('tahun', tanggal_pilih.year))
    page = int(request.args.get('page', 1))

    data_absensi = get_absensi_tanggal(tanggal_pilih)
    hadir = len([d for d in data_absensi if d['status'] == 'Hadir'])
    izin_cuti = len([d for d in data_absensi if d['status'] in ('Cuti', 'Izin Lainnya')])
    sakit = len([d for d in data_absensi if d['status'] == 'Sakit'])
    alpha = len([d for d in data_absensi if d['status'] == 'Alpha'])

    daftar_tanggal_bulan = get_daftar_tanggal_bulan(bulan_pilih, tahun_pilih)
    per_page = 10
    total_pages = max(1, (len(daftar_tanggal_bulan) + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    tanggal_halaman = daftar_tanggal_bulan[(page - 1) * per_page: (page - 1) * per_page + per_page]

    tanggal_kemarin = tanggal_pilih - timedelta(days=1)
    tanggal_besok = tanggal_pilih + timedelta(days=1)
    bisa_maju = tanggal_besok <= datetime.now().date()

    return render_template(
        'direktur/absensi.html', data_absensi=data_absensi, total_karyawan=len(data_absensi),
        hadir=hadir, izin_cuti=izin_cuti, sakit=sakit, alpha=alpha,
        tanggal_pilih=tanggal_pilih, tanggal_pilih_str=tanggal_pilih.strftime('%Y-%m-%d'),
        tanggal_kemarin=tanggal_kemarin.strftime('%Y-%m-%d'), tanggal_besok=tanggal_besok.strftime('%Y-%m-%d'),
        bisa_maju=bisa_maju, bulan_pilih=bulan_pilih, tahun_pilih=tahun_pilih,
        tanggal_halaman=tanggal_halaman, page=page, total_pages=total_pages,
    )


def direktur_reset_absensi():
    nama = request.form.get('nama')
    if nama == 'semua':
        reset_absensi_hari_ini()
        flash('Absensi hari ini untuk SEMUA orang berhasil direset!', 'success')
    else:
        reset_absensi_hari_ini(nama)
        flash(f'Absensi hari ini untuk {nama} berhasil direset!', 'success')
    return redirect(url_for('direktur_absensi'))


def direktur_penggajian_redirect():
    return redirect(url_for('direktur_bp.direktur_penggajian'))


def direktur_laporan():
    semua_laporan = get_laporan_untuk_direktur()

    today = datetime.now().date()
    bulan_pilih = request.args.get('bulan', type=int, default=today.month)
    tahun_pilih = request.args.get('tahun', type=int, default=today.year)

    daftar_laporan = [
        l for l in semua_laporan
        if l['tanggal_kirim'] and l['tanggal_kirim'].month == bulan_pilih and l['tanggal_kirim'].year == tahun_pilih
    ]

    tahun_tersedia = sorted({l['tanggal_kirim'].year for l in semua_laporan if l['tanggal_kirim']}, reverse=True) or [today.year]

    return render_template(
        'direktur/laporan.html', daftar_laporan=daftar_laporan,
        total_revisi=len([l for l in daftar_laporan if l['status_validasi'] == 'Revisi']),
        total_selesai=len([l for l in daftar_laporan if l['status_validasi'] == 'Disetujui']),
        total_proses=len([l for l in daftar_laporan if l['status_validasi'] == 'Menunggu Validasi Direktur']),
        bulan_pilih=bulan_pilih, tahun_pilih=tahun_pilih,
        tahun_tersedia=tahun_tersedia, nama_bulan=NAMA_BULAN,
    )


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
    today = datetime.now().date()
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
    today = datetime.now().date()
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
        today = datetime.now().date()
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