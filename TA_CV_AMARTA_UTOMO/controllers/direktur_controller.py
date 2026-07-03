# Pastikan Anda mengimpor render_template di bagian atas file
from flask import Blueprint, render_template

direktur_bp = Blueprint('direktur_bp', __name__)

@direktur_bp.route('/direktur/absensi')
def direktur_absensi():
    return render_template('direktur/absensi.html')

@direktur_bp.route('/direktur/penggajian')
def direktur_penggajian():
    return render_template('direktur/penggajian.html')

@direktur_bp.route('/direktur/laporan')
def direktur_laporan():
    return render_template('direktur/laporan.html')