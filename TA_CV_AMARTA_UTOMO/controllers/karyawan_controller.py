import os
import calendar
import cloudinary.uploader

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta, date

from utils import allowed_file, get_jabatan_tampilan, TUGAS_PER_DIVISI

from models.karyawan_model import get_karyawan_by_username, get_profil_gaji
from models.absensi_model import (
    get_riwayat_absensi, get_riwayat_absensi_bulan, get_status_hari_ini,
    catat_absen_masuk, catat_absen_keluar, ajukan_izin,
    hitung_durasi_kerja, get_rekap_bulanan
)
from models.progres_model import (
    ajukan_laporan, get_ringkasan_laporan, kirim_ulang_laporan, get_progres_tugas_karyawan
)
from models.gaji_model import get_slip_gaji, get_semua_bulan_tersedia, NAMA_BULAN


def karyawan_dashboard():
    nama_user = session['user']['username']
    karyawan = get_karyawan_by_username(nama_user)
    riwayat = get_riwayat_absensi(nama_user, limit=3)
    rekap = get_rekap_bulanan(nama_user)

    daftar_tugas = TUGAS_PER_DIVISI.get(karyawan['divisi'], []) if karyawan else []
    progres_tugas = get_progres_tugas_karyawan(nama_user, daftar_tugas)
    progres_rata = round(sum(t['progres'] for t in progres_tugas) / len(progres_tugas)) if progres_tugas else 0

    data = {
        "hari_hadir": rekap.get('Hadir', 0),
        "izin": rekap.get('Cuti', 0) + rekap.get('Izin Lainnya', 0) + rekap.get('Sakit', 0),
        "gaji": float(karyawan['gaji_pokok']) if karyawan else 0,
        "progres": progres_rata,
    }

    today = datetime.now()
    tanggal_terakhir = calendar.monthrange(today.year, today.month)[1]
    batas_laporan = f"{tanggal_terakhir} {NAMA_BULAN[today.month]} {today.year}"

    return render_template('karyawan/dashboard.html', data=data, riwayat=riwayat, progres_tugas=progres_tugas, batas_laporan=batas_laporan)


def karyawan_absensi():
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
        'karyawan/absensi.html', riwayat=riwayat, status_hari_ini=status_hari_ini,
        durasi_kerja=durasi_kerja, rekap=rekap, bulan_pilih=bulan_pilih,
        tahun_pilih=tahun_pilih, nama_bulan=NAMA_BULAN
    )


def karyawan_absen_masuk():
    catat_absen_masuk(session['user']['username'])
    flash('Absen masuk berhasil dicatat!', 'success')
    return redirect(url_for('karyawan_absensi'))


def karyawan_absen_keluar():
    catat_absen_keluar(session['user']['username'])
    flash('Absen keluar berhasil dicatat!', 'success')
    return redirect(url_for('karyawan_absensi'))


def karyawan_ajukan_izin(upload_folder):
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
        
        print("Nama file:", file_bukti.filename)
        print("Content Type:", file_bukti.content_type)
                
        try:
            hasil_upload = cloudinary.uploader.upload(
                file_bukti,
                folder="bukti_izin"
            )

            file_bukti_path = hasil_upload["secure_url"]

        except Exception as e:
            flash(f"Gagal upload ke Cloudinary: {e}", "danger")
            return redirect(url_for("karyawan_absensi"))
        
    ajukan_izin(nama_user, jenis_izin, tanggal, keterangan, file_bukti_path)
    flash('Pengajuan izin/cuti berhasil dikirim!', 'success')
    return redirect(url_for('karyawan_absensi'))

def karyawan_input_progres():
    nama_user = session['user']['username']
    profil = get_profil_gaji(nama_user)
    ringkasan = get_ringkasan_laporan(nama_user)
    daftar_tugas = TUGAS_PER_DIVISI.get(profil['divisi'], [])
    return render_template('karyawan/input_progres.html', profil=profil, ringkasan=ringkasan, daftar_tugas=daftar_tugas)


def karyawan_kirim_laporan(upload_folder_laporan):
    nama_user = session['user']['username']
    nama_proyek = request.form.get('id_pekerjaan')
    deskripsi = request.form.get('tugas_pekerjaan')
    status = request.form.get('status_tugas')
    progres_manual = request.form.get('progres_manual')
    progres_manual = int(progres_manual) if progres_manual else None

    file_laporan = request.files.get('file_laporan')
    print("======================")
    print("Nama File :", file_laporan.filename)
    print("Content Type :", file_laporan.content_type)
    print("======================")

    if not file_laporan or file_laporan.filename == '':
        flash('File laporan (PDF) wajib diunggah!', 'danger')
        return redirect(url_for('karyawan_input_progres'))
    if not file_laporan.filename.lower().endswith('.pdf'):
        flash('File laporan harus berformat PDF.', 'danger')
        return redirect(url_for('karyawan_input_progres'))

    try:
        hasil_upload = cloudinary.uploader.upload(
            file_laporan,
            resource_type="raw",
            folder="laporan_kerja",
            public_id=f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        file_path = hasil_upload["secure_url"]

        print("UPLOAD BERHASIL")
        print(file_path)

    except Exception as e:
        flash(f"Gagal upload ke Cloudinary: {e}", "danger")
        return redirect(url_for("karyawan_input_progres"))

    ajukan_laporan(
        nama_user,
        nama_proyek,
        deskripsi,
        status,
        progres_manual,
        file_path
    )

    flash("Laporan kerja berhasil dikirim!", "success")
    return redirect(url_for("karyawan_input_progres"))

def karyawan_kirim_ulang_laporan(id, upload_folder_laporan):
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

    try:
        hasil_upload = cloudinary.uploader.upload(
            file_laporan,
            resource_type="raw",
            folder="laporan_kerja",
            public_id=f"{nama_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )


    except Exception as e:
        flash(f"Gagal upload ke Cloudinary: {e}", "danger")
        return redirect(url_for("karyawan_input_progres"))

    file_path = hasil_upload["secure_url"]

    kirim_ulang_laporan(
        id,
        nama_user,
        deskripsi,
        status,
        progres_manual,
        file_path
    )

    flash("Laporan revisi berhasil dikirim ulang untuk ditinjau!", "success")
    return redirect(url_for("karyawan_input_progres"))

def karyawan_slip_gaji():
    nama_user = session['user']['username']
    karyawan = get_karyawan_by_username(nama_user)
    if not karyawan:
        flash('Data karyawan tidak ditemukan!', 'danger')
        return redirect(url_for('karyawan_dashboard'))

    karyawan['jabatan'] = get_jabatan_tampilan(karyawan['id'], karyawan['divisi'])
    today = datetime.now()
    bulan_dipilih = int(request.args.get('bulan', today.month))
    tahun_dipilih = int(request.args.get('tahun', today.year))

    slip = get_slip_gaji(karyawan['id'], bulan_dipilih, tahun_dipilih)
    daftar_bulan = get_semua_bulan_tersedia(karyawan['id'])

    return render_template(
        'karyawan/slip_gaji.html', profil=karyawan, slip=slip,
        bulan_dipilih=bulan_dipilih, tahun_dipilih=tahun_dipilih,
        daftar_bulan=daftar_bulan, nama_bulan=NAMA_BULAN
    )


# --- API JSON absensi (dipanggil dari JS) ---
def proses_absen_masuk():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"}), 401
    data = request.json or {}
    nama = session['user']['username']
    hasil = catat_absen_masuk(nama, data.get('lat'), data.get('lon'), data.get('alamat'))
    return jsonify(hasil)


def proses_absen_keluar():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"}), 401
    nama = session['user']['username']
    catat_absen_keluar(nama)
    status = get_status_hari_ini(nama)
    durasi = hitung_durasi_kerja(status['masuk'], status['keluar']) if status else '-'
    return jsonify({"jam_keluar": status['keluar'] if status else '-', "durasi_kerja": durasi})