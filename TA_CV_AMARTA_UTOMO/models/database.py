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
        """Membuat koneksi tunggal ke TiDB Cloud dengan membaca Environment Variables."""
        if cls._connection is None or not cls._connection.is_connected():
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_path = os.path.join(base_dir, 'config', 'config.json')
                
                with open(config_path, 'r') as config_file:
                    config = json.load(config_file)
                
                db_config = config['database']
                
                # Mengambil nilai asli dari file .env menggunakan os.getenv()
                cls._connection = mysql.connector.connect(
                    host=os.getenv(db_config['host']),
                    user=os.getenv(db_config['user']),
                    password=os.getenv(db_config['password']),
                    database=os.getenv(db_config['database_name']),
                    port=int(os.getenv(db_config['port'], 4000)),
                    ssl_ca=certifi.where(),
                    ssl_verify_cert=True
                )
                print("[SUCCESS] Berhasil terhubung ke TiDB Cloud Online secara aman via .env.")
            except Exception as e:
                print(f"[ERROR] Gagal menyambungkan ke TiDB Cloud: {str(e)}")
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