DATA_GAJI = [
    {"id": 1, "nama": "Rony Parulian", "divisi": "Produksi", "total_gaji": 5800000, "status": "Belum", "email": "gloriakho5@gmail.com"},
    {"id": 2, "nama": "Aloysius Setiawan", "divisi": "Pengawas Lapangan", "total_gaji": 4500000, "status": "Belum", "email": "gloriakho5@gmail.com"},
    {"id": 3, "nama": "Putri Ayu Lestari", "divisi": "Administrasi", "total_gaji": 3000000, "status": "Belum", "email": "gloriakho5@gmail.com"}
]


def get_semua_data_gaji():
    return DATA_GAJI


def update_status_gaji(id, status_baru):
    for row in DATA_GAJI:
        if row['id'] == id:
            row['status'] = status_baru
            return True
    return False


def get_karyawan_by_id(id):
    for row in get_semua_data_gaji():
        if row['id'] == id: 
            return row
    return None

def get_data_karyawan_by_name(nama):
    # Contoh data, silakan sesuaikan angkanya
    data_karyawan = {
        "Rony": {"hari_hadir": 29, "izin": 1, "gaji": 5800000, "progres": 90},
        "Aloy": {"hari_hadir": 20, "izin": 2, "gaji": 4500000, "progres": 60},
        "Putri": {"hari_hadir": 10, "izin": 3, "gaji": 3000000, "progres": 30}
    }
    return data_karyawan.get(nama, {"hari_hadir": 0, "izin": 0, "gaji": 0, "progres": 0})

def get_profil_gaji(nama):
    data_gaji = {
        "Rony": {
            "nama_lengkap": "Rony Parulian",
            "id_karyawan": "KRY-0042",
            "jabatan": "Staff Produksi",
            "divisi": "Konstruksi",
            "gaji_pokok": 4500000,
            "tunjangan": 500000,
        },
        "Aloy": {
            "nama_lengkap": "Aloysius Setiawan",
            "id_karyawan": "KRY-0043",
            "jabatan": "Pengawas Lapangan",
            "divisi": "Konstruksi",
            "gaji_pokok": 4200000,
            "tunjangan": 400000,
        },
        "Putri": {
            "nama_lengkap": "Putri Ayu Lestari",
            "id_karyawan": "KRY-0044",
            "jabatan": "Staff Administrasi",
            "divisi": "Administrasi",
            "gaji_pokok": 4000000,
            "tunjangan": 350000,
        },
    }
    return data_gaji.get(nama, {
        "nama_lengkap": nama,
        "id_karyawan": "-",
        "jabatan": "-",
        "divisi": "-",
        "gaji_pokok": 0,
        "tunjangan": 0,
    })