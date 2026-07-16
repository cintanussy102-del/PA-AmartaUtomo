-- ============================================================
-- SCHEMA DATABASE: SISTEM KEPEGAWAIAN CV AMARTA UTOMO
-- ============================================================

-- ============================================================
-- TABEL: karyawan
-- Menyimpan data seluruh karyawan (termasuk Direktur & Admin)
-- ============================================================
CREATE TABLE karyawan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    nama_lengkap VARCHAR(150) NOT NULL,
    id_karyawan VARCHAR(20) NOT NULL UNIQUE,
    divisi VARCHAR(100) NOT NULL,
    jabatan VARCHAR(100),
    gaji_pokok DECIMAL(12,2) NOT NULL DEFAULT 0,
    tunjangan DECIMAL(12,2) NOT NULL DEFAULT 0,
    kontak VARCHAR(30),
    email VARCHAR(150),
    tanggal_bergabung DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Aktif',
    status_gaji VARCHAR(20) DEFAULT 'Belum'
);

-- ============================================================
-- TABEL: divisi
-- Master data divisi (nama, deskripsi tugas, kepala divisi)
-- ============================================================
CREATE TABLE divisi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100) NOT NULL UNIQUE,
    deskripsi TEXT,
    kepala_id INT NULL,
    status VARCHAR(20) DEFAULT 'Aktif',
    FOREIGN KEY (kepala_id) REFERENCES karyawan(id) ON DELETE SET NULL
);

-- ============================================================
-- TABEL: absensi
-- Riwayat absensi harian (Hadir/Sakit/Cuti/Izin Lainnya)
-- UNIQUE (nama_karyawan, tanggal) -> satu orang cuma 1 record per hari
-- ============================================================
CREATE TABLE absensi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_karyawan VARCHAR(50) NOT NULL,
    tanggal DATE NOT NULL,
    jam_masuk TIME NULL,
    jam_keluar TIME NULL,
    status VARCHAR(20) NOT NULL,           
    keterangan TEXT NULL,
    file_bukti VARCHAR(255) NULL,
    status_approval VARCHAR(20) DEFAULT 'Approved',  
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    alamat_absen VARCHAR(255) NULL,
    CONSTRAINT unique_nama_tanggal UNIQUE (nama_karyawan, tanggal)
);

-- ============================================================
-- TABEL: laporan_progres
-- Laporan kerja karyawan (submit -> validasi Direktur -> arsip Admin)
-- ============================================================
CREATE TABLE laporan_progres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_karyawan VARCHAR(50) NOT NULL,
    nama_proyek VARCHAR(150) NOT NULL,
    deskripsi_tugas TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Sedang Dikerjakan',  
    progres_manual INT NULL,             
    file_laporan VARCHAR(255),
    tanggal_kirim DATETIME DEFAULT CURRENT_TIMESTAMP,
    status_validasi VARCHAR(40) NOT NULL DEFAULT 'Menunggu Validasi Direktur',
    catatan_revisi TEXT NULL,
    tanggal_diteruskan DATETIME NULL,
    tanggal_validasi DATETIME NULL
);

-- ============================================================
-- TABEL: slip_gaji
-- Snapshot slip gaji per karyawan per bulan/tahun (dikirim Direktur)
-- UNIQUE (karyawan_id, bulan, tahun) -> 1 snapshot per periode, bisa di-update
-- ============================================================
CREATE TABLE slip_gaji (
    id INT AUTO_INCREMENT PRIMARY KEY,
    karyawan_id INT NOT NULL,
    bulan INT NOT NULL,
    tahun INT NOT NULL,
    gaji_pokok DECIMAL(12,2) NOT NULL,
    tunjangan DECIMAL(12,2) NOT NULL,
    total_penghasilan DECIMAL(12,2) NOT NULL,
    hadir INT DEFAULT 0,
    cuti INT DEFAULT 0,
    sakit INT DEFAULT 0,
    izin_lainnya INT DEFAULT 0,
    alpha INT DEFAULT 0,
    jumlah_hari_potong INT DEFAULT 0,
    total_potongan DECIMAL(12,2) DEFAULT 0,
    gaji_bersih DECIMAL(12,2) NOT NULL,
    tanggal_kirim DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (karyawan_id) REFERENCES karyawan(id) ON DELETE CASCADE,
    CONSTRAINT unique_karyawan_periode UNIQUE (karyawan_id, bulan, tahun)
);

-- ============================================================
-- INDEX TAMBAHAN (opsional, mempercepat query yang sering dipakai)
-- ============================================================
CREATE INDEX idx_absensi_tanggal ON absensi (tanggal);
CREATE INDEX idx_laporan_status_validasi ON laporan_progres (status_validasi);
CREATE INDEX idx_laporan_nama_karyawan ON laporan_progres (nama_karyawan);
CREATE INDEX idx_karyawan_divisi ON karyawan (divisi);

-- ============================================================
-- SEED DATA: DIVISI (deskripsi tugas per divisi)
-- ============================================================
INSERT INTO divisi (nama, deskripsi, status) VALUES
('Arsitektur', 'Bertanggung jawab atas desain gambar kerja proyek, review & revisi desain, serta survey lokasi proyek baru.', 'Aktif'),
('Marketing', 'Mengelola promosi unit perumahan, promosi & sewa kos-kosan, serta follow up klien/penyewa.', 'Aktif'),
('Logistik', 'Menangani pengadaan material proyek, distribusi material ke lokasi, dan maintenance fasilitas kos-kosan.', 'Aktif'),
('Pengawas Lapangan', 'Melakukan monitoring progres proyek konstruksi, pengecekan kualitas material/pekerjaan, dan inspeksi kondisi kos-kosan.', 'Aktif'),
('Direktur', 'Memimpin dan mengawasi seluruh operasional perusahaan.', 'Aktif'),
('Administrasi', 'Mengelola administrasi umum dan operasional kantor.', 'Aktif');