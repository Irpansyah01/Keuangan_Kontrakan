import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# MENGGANTI NAMA FILE JADI KONTRAKAN_FINAL AGAR DATABASE YANG RUSAK/KORUP TERBUANG
DB_PATH = os.path.join(BASE_DIR, "data", "kontrakan_final.db")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

def connect():
    # check_same_thread=False wajib di Streamlit agar database tidak bentrok antar-user/halaman
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_table():
    with connect() as conn:
        cursor = conn.cursor()
        # 1. Tabel pengeluaran
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pengeluaran (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT,
                barang TEXT,
                nominal REAL,
                dibayar_oleh TEXT
            )
        ''')
        # 2. Tabel penyelesaian
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penyelesaian_hutang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dari TEXT,
                ke TEXT,
                jumlah INTEGER,
                status INTEGER DEFAULT 0
            )
        ''')
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

def update_status(id_transaksi, status):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE penyelesaian_hutang SET status=? WHERE id=?", (status, id_transaksi))
    conn.commit()
    conn.close()

def sinkronisasi_hutang(daftar_baru):
    conn = connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT dari, ke, jumlah FROM penyelesaian_hutang WHERE status = 1")
        lunas_lama = cursor.fetchall()
        set_lunas = {(x[0], x[1], x[2]) for x in lunas_lama}
    except sqlite3.OperationalError:
        set_lunas = set()

    try:
        cursor.execute("DELETE FROM penyelesaian_hutang")
        for t in daftar_baru:
            kunci = (t["dari"], t["ke"], t["jumlah"])
            if kunci in set_lunas:
                cursor.execute("INSERT INTO penyelesaian_hutang (dari, ke, jumlah, status) VALUES (?, ?, ?, 1)",
                               (t["dari"], t["ke"], t["jumlah"]))
            else:
                cursor.execute("INSERT INTO penyelesaian_hutang (dari, ke, jumlah, status) VALUES (?, ?, ?, 0)",
                               (t["dari"], t["ke"], t["jumlah"]))
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

create_table()
