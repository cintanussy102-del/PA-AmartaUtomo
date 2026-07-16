import os
from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename

from utils import allowed_file, get_jabatan_tampilan, build_laporan_progres_dashboard

from models.karyawan_model import (
    get_semua_karyawan, get_karyawan_by_id, tambah_karyawan,
    update_karyawan, hapus_karyawan, get_karyawan_by_username,
    get_total_karyawan_aktif, get_karyawan_terbaru
)
from models.absensi_model import (
    get_riwayat_absensi_bulan, get_status_hari_ini, hitung_durasi_kerja,
    get_rekap_bulanan, ajukan_izin
)
from models.progres_model import get_semua_laporan_admin, teruskan_ke_direktur
from models.divisi_model import (
    get_semua_divisi_dengan_jumlah, get_jumlah_divisi_aktif,
    get_semua_divisi, get_anggota_divisi, tambah_divisi, update_divisi, hapus_divisi
)
from models.gaji_model import get_slip_gaji, get_semua_bulan_tersedia, NAMA_BULAN


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


def admin_data_karyawan():
    daftar_karyawan = get_semua_karyawan()
    total = len(daftar_karyawan)
    aktif = len([k for k in daftar_karyawan if k['status'] == 'Aktif'])
    izin_cuti = len([k for k in daftar_karyawan if k['status'] != 'Aktif'])
    return render_template('admin/data_karyawan.html', daftar_karyawan=daftar_karyawan, total=total, aktif=aktif, izin_cuti=izin_cuti)


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


def admin_hapus_karyawan(id):
    hapus_karyawan(id)
    flash('Data karyawan berhasil dihapus!', 'success')
    return redirect(url_for('admin_data_karyawan'))


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
        riwayat=riwayat, status_hari_ini=status_hari_ini, durasi_kerja=durasi_kerja,
        rekap=rekap, bulan_pilih=bulan_pilih, tahun_pilih=tahun_pilih, nama_bulan=NAMA_BULAN
    )


def admin_ajukan_izin(upload_folder):
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
        file_bukti.save(os.path.join(upload_folder, filename))
        file_bukti_path = f"uploads/bukti_izin/{filename}"

    ajukan_izin(nama_user, jenis_izin, tanggal, keterangan, file_bukti_path)
    flash('Pengajuan izin/cuti berhasil dikirim!', 'success')
    return redirect(url_for('admin_absensi'))


def admin_divisi():
    divisi_list = get_semua_divisi()
    for d in divisi_list:
        d['anggota'] = get_anggota_divisi(d['nama'])
    total_karyawan = sum(d['jumlah_karyawan'] for d in divisi_list)
    semua_karyawan = get_semua_karyawan()
    return render_template('admin/divisi.html', divisi_list=divisi_list, total_karyawan=total_karyawan, semua_karyawan=semua_karyawan)


def admin_tambah_divisi():
    tambah_divisi(request.form.get('nama'), request.form.get('deskripsi'))
    flash('Divisi baru berhasil ditambahkan!', 'success')
    return redirect(url_for('admin_divisi'))


def admin_edit_divisi(id):
    update_divisi(id, request.form.get('nama'), request.form.get('deskripsi'),
                  request.form.get('kepala_id') or None, request.form.get('status', 'Aktif'))
    flash('Data divisi berhasil diperbarui!', 'success')
    return redirect(url_for('admin_divisi'))


def admin_hapus_divisi(id):
    berhasil, pesan = hapus_divisi(id)
    flash(pesan, 'success' if berhasil else 'danger')
    return redirect(url_for('admin_divisi'))


def admin_rekap_laporan():
    semua = get_semua_laporan_admin()
    disetujui = [l for l in semua if l['status_validasi'] == 'Disetujui']

    bulan_pilih = request.args.get('bulan', type=int)
    tahun_pilih = request.args.get('tahun', type=int)

    if bulan_pilih and tahun_pilih:
        disetujui = [l for l in disetujui if l['tanggal_validasi'] and l['tanggal_validasi'].month == bulan_pilih and l['tanggal_validasi'].year == tahun_pilih]

    per_divisi = {}
    for l in disetujui:
        per_divisi.setdefault(l['divisi'] or 'Tanpa Divisi', []).append(l)

    tahun_tersedia = sorted({l['tanggal_validasi'].year for l in semua if l['status_validasi'] == 'Disetujui' and l['tanggal_validasi']}, reverse=True) or [datetime.now().year]

    return render_template(
        'admin/rekap_laporan.html', per_divisi=per_divisi, total_laporan=len(disetujui),
        total_divisi=len(per_divisi), bulan_pilih=bulan_pilih, tahun_pilih=tahun_pilih,
        tahun_tersedia=tahun_tersedia, nama_bulan=NAMA_BULAN
    )


def admin_teruskan_laporan(id):
    teruskan_ke_direktur(id)
    flash('Laporan berhasil diteruskan ke Direktur untuk divalidasi.', 'success')
    return redirect(url_for('admin_rekap_laporan'))


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
        'admin/slip_gaji.html', profil=admin_data, slip=slip,
        bulan_dipilih=bulan_dipilih, tahun_dipilih=tahun_dipilih,
        daftar_bulan=daftar_bulan, nama_bulan=NAMA_BULAN
    )