import os
import json
import mysql.connector
import certifi
from dotenv import load_dotenv

# Memuat file .env saat aplikasi berjalan
load_dotenv()

class Database:
    _connection = None

    @classmethod
    def get_connection(cls):
        """Membuat koneksi tunggal ke TiDB Cloud dengan membaca Railway Variables langsung."""
        if cls._connection is None or not cls._connection.is_connected():
            try:
                # Kita langsung ambil dari os.getenv() dengan nama variabel yang konsisten
                cls._connection = mysql.connector.connect(
                    host=os.getenv('DB_HOST'),      # Pastikan di Railway Variables namanya DB_HOST
                    user=os.getenv('DB_USER'),      # Pastikan di Railway Variables namanya DB_USER
                    password=os.getenv('DB_PASSWORD'),
                    database=os.getenv('DB_NAME'),
                    port=int(os.getenv('DB_PORT', 4000)),
                    ssl_ca=certifi.where(),
                    ssl_verify_cert=True
                )
                print("[SUCCESS] Berhasil terhubung ke database!")
            except Exception as e:
                print(f"[ERROR] Gagal menyambungkan: {str(e)}")
                cls._connection = None
        return cls._connection

    @classmethod
    def execute_query(cls, query, params=None):
        conn = cls.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            conn.commit()
            cursor.close()
            return True
        return False

    @classmethod
    def fetch_all(cls, query, params=None):
        conn = cls.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        return []