import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import database
import io

st.set_page_config(page_title="Keuangan Kontrakan", layout="wide")

st.title("🏠 Aplikasi Keuangan Kontrakan")
st.write("Kelola keuangan bersama penghuni kontrakan secara praktis dan adil.")
st.divider()

# Cek Hari Saat Ini (0 = Senin, 6 = Minggu)
hari_ini = datetime.now().weekday()
nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][hari_ini]

# Navigasi Menu
if "menu_aktif" not in st.session_state:
    st.session_state["menu_aktif"] = "RINGKASAN"

c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
with c_btn1:
    if st.button("📊 DAFTAR RINGKASAN", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "RINGKASAN" else "secondary"):
        st.session_state["menu_aktif"] = "RINGKASAN"
        st.rerun()
with c_btn2:
    if st.button("➕ TAMBAH PENGELUARAN", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "TAMBAH" else "secondary"):
        st.session_state["menu_aktif"] = "TAMBAH"
        st.rerun()
with c_btn3:
    if st.button("💸 PEMBAYARAN MINGGUAN", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "HUTANG" else "secondary"):
        st.session_state["menu_aktif"] = "HUTANG"
        st.rerun()
with c_btn4:
    if st.button("📋 RIWAYAT & EXCEL", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "RIWAYAT" else "secondary"):
        st.session_state["menu_aktif"] = "RIWAYAT"
        st.rerun()

st.divider()

@st.cache_data(ttl=1)
def load_data_cepat():
    try:
        with database.connect() as conn:
            return pd.read_sql_query("SELECT * FROM pengeluaran ORDER BY tanggal DESC", conn)
    except Exception:
        return pd.DataFrame(columns=["id", "tanggal", "barang", "nominal", "dibayar_oleh"])

df = load_data_cepat()
SEMUA_ANGGOTA = ["Irpan", "Azril", "Maulana", "Angga"]

# HALAMAN 1: RINGKASAN
if st.session_state["menu_aktif"] == "RINGKASAN":
    st.header("📊 Ringkasan Statistik")
    if df.empty:
        st.info("Belum ada data pengeluaran.")
    else:
        total_dana = df["nominal"].sum()
        st.metric("💰 Total Pengeluaran Bersama", f"Rp {total_dana:,.0f}")
        ringkasan_orang = df.groupby("dibayar_oleh")["nominal"].sum()
        st.bar_chart(ringkasan_orang)

# HALAMAN 2: TAMBAH PENGELUARAN
elif st.session_state["menu_aktif"] == "TAMBAH":
    st.header("📝 Formulir Input Nota")
    with st.form("form_kas_baru", clear_on_submit=True):
        tanggal = st.date_input("Pilih Tanggal Nota:", datetime.now())
        dibayar_oleh = st.selectbox("Siapa yang membayar duluan?:", SEMUA_ANGGOTA)
        barang = st.text_input("Nama Barang / Keperluan Kontrakan:")
        nominal = st.number_input("Nominal (Rp):", min_value=0, step=1000)
        
        st.markdown("⚠️ **Siapa saja yang ikut iuran?**")
        col_cb = st.columns(4)
        siapa_ikut = []
        for idx, anggota in enumerate(SEMUA_ANGGOTA):
            with col_cb[idx]:
                if st.checkbox(anggota, value=True, key=f"cb_{anggota}"):
                    siapa_ikut.append(anggota)
        
        if st.form_submit_button("💾 Simpan Data"):
            if barang.strip() == "" or nominal <= 0 or len(siapa_ikut) == 0:
                st.error("Data kurang lengkap!")
            else:
                konsumen_txt = ",".join(siapa_ikut)
                database.tambah_pengeluaran(str(tanggal), f"{barang} | Ikut: {konsumen_txt}", nominal, dibayar_oleh)
                st.success("Berhasil dicatat!")
                st.cache_data.clear()
                st.rerun()

# HALAMAN 3: PEMBAYARAN MINGGUAN
elif st.session_state["menu_aktif"] == "HUTANG":
    st.header("💸 Penyelesaian Pembayaran")
    st.info(f"Hari ini: **{nama_hari}**")
    
    if df.empty:
        st.info("Belum ada transaksi sama sekali.")
    else:
        saldo_semua = {nama: 0 for nama in SEMUA_ANGGOTA}
        for _, row in df.iterrows():
            nama_barang_mentah = str(row["barang"])
            nominal_nota = row["nominal"]
            pembayar_nota = row["dibayar_oleh"]
            
            if " | Ikut: " in nama_barang_mentah:
                _, konsumen_part = nama_barang_mentah.split(" | Ikut: ")
                peserta_nota = konsumen_part.split(",")
            else:
                peserta_nota = SEMUA_ANGGOTA
            
            beban_per_orang = nominal_nota / len(peserta_nota)
            for p in peserta_nota:
                if p in saldo_semua:
                    saldo_semua[p] -= beban_per_orang
            if pembayar_nota in saldo_semua:
                saldo_semua[pembayar_nota] += nominal_nota

        pembayar = [{"nama": n, "saldo": abs(s)} for n, s in saldo_semua.items() if s < 0]
        penerima = [{"nama": n, "saldo": s} for n, s in saldo_semua.items() if s > 0]

        transaksi_kalkulasi = []
        i, j = 0, 0
        while i < len(pembayar) and j < len(penerima):
            b, p = pembayar[i], penerima[j]
            jumlah = int(min(b["saldo"], p["saldo"]))
            if jumlah > 0:
                transaksi_kalkulasi.append({"dari": b["nama"], "ke": p["nama"], "jumlah": jumlah})
            b["saldo"] -= jumlah
            p["saldo"] -= jumlah
            if b["saldo"] == 0: i += 1
            if p["saldo"] == 0: j += 1

        database.sinkronisasi_hutang(transaksi_kalkulasi)
        data_hutang = database.ambil_penyelesaian()

        # JIKA BUKAN HARI MINGGU (SISTEM KUNCI / HANYA LIHAT DATA)
        if hari_ini != 6:  # 6 = Hari Minggu
            st.warning("⚠️ Pembayaran hanya dibuka setiap hari **Minggu**. Hutang belum lunas minggu lalu akan otomatis diakumulasikan ke minggu depan.")
            
            st.subheader("📋 Catatan Hutang Berjalan Saat Ini:")
            for item in data_hutang:
                _, dari, ke, jml, status = item
                if status == 0:
                    st.markdown(f"❌ **{dari}** belum bayar ke **{ke}** sebesar **Rp {jml:,.0f}**")
        else:
            # JIKA HARI MINGGU (TOMBOL AKTIF)
            tab1, tab2 = st.tabs(["⏳ Belum Dibayar", "✅ Sudah Dilunasi"])
            
            with tab1:
                ada_belum = False
                for item in data_hutang:
                    id_h, dari, ke, jml, status = item
                    if status == 0:
                        ada_belum = True
                        with st.container(border=True):
                            col_txt, col_btn = st.columns([6, 2])
                            col_txt.markdown(f"👤 **{dari}** ➡️ wajib transfer ke **{ke}** \n### Rp {jml:,.0f}")
                            
                            if col_btn.button("✅ Konfirmasi Lunas", key=f"lns_{id_h}", type="primary", use_container_width=True):
                                database.update_status(id_h, 1)
                                st.success("Berhasil dikonfirmasi lunas!")
                                st.cache_data.clear()
                                st.rerun()
                if not ada_belum:
                    st.success("🎉 Semua iuran minggu ini sudah impas lunas!")

            with tab2:
                for item in data_hutang:
                    id_h, dari, ke, jml, status = item
                    if status == 1:
                        with st.container(border=True):
                            col_txt, col_btn = st.columns([6, 2])
                            col_txt.markdown(f"~~**{dari}** ke **{ke}**~~ (Lunas)\n### Rp {jml:,.0f}")
                            if col_btn.button("↩️ Batalkan", key=f"btl_{id_h}", use_container_width=True):
                                database.update_status(id_h, 0)
                                st.cache_data.clear()
                                st.rerun()

# HALAMAN 4: RIWAYAT
elif st.session_state["menu_aktif"] == "RIWAYAT":
    st.header("📋 Laporan Riwayat Transaksi")
    data_mentah = database.ambil_semua_data()
    if not data_mentah:
        st.info("Belum ada riwayat transaksi.")
    else:
        clean_rows = []
        for r in data_mentah:
            id_r, tgl, brg, nom, oleh = r
            brg_str = str(brg)
            brg_bersih = brg_str.split(" | Ikut: ")[0] if " | Ikut: " in brg_str else brg_str
            clean_rows.append([id_r, tgl, brg_bersih, nom, oleh])
            
        df_riwayat = pd.DataFrame(clean_rows, columns=["id", "tanggal", "barang", "nominal", "dibayar_oleh"])
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_riwayat[["tanggal", "barang", "nominal", "dibayar_oleh"]].to_excel(writer, sheet_name='Data_Kas', index=False)
        st.download_button(label="🟢 Download Excel (.xlsx)", data=buffer.getvalue(), file_name="Laporan_Kas.xlsx", mime="application/vnd.ms-excel")
        
        st.subheader("Riwayat Nota:")
        st.dataframe(df_riwayat, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗑️ Hapus Data Salah Input")
        id_target = st.number_input("Masukkan ID Nota untuk dihapus:", min_value=0, step=1)
        if st.button("❌ Hapus Permanen", type="primary") and id_target > 0:
            database.hapus_pengeluaran(id_target)
            st.success(f"Data ID {id_target} berhasil dihapus!")
            st.cache_data.clear()
            st.rerun()
