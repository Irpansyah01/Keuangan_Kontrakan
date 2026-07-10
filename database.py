import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "kontrakan.db")
BUKTI_DIR = os.path.join(BASE_DIR, "bukti_transfer")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(BUKTI_DIR, exist_ok=True)

def connect():
    return sqlite3.connect(DB_PATH)

def create_table():
    conn = connect()
    cursor = conn.cursor()
    
    # Tabel Pengeluaran
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pengeluaran(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT,
        barang TEXT,
        nominal INTEGER,
        dibayar_oleh TEXT
    )
    """)
    
    # Tabel Penyelesaian Hutang + Kolom Foto Bukti
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS penyelesaian_hutang(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dari_orang TEXT,
        ke_orang TEXT,
        jumlah INTEGER,
        status INTEGER DEFAULT 0,
        bukti_foto TEXT
    )
    """)
    conn.commit()
    conn.close()

def tambah_pengeluaran(tanggal, barang, nominal, dibayar_oleh):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pengeluaran (tanggal, barang, nominal, dibayar_oleh) VALUES (?, ?, ?, ?)", 
                   (tanggal, barang, nominal, dibayar_oleh))
    conn.commit()
    conn.close()

def ambil_semua_data():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pengeluaran ORDER BY tanggal DESC")
    data = cursor.fetchall()
    conn.close()
    return data

# --- FITUR BARU: FUNGSI HAPUS DATA YANG SALAH INPUT ---
def hapus_pengeluaran(id_data):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pengeluaran WHERE id=?", (id_data,))
    conn.commit()
    conn.close()

def ambil_penyelesaian():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM penyelesaian_hutang")
    data = cursor.fetchall()
    conn.close()
    return data

def update_status_hutang(id_transaksi, status, nama_file_foto=None):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE penyelesaian_hutang SET status=?, bukti_foto=? WHERE id=?", (status, nama_file_foto, id_transaksi))
    conn.commit()
    conn.close()

def sinkronisasi_hutang(daftar_baru):
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT dari_orang, ke_orang, jumlah, status, bukti_foto FROM penyelesaian_hutang")
    lama = cursor.fetchall()
    status_dict = {(x[0], x[1], x[2]): (x[3], x[4]) for x in lama}
    
    cursor.execute("DELETE FROM penyelesaian_hutang")
    
    for t in daftar_baru:
        kunci = (t["dari"], t["ke"], t["jumlah"])
        status_aktif, foto_aktif = status_dict.get(kunci, (0, None))
        cursor.execute("INSERT INTO penyelesaian_hutang (dari_orang, ke_orang, jumlah, status, bukti_foto) VALUES (?, ?, ?, ?, ?)",
                       (t["dari"], t["ke"], t["jumlah"], status_aktif, foto_aktif))
    conn.commit()
    conn.close()

create_table()
