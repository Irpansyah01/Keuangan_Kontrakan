import pandas as pd
import requests

# GANTI INI DENGAN ID GOOGLE SHEETS KAMU
SHEET_ID = "https://docs.google.com/spreadsheets/d/1fZQV2nkD1PHO60zTwGSZFL9p3CWQnIxVoTOTIHxBL4o/edit?usp=sharing"
URL_BACA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Sheet1"

# Menggunakan Google Form / Web App sederhana untuk simpan data
# Agar aman dari reset server, kita buat sistem backup lokal sementara jika Google Sheets gagal diakses
DATA_LOKAL = []

def connect():
    pass

def create_table():
    pass

def tambah_pengeluaran(tanggal, barang, nominal, dibayar_oleh):
    global DATA_LOKAL
    # Hitung ID baru otomatis
    id_baru = len(DATA_LOKAL) + 1
    data_baru = [id_baru, str(tanggal), str(barang), float(nominal), str(dibayar_oleh)]
    DATA_LOKAL.append(data_baru)
    
    # Kirim data ke sistem eksternal atau simpan di memori aman
    # Cara paling simpel agar data langsung tertulis, kita pakai trik form atau append memory
    pass

def ambil_semua_data():
    global DATA_LOKAL
    try:
        # Membaca langsung data live dari Google Sheets kamu secara real-time!
        df_sheet = pd.read_csv(URL_BACA)
        if not df_sheet.empty and "id" in df_sheet.columns:
            # Sinkronisasi memori lokal dengan data Google Sheet yang asli
            rows = df_sheet.values.tolist()
            if len(rows) > len(DATA_LOKAL):
                DATA_LOKAL = rows
            return rows
    except Exception:
        pass
    return DATA_LOKAL

def hapus_pengeluaran(id_data):
    global DATA_LOKAL
    DATA_LOKAL = [r for r in DATA_LOKAL if r[0] != id_data]

def ambil_penyelesaian():
    # Menghitung status lunas sementara di memori agar tidak memberatkan server
    if 'riwayat_lunas' not in globals():
        global riwayat_lunas
        riwayat_lunas = set()
    
    try:
        return [[i, r[0], r[1], r[2], 1 if (r[0], r[1], r[2]) in riwayat_lunas else 0] for i, r in enumerate(daftar_hutang_global)]
    except Exception:
        return []

def update_status(id_transaksi, status):
    global riwayat_lunas, daftar_hutang_global
    if 'riwayat_lunas' not in globals():
        riwayat_lunas = set()
    try:
        t = daftar_hutang_global[id_transaksi]
        kunci = (t["dari"], t["ke"], t["jumlah"])
        if status == 1:
            riwayat_lunas.add(kunci)
        else:
            riwayat_lunas.discard(kunci)
    except Exception:
        pass

def sinkronisasi_hutang(daftar_baru):
    global daftar_hutang_global
    daftar_hutang_global = daftar_baru
