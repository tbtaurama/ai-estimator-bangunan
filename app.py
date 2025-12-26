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
st.caption("Powered by Gemini 2.0 Flash")

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

# --- FUNGSI UTAMA ---
def analyze_blueprint(api_key, file_path, file_mime_type):
    genai.configure(api_key=api_key)
    
    with st.spinner('Mengupload file ke server AI...'):
        sample_file = genai.upload_file(path=file_path, display_name="Gambar Kerja")
        
    # Tunggu file siap
    while sample_file.state.name == "PROCESSING":
        time.sleep(2)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        st.error("Gagal memproses file di sisi Google.")
        return None

    # --- BAGIAN PENTING: MENGGUNAKAN GEMINI 2.0 FLASH ---
    # Kita menggunakan model yang PASTI ADA di daftar Anda
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")

    prompt = """
    Bertindaklah sebagai Senior Quantity Surveyor. Tugas Anda:
    1. Analisis gambar teknik (PDF) yang dilampirkan.
    2. Identifikasi elemen konstruksi visual (Dinding, Lantai, Plafon, Jendela, Pintu, MEP).
    3. Lakukan "Take-off" atau perhitungan volume estimasi kasar berdasarkan proporsi visual gambar.
    
    ATURAN PENTING:
    - Jangan berikan narasi pengantar.
    - Output HARUS berupa JSON valid array of objects.
    - Struktur JSON:
    [
        {"kategori": "Arsitektur/Struktur/MEP", "item": "Nama Pekerjaan", "satuan": "m2/m3/unit", "estimasi_volume": 0, "catatan": "dasar perhitungan"}
    ]
    """

    with st.spinner('AI sedang menganalisis gambar dengan Gemini 2.0 Flash...'):
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
        # Simpan file sementara
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

                        st.success("Analisis Selesai!")
                        
                        # Tampilkan Tabel
                        st.subheader("📊 Hasil Rekapitulasi Volume")
                        st.dataframe(df, use_container_width=True)

                        # Siapkan Excel
                        excel_file = "Estimasi_RAB.xlsx"
                        df.to_excel(excel_file, index=False)

                        with open(excel_file, "rb") as f:
                            st.download_button(
                                label="📥 Download Excel",
                                data=f,
                                file_name="Rekapitulasi_Estimasi_Biaya.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except json.JSONDecodeError:
                        st.error("Gagal format data. Output AI tidak valid JSON.")
                        st.text_area("Raw Output:", json_result)
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
            finally:
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
