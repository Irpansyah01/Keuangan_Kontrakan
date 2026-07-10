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

# ========================================================
# NAVIGASI BUTTON BESAR
# ========================================================
if "menu_aktif" not in st.session_state:
    st.session_state["menu_aktif"] = "RINGKASAN"

c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)

with c_btn1:
    if st.button("📊 DAFTAR RINGKASAN PENGELUARAN", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "RINGKASAN" else "secondary"):
        st.session_state["menu_aktif"] = "RINGKASAN"
        st.rerun()

with c_btn2:
    if st.button("➕ TAMBAH PENGELUARAN", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "TAMBAH" else "secondary"):
        st.session_state["menu_aktif"] = "TAMBAH"
        st.rerun()

with c_btn3:
    if st.button("💸 PENYELESAIAN PEMBAYARAN PERMINGGU", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "HUTANG" else "secondary"):
        st.session_state["menu_aktif"] = "HUTANG"
        st.rerun()

with c_btn4:
    if st.button("📋 RIWAYAT & EXCEL", use_container_width=True, type="primary" if st.session_state["menu_aktif"] == "RIWAYAT" else "secondary"):
        st.session_state["menu_aktif"] = "RIWAYAT"
        st.rerun()

st.write("")
st.divider()

# Ambil data pengeluaran dari DB
@st.cache_data(ttl=1)
def load_data_cepat():
    with sqlite3.connect(database.DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM pengeluaran", conn)

df = load_data_cepat()
SEMUA_ANGGOTA = ["Irpan", "Azril", "Maulana", "Angga"]

# ========================================================
# HALAMAN 1: DAFTAR RINGKASAN PENGELUARAN
# ========================================================
if st.session_state["menu_aktif"] == "RINGKASAN":
    st.header("📊 Ringkasan Statistik Pengeluaran")
    if df.empty:
        st.info("Belum ada data pengeluaran kas. Silakan klik tombol 'TAMBAH PENGELUARAN' di atas.")
    else:
        total_dana = df["nominal"].sum()
        total_nota = len(df)
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("💰 Total Pengeluaran Bersama", f"Rp {total_dana:,.0f}")
        col_m2.metric("🧾 Jumlah Nota Masuk", f"{total_nota} Transaksi")
        
        st.write("")
        st.markdown("**Grafik Total Belanja yang Dibayarkan Per Orang:**")
        ringkasan_orang = df.groupby("dibayar_oleh")["nominal"].sum()
        st.bar_chart(ringkasan_orang)

# ========================================================
# HALAMAN 2: FORMULIR TAMBAH PENGELUARAN
# ========================================================
elif st.session_state["menu_aktif"] == "TAMBAH":
    st.header("📝 Formulir Input Nota Belanja Baru")
    with st.form("form_kas_baru", clear_on_submit=True):
        col_tgl, col_nama = st.columns(2)
        with col_tgl:
            tanggal = st.date_input("Pilih Tanggal Nota:", datetime.now())
        with col_nama:
            dibayar_oleh = st.selectbox("Siapa yang membayar duluan?:", SEMUA_ANGGOTA)
            
        barang = st.text_input("Nama Barang / Keperluan Kontrakan:", placeholder="Contoh: Beli Galon, Token Listrik")
        nominal = st.number_input("Nominal / Harga Barang (Rp):", min_value=0, step=1000)
        
        st.markdown("⚠️ **Siapa saja yang ikut iuran/menikmati fasilitas ini?**")
        col_cb = st.columns(4)
        siapa_ikut = []
        for idx, anggota in enumerate(SEMUA_ANGGOTA):
            with col_cb[idx]:
                if st.checkbox(anggota, value=True, key=f"cb_{anggota}"):
                    siapa_ikut.append(anggota)
        
        simpan = st.form_submit_button("💾 Simpan ke Dalam Sistem")
        if simpan:
            if barang.strip() == "" or nominal <= 0:
                st.error("Gagal simpan! Isian nama barang wajib diisi.")
            elif len(siapa_ikut) == 0:
                st.error("Gagal simpan! Minimal harus ada 1 orang yang diceklis.")
            else:
                konsumen_txt = ",".join(siapa_ikut)
                database.tambah_pengeluaran(str(tanggal), f"{barang} | Ikut: {konsumen_txt}", nominal, dibayar_oleh)
                st.success(f"Berhasil dicatat!")
                st.cache_data.clear()
                st.rerun()

# ========================================================
# HALAMAN 3: PENYELESAIAN PEMBAYARAN PERMINGGU (FIXED & ANTI-GAGAL)
# ========================================================
elif st.session_state["menu_aktif"] == "HUTANG":
    st.header("💸 Penyelesaian Hutang Mingguan (Berdasarkan Ceklis)")
    if df.empty:
        st.info("Hutang piutang kosong.")
    else:
        saldo_semua = {nama: 0 for nama in SEMUA_ANGGOTA}

        for _, row in df.iterrows():
            nama_barang_mentah = row["barang"]
            nominal_nota = row["nominal"]
            pembayar_nota = row["dibayar_oleh"]
            
            if " | Ikut: " in nama_barang_mentah:
                barang_asli, konsumen_part = nama_barang_mentah.split(" | Ikut: ")
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

        tab1, tab2 = st.tabs(["⏳ Belum Dibayar", "✅ Sudah Dilunasi"])

        with tab1:
            ada_belum = False
            for item in data_hutang:
                id_h, dari, ke, jml, status, foto = item
                if status == 0:
                    ada_belum = True
                    with st.container(border=True):
                        col_txt, col_upl = st.columns([4, 3])
                        with col_txt:
                            st.markdown(f"👤 **{dari}** ➡️ wajib transfer ke **{ke}**")
                            st.markdown(f"### Rp {jml:,.0f}")
                        with col_upl:
                            # DIUBAH JADI INPUT TEKS/LINK AGAR 100% AMAN DI SERVER LIVE ONLINE
                            input_bukti = st.text_input("Link Foto Bukti TF (Opsional, Boleh Kosong):", placeholder="Contoh: link Gdrive atau ketik 'LUNAS'", key=f"t_{id_h}")
                            if st.button("Konfirmasi Bayar Lunas", key=f"b_{id_h}", type="primary"):
                                database.update_status_hutang(id_h, 1, input_bukti if input_bukti.strip() != "" else "Lunas (Tanpa Link)")
                                st.success("Status lunas dikonfirmasi!")
                                st.cache_data.clear()
                                st.rerun()
            if not ada_belum:
                st.success("🎉 Luar biasa! Semua iuran minggu ini sudah impas lunas.")

        with tab2:
            ada_lunas = False
            for item in data_hutang:
                id_h, dari, ke, jml, status, foto = item
                if status == 1:
                    ada_lunas = True
                    with st.container(border=True):
                        c_t, c_f, c_b = st.columns([3, 2, 2])
                        c_t.markdown(f"~~**{dari}** ke **{ke}**~~ (Lunas)\n### Rp {jml:,.0f}")
                        
                        # Menampilkan catatan atau link gdrive yang diinput tadi
                        if foto:
                            c_f.markdown(f"ℹ️ **Keterangan Bukti:**\n`{foto}`")
                        else:
                            c_f.caption("Tidak ada catatan bukti")
                            
                        if c_b.button("Batalkan Pelunasan", key=f"btl_{id_h}"):
                            database.update_status_hutang(id_h, 0, None)
                            st.cache_data.clear()
                            st.rerun()
            if not ada_lunas:
                st.info("Belum ada transaksi iuran yang diselesaikan.")

# ========================================================
# HALAMAN 4: RIWAYAT, HAPUS DATA & EXCEL
# ========================================================
elif st.session_state["menu_aktif"] == "RIWAYAT":
    st.header("📋 Laporan & Penelusuran Riwayat")
    
    data_mentah = database.ambil_semua_data()
    if not data_mentah:
        st.info("Belum ada riwayat transaksi.")
    else:
        clean_rows = []
        for r in data_mentah:
            id_r, tgl, brg, nom, oleh = r
            brg_bersih = brg.split(" | Ikut: ")[0] if " | Ikut: " in brg else brg
            clean_rows.append([id_r, tgl, brg_bersih, nom, oleh])
            
        df_riwayat = pd.DataFrame(clean_rows, columns=["id", "tanggal", "barang", "nominal", "dibayar_oleh"])
        df_riwayat["tanggal_dt"] = pd.to_datetime(df_riwayat["tanggal"])
        df_riwayat["bulan_tahun"] = df_riwayat["tanggal_dt"].dt.strftime("%Y-%m")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_riwayat[["tanggal", "barang", "nominal", "dibayar_oleh"]].to_excel(writer, sheet_name='Data_Kas', index=False)
        
        st.download_button(label="🟢 Download Excel (.xlsx)", data=buffer.getvalue(), file_name="Laporan_Kas.xlsx", mime="application/vnd.ms-excel")
        st.divider()

        st.subheader("📝 Semua Riwayat Nota Masuk")
        st.write("Jika ada data yang salah input, catat nomor **ID**-nya lalu masukkan ke kolom hapus di bawah.")
        st.dataframe(df_riwayat[["id", "tanggal", "barang", "nominal", "dibayar_oleh"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗑️ Zona Hapus Data Salah Input")
        id_target = st.number_input("Masukkan ID Angka Nota yang mau dihapus:", min_value=0, step=1)
        tombol_hapus = st.button("❌ Hapus Permanen Nota Ini", type="primary")
        
        if tombol_hapus and id_target > 0:
            database.hapus_pengeluaran(id_target)
            st.success(f"Nota dengan ID {id_target} berhasil dihapus!")
            st.cache_data.clear()
            st.rerun()
            
