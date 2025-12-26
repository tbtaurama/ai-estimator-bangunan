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
    api_key = st.text_input("Masukkan Google AI Studio API Key", type="password")
    st.info("Pastikan API Key memiliki akses ke model Gemini 1.5 Pro atau Flash.")

# --- FUNGSI UTAMA ---
def analyze_blueprint(api_key, file_path, file_mime_type):
    """Mengirim file ke Gemini untuk dianalisis."""
    genai.configure(api_key=api_key)
    
    # Upload file ke Google GenAI
    with st.spinner('Mengupload file ke server AI...'):
        sample_file = genai.upload_file(path=file_path, display_name="Gambar Kerja")
        
    # Tunggu sampai file siap diproses
    while sample_file.state.name == "PROCESSING":
        time.sleep(2)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        st.error("Gagal memproses file di sisi Google.")
        return None

    # Model Configuration
    # Kita menggunakan Gemini 1.5 Flash untuk kecepatan, atau Pro untuk akurasi tinggi
    model = genai.GenerativeModel(model_name="gemini-1.5-pro")

    # Prompt Engineering (Sangat Penting)
    prompt = """
    Anda adalah Quantity Surveyor (QS) AI ahli. Tugas anda:
    1. Analisis gambar teknik konstruksi yang dilampirkan ini (Skala 1:100 pada A3).
    2. Identifikasi elemen pekerjaan (misal: Dinding Bata, Plesteran, Titik Lampu, Stopkontak, Kolom Beton).
    3. Lakukan estimasi kuantitas (Volume, Luas, atau Unit) berdasarkan visual yang terlihat. 
       Catatan: Karena anda tidak bisa mengukur skala piksel secara presisi, berikan estimasi terbaik berdasarkan proporsi visual standar arsitektur.
    4. Kelompokkan berdasarkan kategori (Arsitektur, Struktur, atau MEP).
    
    PENTING: Keluarkan jawaban HANYA dalam format JSON murni tanpa markdown, dengan struktur berikut:
    [
        {"kategori": "Arsitektur", "item": "Dinding Bata Merah", "satuan": "m2", "estimasi_volume": 150, "catatan": "Asumsi tinggi dinding 3m"},
        {"kategori": "MEP", "item": "Titik Lampu Downlight", "satuan": "titik", "estimasi_volume": 12, "catatan": "Area ruang tengah dan kamar"}
    ]
    """

    with st.spinner('AI sedang membaca gambar dan menghitung RAB...'):
        response = model.generate_content([sample_file, prompt])
        
    # Bersihkan response text agar menjadi valid JSON
    result_text = response.text.replace("```json", "").replace("```", "").strip()
    return result_text

# --- ANTARMUKA UTAMA ---
uploaded_file = st.file_uploader("Pilih File PDF Gambar Kerja", type=['pdf', 'png', 'jpg', 'jpeg'])

if uploaded_file is not None and api_key:
    # Simpan file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    if st.button("🚀 Mulai Analisis Estimasi"):
        try:
            # Proses Analisis
            json_result = analyze_blueprint(api_key, tmp_file_path, uploaded_file.type)
            
            if json_result:
                # Parsing JSON ke Dataframe
                data = json.loads(json_result)
                df = pd.DataFrame(data)

                # Tampilkan Hasil di Layar
                st.subheader("📊 Hasil Rekapitulasi Volume")
                st.dataframe(df, use_container_width=True)

                # Konversi ke Excel
                excel_file = "Estimasi_RAB.xlsx"
                df.to_excel(excel_file, index=False)

                # Tombol Download
                with open(excel_file, "rb") as f:
                    st.download_button(
                        label="📥 Download Laporan Excel",
                        data=f,
                        file_name="Rekapitulasi_Estimasi_Biaya.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("Gagal mendapatkan respon dari AI. Coba lagi.")

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
            st.warning("Tips: Pastikan gambar jelas dan API Key valid.")
        
        finally:
            # Hapus file sementara
            os.remove(tmp_file_path)

elif not api_key:
    st.warning("⚠️ Masukkan API Key di sidebar sebelah kiri untuk memulai.")