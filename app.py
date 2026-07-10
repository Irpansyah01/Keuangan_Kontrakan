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
# SISTEM NAVIGASI 4 BUTTON BESAR
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

# Hubungkan ke database
with sqlite3.connect(database.DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM pengeluaran", conn)

# Daftar semua anak kontrakan tetap
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
# HALAMAN 2: FORMULIR TAMBAH PENGELUARAN (UPDATE FITUR CEKLIS)
# ========================================================
elif st.session_state["menu_aktif"] == "TAMBAH":
    st.header("📝 Formulir Input Nota Belanja Baru")
    with st.form("form_kas_baru", clear_on_submit=True):
        col_tgl, col_nama = st.columns(2)
        with col_tgl:
            tanggal = st.date_input("Pilih Tanggal Nota:", datetime.now())
        with col_nama:
            dibayar_oleh = st.selectbox("Siapa yang membayar duluan?:", SEMUA_ANGGOTA)
            
        barang = st.text_input("Nama Barang / Keperluan Kontrakan:", placeholder="Contoh: Beli Galon, Token Listrik, Patungan Makan")
        nominal = st.number_input("Nominal / Harga Barang (Rp):", min_value=0, step=1000)
        
        # --- FITUR SOLUSI BARU: CEKLIS PENGGUNA ---
        st.markdown("⚠️ **Siapa saja yang ikut iuran/menikmati fasilitas ini?** (Uncheck yang tidak ikut)")
        col_cb = st.columns(4)
        siapa_ikut = []
        for idx, anggota in enumerate(SEMUA_ANGGOTA):
            with col_cb[idx]:
                # Secara default ter-ceklis semua (True)
                if st.checkbox(anggota, value=True, key=f"cb_{anggota}"):
                    siapa_ikut.append(anggota)
        
        simpan = st.form_submit_button("💾 Simpan ke Dalam Sistem")
        if simpan:
            if barang.strip() == "" or nominal <= 0:
                st.error("Gagal simpan! Isian nama barang wajib diisi dan nominal harus lebih besar dari Rp 0.")
            elif len(siapa_ikut) == 0:
                st.error("Gagal simpan! Minimal harus ada 1 orang yang diceklis sebagai penanggung beban iuran.")
            else:
                # Trik pintar: Menyimpan daftar orang yang ikut dalam format teks dipisah koma, contoh: "Irpan,Azril"
                konsumen_txt = ",".join(siapa_ikut)
                
                # Kita akali masukkan data orang yang ikut ke tabel dengan format khusus di nama barang, atau modifikasi query
                database.tambah_pengeluaran(str(tanggal), f"{barang} | Ikut: {konsumen_txt}", nominal, dibayar_oleh)
                st.success(f"Berhasil! Nota '{barang}' sukses dicatat. Dibagi adil untuk: {', '.join(siapa_ikut)}")
                st.rerun()

# ========================================================
# HALAMAN 3: PENYELESAIAN PEMBAYARAN PERMINGGU (LOGIKA BARU)
# ========================================================
elif st.session_state["menu_aktif"] == "HUTANG":
    st.header("💸 Penyelesaian Hutang Mingguan (Berdasarkan Ceklis)")
    if df.empty:
        st.info("Hutang piutang kosong karena belum ada transaksi belanja yang terdata.")
    else:
        saldo_semua = {nama: 0 for nama in SEMUA_ANGGOTA}

        for _, row in df.iterrows():
            nama_barang_mentah = row["barang"]
            nominal_nota = row["nominal"]
            pembayar_nota = row["dibayar_oleh"]
            
            # Memisahkan nama barang asli dengan daftar orang yang diceklis tadi
            if " | Ikut: " in nama_barang_mentah:
                barang_asli, konsumen_part = nama_barang_mentah.split(" | Ikut: ")
                peserta_nota = konsumen_part.split(",")
            else:
                # Jaga-jaga jika ada data lama yang belum pakai sistem ceklis
                peserta_nota = ["Irpan", "Azril", "Maulana", "Angga"]
            
            # Hitung pembagian hanya untuk orang yang ikut menikmati
            beban_per_orang = nominal_nota / len(peserta_nota)
            
            # Kurangi saldo orang-orang yang ada di dalam ceklis nota tersebut
            for p in peserta_nota:
                if p in saldo_semua:
                    saldo_semua[p] -= beban_per_orang
                    
            # Tambahkan nominal penuh ke orang yang nalangin di awal
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
                            file_foto = st.file_uploader("Upload Foto Bukti TF", type=["png", "jpg", "jpeg"], key=f"f_{id_h}")
                            if st.button("Konfirmasi Bayar Lunas", key=f"b_{id_h}"):
                                nama_file_simpan = None
                                if file_foto:
                                    nama_file_simpan = f"bukti_{id_h}_{file_foto.name}"
                                    with open(os.path.join(database.BUKTI_DIR, nama_file_simpan), "wb") as f:
                                        f.write(file_foto.getbuffer())
                                database.update_status_hutang(id_h, 1, nama_file_simpan)
                                st.success("Status lunas dikonfirmasi!")
                                st.rerun()
            if not ada_belum:
                st.success("🎉 Luar biasa! Semua iuran minggu ini sudah impas lunas.")

        with tab2:
            for item in data_hutang:
                id_h, dari, ke, jml, status, foto = item
                if status == 1:
                    with st.container(border=True):
                        c_t, c_f, c_b = st.columns([3, 2, 2])
                        c_t.markdown(f"~~**{dari}** ke **{ke}**~~ (Lunas)\n### Rp {jml:,.0f}")
                        if foto:
                            jalur_foto = os.path.join(database.BUKTI_DIR, foto)
                            if os.path.exists(jalur_foto):
                                c_f.image(jalur_foto, width=150, caption="Foto Bukti Transfer")
                        if c_b.button("Batalkan Pelunasan", key=f"btl_{id_h}"):
                            database.update_status_hutang(id_h, 0, None)
                            st.rerun()

# ========================================================
# HALAMAN 4: RIWAYAT, HAPUS DATA & EXCEL
# ========================================================
elif st.session_state["menu_aktif"] == "RIWAYAT":
    st.header("📋 Laporan & Penelusuran Riwayat")
    
    data_mentah = database.ambil_semua_data()
    if not data_mentah:
        st.info("Belum ada riwayat transaksi belanja yang tersimpan.")
    else:
        # Bersihkan tampilan nama barang dari teks sistem iuran saat diexport
        clean_rows = []
        for r in data_mentah:
            id_r, tgl, brg, nom, oleh = r
            brg_bersih = brg.split(" | Ikut: ")[0] if " | Ikut: " in brg else brg
            clean_rows.append([id_r, tgl, brg_bersih, nom, oleh])
            
        df_riwayat = pd.DataFrame(clean_rows, columns=["id", "tanggal", "barang", "nominal", "dibayar_oleh"])
        df_riwayat["tanggal_dt"] = pd.to_datetime(df_riwayat["tanggal"])
        df_riwayat["bulan_tahun"] = df_riwayat["tanggal_dt"].dt.strftime("%Y-%m")
        
        def rumus_minggu(dt):
            return (dt.day - 1) // 7 + 1
        df_riwayat["minggu_ke"] = df_riwayat["tanggal_dt"].apply(rumus_minggu)
        
        st.subheader("📥 Ekspor Laporan Kas Kontrakan")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_riwayat[["tanggal", "barang", "nominal", "dibayar_oleh"]].to_excel(writer, sheet_name='Data_Kas', index=False)
        
        st.download_button(
            label="🟢 Download Seluruh Laporan (.xlsx / Excel)",
            data=buffer.getvalue(),
            file_name="Laporan_Keuangan_Kontrakan.xlsx",
            mime="application/vnd.ms-excel"
        )
        st.divider()

        st.subheader("🔍 Filter Berdasarkan Minggu & Bulan")
        list_bulan = sorted(df_riwayat["bulan_tahun"].unique(), reverse=True)
        bulan_pilihan = st.selectbox("Pilih Bulan Akuntansi:", list_bulan)
        
        df_bulan_filter = df_riwayat[df_riwayat["bulan_tahun"] == bulan_pilihan].sort_values(by="tanggal_dt", ascending=False)
        total_bulan = df_bulan_filter["nominal"].sum()
        st.markdown(f"### Total Belanja Bulan ini: **Rp {total_bulan:,.0f}**")

        for m in range(1, 6):
            df_minggu = df_bulan_filter[df_riwayat["minggu_ke"] == m]
            if not df_minggu.empty:
                total_m = df_minggu["nominal"].sum()
                with st.expander(f"📅 Minggu ke-{m} | Total Belanja: Rp {total_m:,.0f}"):
                    
                    st.markdown("---")
                    c_h1, c_h2, c_h3, c_h4, c_h5 = st.columns([2, 3, 2, 2, 1.5])
                    c_h1.markdown("**Tanggal**")
                    c_h2.markdown("**Nama Barang**")
                    c_h3.markdown("**Nominal**")
                    c_h4.markdown("**Dibayar Oleh**")
                    c_h5.markdown("**Aksi**")
                    st.markdown("---")
                    
                    for idx, baris in df_minggu.iterrows():
                        col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns([2, 3, 2, 2, 1.5])
                        col_r1.write(baris["tanggal"])
                        col_r2.write(baris["barang"])
                        col_r3.write(f"Rp {baris['nominal']:,.0f}")
                        col_r4.write(baris["dibayar_oleh"])
                        
                        if col_r5.button("🗑️ Hapus", key=f"del_{baris['id']}", type="primary"):
                            database.hapus_pengeluaran(baris["id"])
                            st.success("Data berhasil dihapus!")
                            st.rerun()
