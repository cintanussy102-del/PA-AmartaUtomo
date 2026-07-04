def get_semua_data_gaji():
    return [
        {"id": 1, "nama": "Rony Parulian", "divisi": "Produksi", "total_gaji": 5800000, "status": "Terkirim", "email": "gloriakho5@gmail.com"},
        {"id": 2, "nama": "Siti Aminah", "divisi": "Administrasi", "total_gaji": 5050000, "status": "Belum", "email": "gloriakho5@gmail.com"}
    ]

def get_karyawan_by_id(id):
    for row in get_semua_data_gaji():
        if row['id'] == id: return row
    return None