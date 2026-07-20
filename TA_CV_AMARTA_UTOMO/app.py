import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from utils import login_required

from controllers import auth_controller, admin_controller, karyawan_controller, direktur_controller
from controllers.direktur_controller import direktur_bp

app = Flask(
    __name__,
    template_folder=os.path.join('views', 'templates'),
    static_folder=os.path.join('views', 'static')
)

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

@app.template_filter('rupiah')
def format_rupiah(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

app.register_blueprint(direktur_bp)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key_amarta')

UPLOAD_FOLDER = os.path.join('views', 'static', 'uploads', 'bukti_izin')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

UPLOAD_FOLDER_LAPORAN = os.path.join('views', 'static', 'uploads', 'laporan_kerja')
os.makedirs(UPLOAD_FOLDER_LAPORAN, exist_ok=True)
app.config['UPLOAD_FOLDER_LAPORAN'] = UPLOAD_FOLDER_LAPORAN

debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
server_port = int(os.getenv('FLASK_PORT', 5000))

# ============================================================
# ROUTING — Semua logic ada di controllers/, app.py cuma daftar rute
# ============================================================

app.add_url_rule('/', 'welcome', auth_controller.welcome)
app.add_url_rule('/login', 'login', auth_controller.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', auth_controller.logout)

# --- ADMIN ---
app.add_url_rule('/admin/dashboard', 'admin_dashboard', login_required(role='admin')(admin_controller.admin_dashboard))
app.add_url_rule('/admin/data-karyawan', 'admin_data_karyawan', login_required(role='admin')(admin_controller.admin_data_karyawan))
app.add_url_rule('/admin/data-karyawan/tambah', 'admin_tambah_karyawan', login_required(role='admin')(admin_controller.admin_tambah_karyawan), methods=['POST'])
app.add_url_rule('/admin/data-karyawan/edit/<int:id>', 'admin_edit_karyawan', login_required(role='admin')(admin_controller.admin_edit_karyawan), methods=['GET', 'POST'])
app.add_url_rule('/admin/data-karyawan/hapus/<int:id>', 'admin_hapus_karyawan', login_required(role='admin')(admin_controller.admin_hapus_karyawan), methods=['POST'])
app.add_url_rule('/admin/absensi', 'admin_absensi', login_required(role='admin')(admin_controller.admin_absensi))
app.add_url_rule('/admin/ajukan-izin', 'admin_ajukan_izin', login_required(role='admin')(lambda: admin_controller.admin_ajukan_izin(UPLOAD_FOLDER)), methods=['POST'])
app.add_url_rule('/admin/divisi', 'admin_divisi', login_required(role='admin')(admin_controller.admin_divisi))
app.add_url_rule('/admin/divisi/tambah', 'admin_tambah_divisi', login_required(role='admin')(admin_controller.admin_tambah_divisi), methods=['POST'])
app.add_url_rule('/admin/divisi/edit/<int:id>', 'admin_edit_divisi', login_required(role='admin')(admin_controller.admin_edit_divisi), methods=['POST'])
app.add_url_rule('/admin/divisi/hapus/<int:id>', 'admin_hapus_divisi', login_required(role='admin')(admin_controller.admin_hapus_divisi), methods=['POST'])
app.add_url_rule('/admin/rekap-laporan', 'admin_rekap_laporan', login_required(role='admin')(admin_controller.admin_rekap_laporan))
app.add_url_rule('/admin/teruskan-laporan/<int:id>', 'admin_teruskan_laporan', login_required(role='admin')(admin_controller.admin_teruskan_laporan), methods=['POST'])
app.add_url_rule('/admin/slip-gaji', 'admin_slip_gaji', login_required(role='admin')(admin_controller.admin_slip_gaji))

# --- KARYAWAN ---
app.add_url_rule('/karyawan/dashboard', 'karyawan_dashboard', login_required(role='karyawan')(karyawan_controller.karyawan_dashboard))
app.add_url_rule('/karyawan/absensi', 'karyawan_absensi', login_required(role='karyawan')(karyawan_controller.karyawan_absensi))
app.add_url_rule('/karyawan/absen-masuk', 'karyawan_absen_masuk', login_required(role='karyawan')(karyawan_controller.karyawan_absen_masuk), methods=['POST'])
app.add_url_rule('/karyawan/absen-keluar', 'karyawan_absen_keluar', login_required(role='karyawan')(karyawan_controller.karyawan_absen_keluar), methods=['POST'])
app.add_url_rule('/karyawan/ajukan-izin', 'karyawan_ajukan_izin', login_required(role='karyawan')(lambda: karyawan_controller.karyawan_ajukan_izin(UPLOAD_FOLDER)), methods=['POST'])
app.add_url_rule('/karyawan/input-progres', 'karyawan_input_progres', login_required(role='karyawan')(karyawan_controller.karyawan_input_progres))
app.add_url_rule('/karyawan/kirim-laporan', 'karyawan_kirim_laporan', login_required(role='karyawan')(lambda: karyawan_controller.karyawan_kirim_laporan(UPLOAD_FOLDER_LAPORAN)), methods=['POST'])
app.add_url_rule('/karyawan/kirim-ulang-laporan/<int:id>', 'karyawan_kirim_ulang_laporan', login_required(role='karyawan')(lambda id: karyawan_controller.karyawan_kirim_ulang_laporan(id, UPLOAD_FOLDER_LAPORAN)), methods=['POST'])
app.add_url_rule('/karyawan/slip-gaji', 'karyawan_slip_gaji', login_required(role='karyawan')(karyawan_controller.karyawan_slip_gaji))
app.add_url_rule('/proses-absen-masuk', 'proses_absen_masuk', karyawan_controller.proses_absen_masuk, methods=['POST'])
app.add_url_rule('/proses-absen-keluar', 'proses_absen_keluar', karyawan_controller.proses_absen_keluar, methods=['POST'])

# --- DIREKTUR ---
app.add_url_rule('/direktur/dashboard', 'direktur_dashboard', login_required(role='direktur')(direktur_controller.direktur_dashboard))
app.add_url_rule('/direktur/monitoring', 'direktur_monitoring', login_required(role='direktur')(direktur_controller.direktur_monitoring))
app.add_url_rule('/direktur/absensi', 'direktur_absensi', login_required(role='direktur')(direktur_controller.direktur_absensi))
app.add_url_rule('/direktur/reset-absensi', 'direktur_reset_absensi', login_required(role='direktur')(direktur_controller.direktur_reset_absensi), methods=['POST'])
app.add_url_rule('/direktur/penggajian', 'direktur_penggajian', login_required(role='direktur')(direktur_controller.direktur_penggajian_redirect))
app.add_url_rule('/direktur/validasi-gaji', 'direktur_validasi_gaji', login_required(role='direktur')(direktur_controller.direktur_penggajian_redirect))
app.add_url_rule('/direktur/laporan', 'direktur_laporan', login_required(role='direktur')(direktur_controller.direktur_laporan))
app.add_url_rule('/direktur/validasi-laporan/<int:id>', 'direktur_validasi_laporan', login_required(role='direktur')(direktur_controller.direktur_validasi_laporan), methods=['POST'])

if __name__ == '__main__':
    app.run(debug=debug_mode, port=server_port)