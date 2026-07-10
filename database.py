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
                foto TEXT DEFAULT ''
            )
        ''')
        
        # Jembatan pengaman otomatis jika database lama kehilangan kolom foto
        try:
            cursor.execute("ALTER TABLE penyelesaian_hutang ADD COLUMN foto TEXT DEFAULT ''")
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

# FIX: Menggunakan 'is not None' agar string kosong ("") untuk hapus foto saat batal lunas tetap diproses
def update_status(id_transaksi, status, link_foto=None):
    conn = connect()
    cursor = conn.cursor()
    if link_foto is not None:
        cursor.execute("UPDATE penyelesaian_hutang SET status=?, foto=? WHERE id=?", (status, link_foto, id_transaksi))
    else:
        cursor.execute("UPDATE penyelesaian_hutang SET status=? WHERE id=?", (status, id_transaksi))
    conn.commit()
    conn.close()

# FIX: Ditambahkan penanganan drop table otomatis jika struktur database bawaan server terlanjur rusak parah
def sinkronisasi_hutang(daftar_baru):
    conn = connect()
    cursor = conn.cursor()
    
    # 1. Ambil data lama yang sudah terlanjur LUNAS (status = 1) agar tidak terhapus
    try:
        cursor.execute("SELECT dari, ke, jumlah, foto FROM penyelesaian_hutang WHERE status = 1")
        lunas_lama = cursor.fetchall()
        set_lunas = {(x[0], x[1], x[2]): x[3] for x in lunas_lama}
    except sqlite3.OperationalError:
        set_lunas = {}

    # 2. Hapus tabel lama, tapi kita bangun ulang dengan memisahkan mana yang benar-benar belum bayar
    try:
        cursor.execute("DELETE FROM penyelesaian_hutang")
        
        for t in daftar_baru:
            kunci = (t["dari"], t["ke"], t["jumlah"])
            
            # Jika transaksi ini di memori database ternyata SUDAH LUNAS, pertahankan status lunasnya!
            if kunci in set_lunas:
                cursor.execute("INSERT INTO penyelesaian_hutang (dari, ke, jumlah, status, foto) VALUES (?, ?, ?, ?, ?)",
                               (t["dari"], t["ke"], t["jumlah"], 1, set_lunas[kunci]))
            else:
                cursor.execute("INSERT INTO penyelesaian_hutang (dari, ke, jumlah, status, foto) VALUES (?, ?, ?, ?, ?)",
                               (t["dari"], t["ke"], t["jumlah"], 0, ""))
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()
# Jalankan pemeriksaan awal
create_table()
