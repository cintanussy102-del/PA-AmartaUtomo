from flask import render_template, request, redirect, url_for, session, flash
from models.karyawan_model import get_karyawan_by_divisi_dan_username

DIVISI_LOGIN_MAP = {
    'Arsitektur': 'Arsitektur',
    'Marketing': 'Marketing',
    'Logistik': 'Logistik',
    'Pengawas': 'Pengawas Lapangan',
}


def welcome():
    return render_template('welcome.html')


def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        pesan_gagal = 'Username atau Password Salah!'

        if username == 'Admin':
            if password == 'Glory':
                session['user'] = {'username': 'admin', 'nama_lengkap': 'Glory', 'role': 'admin'}
                return redirect(url_for('admin_dashboard'))
            flash(pesan_gagal, 'danger')
            return redirect(url_for('login'))

        elif username == 'Direktur':
            if password == 'Gloria':
                session['user'] = {'username': 'direktur', 'nama_lengkap': 'Gloria', 'role': 'direktur'}
                return redirect(url_for('direktur_dashboard'))
            flash(pesan_gagal, 'danger')
            return redirect(url_for('login'))

        elif username in DIVISI_LOGIN_MAP:
            divisi_asli = DIVISI_LOGIN_MAP[username]
            karyawan = get_karyawan_by_divisi_dan_username(divisi_asli, password)
            if karyawan:
                session['user'] = {
                    'username': karyawan['username'],
                    'nama_lengkap': karyawan['nama_lengkap'],
                    'role': 'karyawan'
                }
                return redirect(url_for('karyawan_dashboard'))
            flash(pesan_gagal, 'danger')
            return redirect(url_for('login'))

        else:
            flash(pesan_gagal, 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


def logout():
    session.clear()
    return redirect(url_for('login'))