import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "kontrakan.db")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

def connect():
    return sqlite3.connect(DB_PATH)

def create_table():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 1. Pastikan tabel pengeluaran aman
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pengeluaran (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT,
                barang TEXT,
                nominal REAL,
                dibayar_oleh TEXT
            )
        ''')
        # 2. Pastikan tabel penyelesaian_hutang punya struktur kolom yang konsisten
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penyelesaian_hutang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dari TEXT,
                ke TEXT,
                jumlah INTEGER,
                status INTEGER DEFAULT 0,
                foto TEXT
            )
        ''')
        
        # Jembatan pengaman jika database lama belum memiliki kolom foto
        try:
            cursor.execute("ALTER TABLE penyelesaian_hutang ADD COLUMN foto TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()

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

# FUNGSI UPDATE STATUS YANG SUDAH DISINKRONKAN NAMA KOLOMNYA
def update_status(id_transaksi, status, link_foto=None):
    conn = connect()
    cursor = conn.cursor()
    if link_foto:
        cursor.execute("UPDATE penyelesaian_hutang SET status=?, foto=? WHERE id=?", (status, link_foto, id_transaksi))
    else:
        cursor.execute("UPDATE penyelesaian_hutang SET status=? WHERE id=?", (status, id_transaksi))
    conn.commit()
    conn.close()

# FUNGSI SINKRONISASI YANG SUDAH DI-FIX (MENGGUNAKAN NAMA KOLOM DARI, KE, JUMALH, STATUS, FOTO)
def sinkronisasi_hutang(daftar_baru):
    conn = connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT dari, ke, jumlah, status, foto FROM penyelesaian_hutang")
        lama = cursor.fetchall()
        status_dict = {(x[0], x[1], x[2]): (x[3], x[4]) for x in lama}
    except sqlite3.OperationalError:
        status_dict = {}
        
    cursor.execute("DELETE FROM penyelesaian_hutang")
    
    for t in daftar_baru:
        kunci = (t["dari"], t["ke"], t["jumlah"])
        status_aktif, foto_aktif = status_dict.get(kunci, (0, None))
        cursor.execute("INSERT INTO penyelesaian_hutang (dari, ke, jumlah, status, foto) VALUES (?, ?, ?, ?, ?)",
                       (t["dari"], t["ke"], t["jumlah"], status_aktif, foto_aktif))
    conn.commit()
    conn.close()

# Jalankan pembuatan/pemeriksaan tabel saat file ini diimpor
create_table()
