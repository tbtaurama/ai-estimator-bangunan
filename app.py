import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
import tempfile
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Estimator Bangunan", layout="wide")

st.title("🏗️ AI Estimator: Baca Gambar Kerja & RAB")
st.markdown("Upload gambar kerja (Arsitektur/MEP/Struktur) dalam format PDF untuk estimasi volume otomatis.")

# --- SIDEBAR: KONFIGURASI API ---
with st.sidebar:
    st.header("Konfigurasi")
    
    # Cek API Key
    if 'GOOGLE_API_KEY' in st.secrets:
        api_key = st.secrets['GOOGLE_API_KEY']
        st.success("✅ API Key terdeteksi dari sistem.")
    else:
        api_key = st.text_input("Masukkan Google AI Studio API Key", type="password")
        if api_key:
             st.success("✅ API Key dimasukkan manual.")

    st.markdown("---")
    # FITUR DEBUGGING: Tombol untuk melihat model apa yang tersedia bagi user
    if st.button("🔍 Cek Model Tersedia"):
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.write("Daftar Model yang bisa Anda pakai:")
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        st.code(m.name)
            except Exception as e:
                st.error(f"Error cek model: {e}")
        else:
            st.warning("Masukkan API Key dulu.")

# --- FUNGSI UTAMA ---
def analyze_blueprint(api_key, file_path, file_mime_type):
    genai.configure(api_key=api_key)
    
    with st.spinner('Mengupload file ke server AI...'):
        sample_file = genai.upload_file(path=file_path, display_name="Gambar Kerja")
        
    # Tunggu file siap (looping check state)
    while sample_file.state.name == "PROCESSING":
        time.sleep(2)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        st.error("Gagal memproses file di sisi Google.")
        return None

    # --- PERUBAHAN DI SINI: MENGGUNAKAN GEMINI 1.5 FLASH ---
    # Flash lebih stabil dan cepat untuk API tier gratis/umum
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    prompt = """
    Anda adalah Quantity Surveyor (QS) AI ahli. Tugas anda:
    1. Analisis gambar teknik konstruksi yang dilampirkan ini (Skala 1:100 pada A3).
    2. Identifikasi elemen pekerjaan (misal: Dinding Bata, Plesteran, Titik Lampu, Stopkontak, Kolom Beton).
    3. Lakukan estimasi kuantitas (Volume, Luas, atau Unit) berdasarkan visual.
    
    PENTING: Keluarkan jawaban HANYA dalam format JSON murni tanpa markdown (jangan pakai ```json), dengan struktur:
    [
        {"kategori": "Arsitektur", "item": "Dinding Bata Merah", "satuan": "m2", "estimasi_volume": 150, "catatan": "Asumsi tinggi 3m"},
        {"kategori": "MEP", "item": "Titik Lampu", "satuan": "titik", "estimasi_volume": 10, "catatan": "-"}
    ]
    """

    with st.spinner('AI sedang membaca gambar dan menghitung RAB...'):
        response = model.generate_content([sample_file, prompt])
        
    # Bersihkan response text agar menjadi valid JSON
    result_text = response.text.replace("```json", "").replace("```", "").strip()
    return result_text

# --- ANTARMUKA UTAMA ---
uploaded_file = st.file_uploader("Pilih File PDF Gambar Kerja", type=['pdf', 'png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    if not api_key:
        st.warning("⚠️ Masukkan API Key di sidebar.")
    else:
        # Simpan file sementara untuk diupload
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        if st.button("🚀 Mulai Analisis Estimasi"):
            try:
                json_result = analyze_blueprint(api_key, tmp_file_path, uploaded_file.type)
                
                if json_result:
                    try:
                        data = json.loads(json_result)
                        df = pd.DataFrame(data)

                        st.subheader("📊 Hasil Rekapitulasi Volume")
                        st.dataframe(df, use_container_width=True)

                        excel_file = "Estimasi_RAB.xlsx"
                        df.to_excel(excel_file, index=False)

                        with open(excel_file, "rb") as f:
                            st.download_button(
                                label="📥 Download Laporan Excel",
                                data=f,
                                file_name="Rekapitulasi_Estimasi_Biaya.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except json.JSONDecodeError:
                        st.error("Gagal membaca format data dari AI. Coba lagi atau gunakan gambar yang lebih jelas.")
                        st.text("Raw Output AI:")
                        st.write(json_result) # Tampilkan raw text untuk debugging
            except Exception as e:
                st.error(f"Terjadi kesalahan sistem: {e}")
            finally:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
