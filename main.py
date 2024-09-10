import streamlit as st
import os
import tempfile
from openai import OpenAI
from dotenv import load_dotenv
import ffmpeg
import datetime

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()


def extract_audio(video_file):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        try:
            (
                ffmpeg
                .input(video_file)
                .output(temp_audio.name, acodec='libmp3lame', ar=44100, ac=2, b='192k')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return temp_audio.name
        except ffmpeg.Error as e:
            raise RuntimeError(f"Error extracting audio: {e.stderr.decode()}")


def transcribe_audio(audio_file):
    with open(audio_file, "rb") as audio:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio,
            response_format="srt"
        )
    return response


def translate_text(text, target_language):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "You are a very helpful and talented translator who can translate all languages and srt files."},
            {"role": "user",
             "content": f"Could you please translate the .srt text below to {target_language}? Do not add any comments of yours only the translation. This is crucial, even if the language of the given text and the selected language is same, do not change the given text and return it same as original."
                        f"Please do not change the timestamps and structure of the file.\n<Transcription>{text}</Transcription>"}
        ]
    )
    return response.choices[0].message.content.strip()


def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_file.write(uploaded_file.read())
        return temp_file.name


def save_text_file(text, prefix):
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{current_time}.srt"

    return text, filename


# Custom CSS for styling
st.markdown("""
<style>
    .translation-text {
        background-color: #F0F0F0;
        padding: 10px;
        border-radius: 5px;
        white-space: pre-wrap;
        font-family: monospace;
        max-height: 300px;  /* Set a maximum height */
        overflow-y: auto;   /* Enable vertical scrolling */
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .process-step {
        background-color: #E6F3FF;
        padding: 5px 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }
    .stDownloadButton>button {
        background-color: #3498db;
        color: white;
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }
    .stDownloadButton>button:hover {
        background-color: #2980b9;
    }
    .title-section {
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
        color: #333333;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-section">🎥 AI-Powered Video Translation App 🌐</div>', unsafe_allow_html=True)

st.markdown("---")

# Language selection with checkboxes
st.subheader("1. Dil Seçimi")
languages = {
    "Türkçe": "Turkish",
    "İngilizce": "English",
    "Fransızca": "French",
    "Almanca": "German"
}
selected_languages = []
cols = st.columns(len(languages))
for i, (lang, eng_name) in enumerate(languages.items()):
    if cols[i].checkbox(lang):
        selected_languages.append(lang)

st.markdown("---")

# Video upload
st.subheader("2. Video Yükleme")
uploaded_file = st.file_uploader("", type=["mp4", "mov", "avi", "mkv"])
if uploaded_file:
    st.success("Video yüklendi!")

# Process button (renamed to "Çevirileri Al")
if st.button("Çevirileri Al", type="primary"):
    if not uploaded_file:
        st.error("Lütfen bir video dosyası yükleyin.")
    elif not selected_languages:
        st.error("Lütfen en az bir dil seçin.")
    else:
        try:
            with st.spinner("Video işleniyor..."):
                # Process flow
                st.subheader("İşlem Aşamaları:")

                # Step 1: Save uploaded file
                st.markdown('<div class="process-step">1. Video yükleniyor</div>', unsafe_allow_html=True)
                temp_video_path = save_uploaded_file(uploaded_file)

                # Step 2: Extract audio
                st.markdown('<div class="process-step">2. Video ses dosyasına dönüştürülüyor (ffmpeg)</div>',
                            unsafe_allow_html=True)
                audio_file = extract_audio(temp_video_path)

                # Step 3: Transcribe audio
                st.markdown('<div class="process-step">3. Ses dosyası metne çevriliyor (OpenAI Whisper)</div>',
                            unsafe_allow_html=True)
                transcription = transcribe_audio(audio_file)

                # Save transcription
                transcription, transcription_filename = save_text_file(transcription, "transcription")
                st.session_state.transcription = {
                    'content': transcription,
                    'filename': transcription_filename
                }

                # Step 4: Translate text
                st.markdown('<div class="process-step">4. Metin seçilen dillere çevriliyor (ChatGPT 4o-mini)</div>',
                            unsafe_allow_html=True)
                translations = {}
                for lang in selected_languages:
                    translation = translate_text(transcription, languages[lang])
                    content, filename = save_text_file(translation, f"{lang}_{languages[lang]}")
                    translations[lang] = {'content': content, 'filename': filename}

                st.session_state.translations = translations






        except RuntimeError as e:
            st.error(f"İşlem hatası: {str(e)}")
        except Exception as e:
            st.error(f"Beklenmeyen bir hata oluştu: {str(e)}")
        finally:
            # Clean up temporary files
            if 'temp_video_path' in locals():
                os.unlink(temp_video_path)
            if 'audio_file' in locals():
                os.unlink(audio_file)

        st.success("İşlem tamamlandı!")

# Display results
if 'transcription' in st.session_state and 'translations' in st.session_state:
    st.subheader("Transkripsiyon ve Çeviri Sonuçları")

    # Display and download transcription
    st.subheader("Orijinal Transkripsiyon:")
    st.markdown(f'<div class="translation-text">{st.session_state.transcription["content"]}</div>',
                unsafe_allow_html=True)

    st.download_button(

        label="Orijinal İçerik Metni",
        data=st.session_state.transcription['content'],
        file_name=st.session_state.transcription['filename'],
        mime='text/plain',
        key="transcription_download"
    )

    # Display and download translations
    for lang, translation_data in st.session_state.translations.items():
        st.markdown("-----")
        st.subheader(f"{lang} Çevirisi:")

        # Display the translated text once
        st.markdown(f'<div class="translation-text">{translation_data["content"]}</div>', unsafe_allow_html=True)

        # Custom download button
        st.download_button(

            label=f"{lang} Çeviriyi İndir",
            data=translation_data['content'],
            file_name=translation_data['filename'],
            mime='text/plain',
            key=f"{lang}_download"
        )

        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")