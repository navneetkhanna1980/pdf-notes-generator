import streamlit as st
import PyPDF2
import pdfplumber
import google.generativeai as genai
from pathlib import Path
import re
import time
import io
from datetime import datetime

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="📚 Smart PDF Notes Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 10px;
    }
    .chapter-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 20px 0 15px 0;
    }
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        font-weight: 600;
        text-align: center;
        margin: 15px 0;
    }
    .info-card {
        background: #16213e;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #667eea;
    }
    .info-card h3 {
        color: #667eea;
        font-size: 2rem;
        margin: 0;
    }
    .info-card p {
        color: #aaa;
        margin: 5px 0 0 0;
    }
    .highlight-box {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid #667eea;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 30px;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
    }
    .footer {
        text-align: center;
        color: #555;
        padding: 20px;
        margin-top: 40px;
        border-top: 1px solid #222;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# PDF EXTRACTOR CLASS
# ============================================================
class PDFExtractor:

    def extract_text_pdfplumber(self, pdf_file):
        full_text = ""
        page_texts = []
        try:
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        page_texts.append({
                            "page": page_num + 1,
                            "text": text
                        })
                        full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
            return full_text, page_texts, total_pages
        except Exception as e:
            return None, None, 0

    def extract_text_pypdf2(self, pdf_file):
        full_text = ""
        page_texts = []
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(reader.pages)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    page_texts.append({
                        "page": page_num + 1,
                        "text": text
                    })
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
            return full_text, page_texts, total_pages
        except Exception as e:
            return None, None, 0

    def detect_chapters(self, text):
        chapter_patterns = [
            r'Chapter\s+\d+',
            r'CHAPTER\s+\d+',
            r'Chapter\s+[IVXLCDM]+',
            r'Unit\s+\d+',
            r'UNIT\s+\d+',
            r'Section\s+\d+',
            r'SECTION\s+\d+',
            r'Part\s+\d+',
            r'Module\s+\d+',
            r'Lesson\s+\d+',
        ]
        found_chapters = []
        for pattern in chapter_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_chapters.extend(matches)
        return len(found_chapters) > 1, list(set(found_chapters))

    def split_by_chapters(self, text):
        chapter_pattern = r'(Chapter\s+\d+[^\n]*|CHAPTER\s+\d+[^\n]*|Unit\s+\d+[^\n]*|UNIT\s+\d+[^\n]*|Section\s+\d+[^\n]*|Part\s+\d+[^\n]*|Module\s+\d+[^\n]*|Lesson\s+\d+[^\n]*)'
        parts = re.split(chapter_pattern, text, flags=re.IGNORECASE)
        chapters = []
        i = 1
        while i < len(parts):
            chapter_title = parts[i].strip()
            chapter_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if chapter_content and len(chapter_content) > 100:
                chapters.append({
                    "title": chapter_title,
                    "content": chapter_content
                })
            i += 2
        if not chapters and parts:
            chapters.append({
                "title": "Document Content",
                "content": text
            })
        return chapters


# ============================================================
# AI NOTES GENERATOR CLASS - UPDATED MODELS
# ============================================================
class NotesGenerator:

    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = None
        self.model_name = ""

        # ✅ Updated model list - Latest working models
        models_to_try = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash-latest',
            'gemini-1.5-pro-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro',
        ]

        for model_name in models_to_try:
            try:
                test_model = genai.GenerativeModel(model_name)
                test_response = test_model.generate_content("Say hello")
                if test_response:
                    self.model = test_model
                    self.model_name = model_name
                    break
            except Exception:
                continue

        if self.model is None:
            st.error("❌ No Gemini model found. Please check your API key!")

    def generate_notes_for_chapter(self, chapter_title,
                                    chapter_content, notes_style, language):
        style_prompts = {
            "Detailed": "comprehensive and detailed",
            "Concise": "brief and concise (bullet points only)",
            "Mind Map Style": "mind map style with main topics and sub-topics",
            "Q&A Format": "question and answer format",
            "Exam Ready": "exam-focused with important definitions and key points"
        }
        style_desc = style_prompts.get(notes_style, "comprehensive")

        prompt = f"""
        You are an expert educator and note-maker.
        Create {style_desc} study notes from the following content.

        Chapter/Section: {chapter_title}

        Content:
        {chapter_content[:8000]}

        Instructions:
        1. Extract ONLY the most important information
        2. Remove all unnecessary filler content
        3. Organize information clearly
        4. Use bullet points for key facts
        5. Mark definitions with "📌 Definition:"
        6. Mark formulas with "📐 Formula:"
        7. Mark key concepts with "🔑 Key Concept:"
        8. Mark examples with "💡 Example:"
        9. Add "⚠️ Important:" for critical points
        10. Create "📝 Quick Summary" at the end
        11. Write in {language} language

        Format beautifully with emojis and clear structure.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_notes_no_chapters(self, full_text, notes_style, language):
        style_prompts = {
            "Detailed": "comprehensive and detailed",
            "Concise": "brief and concise",
            "Mind Map Style": "mind map style",
            "Q&A Format": "question and answer format",
            "Exam Ready": "exam-focused"
        }
        style_desc = style_prompts.get(notes_style, "comprehensive")

        prompt = f"""
        You are an expert educator and note-maker.
        Create {style_desc} study notes from this document.

        Content:
        {full_text[:10000]}

        Instructions:
        1. Identify and organize main topics
        2. Extract ONLY important information
        3. Create proper sections
        4. Use bullet points
        5. Mark definitions with "📌 Definition:"
        6. Mark formulas with "📐 Formula:"
        7. Mark concepts with "🔑 Key Concept:"
        8. Mark examples with "💡 Example:"
        9. Add "⚠️ Important:" for critical points
        10. Create "📝 Quick Summary" at end
        11. Write in {language} language

        Format beautifully with proper structure.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_key_points(self, full_text, language):
        prompt = f"""
        From this content extract:
        1. Top 10 most important key points
        2. 5 most important definitions
        3. Critical formulas or rules
        4. Common exam questions

        Content: {full_text[:5000]}
        Language: {language}

        Use clear sections, bullet points and emojis.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_flashcards(self, full_text, language):
        prompt = f"""
        Create 15 flashcards for quick revision.

        Format:
        🃏 CARD [NUMBER]
        Q: [Question]
        A: [Answer]
        ---

        Content: {full_text[:5000]}
        Language: {language}

        Make diverse questions - definitions, concepts, applications.
        Keep answers concise but complete.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_pdf_info(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        info = {
            "pages": len(reader.pages),
            "title": reader.metadata.get('/Title', 'Unknown') if reader.metadata else 'Unknown',
            "author": reader.metadata.get('/Author', 'Unknown') if reader.metadata else 'Unknown',
        }
        return info
    except:
        return {"pages": "Unknown", "title": "Unknown", "author": "Unknown"}


def create_download_text(notes_data, has_chapters):
    content = "=" * 60 + "\n"
    content += "📚 SMART STUDY NOTES\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    content += "=" * 60 + "\n\n"
    if has_chapters:
        for chapter in notes_data:
            content += f"\n{'=' * 40}\n"
            content += f"📖 {chapter['title']}\n"
            content += f"{'=' * 40}\n\n"
            content += chapter['notes'] + "\n\n"
    else:
        content += notes_data + "\n"
    return content


def estimate_reading_time(text):
    words = len(text.split())
    minutes = words // 200
    return max(1, minutes)


# ============================================================
# MAIN APP
# ============================================================
def main():

    # HEADER
    st.markdown("""
    <div class="main-header">
        <h1>📚 Smart PDF Notes Generator</h1>
        <p>Upload any PDF → Get Beautiful Study Notes with AI</p>
    </div>
    """, unsafe_allow_html=True)

    # SIDEBAR
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        st.markdown("---")

        st.markdown("### 🔑 Gemini API Key")
        api_key = st.text_input(
            "Enter Google Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Get free key from: aistudio.google.com"
        )

        if not api_key:
            st.warning("⚠️ Enter Gemini API Key")
            st.markdown("**Get Free API Key:**")
            st.markdown("🔗 [Google AI Studio](https://aistudio.google.com/app/apikey)")
        else:
            st.success("✅ API Key Added!")

        st.markdown("---")

        st.markdown("### 📝 Notes Style")
        notes_style = st.selectbox(
            "Choose Format",
            ["Detailed", "Concise", "Mind Map Style", "Q&A Format", "Exam Ready"]
        )

        st.markdown("### 🌍 Language")
        language = st.selectbox(
            "Notes Language",
            ["English", "Hindi", "Hinglish", "Gujarati",
             "Marathi", "Bengali", "Tamil"]
        )

        st.markdown("---")
        st.markdown("### 🎯 Extra Features")
        generate_flashcards = st.checkbox("🃏 Flashcards", value=True)
        generate_keypoints = st.checkbox("🔑 Key Points", value=True)

        st.markdown("---")
        st.markdown("""
        <div style='background:#1a1a2e; padding:15px;
                    border-radius:10px; border:1px solid #667eea;'>
            <h4 style='color:#667eea; margin:0 0 10px 0;'>✨ Features</h4>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Any PDF size</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Chapter-wise notes</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ AI powered</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Multiple formats</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Download notes</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Flashcards</p>
            <p style='color:#aaa; font-size:0.85rem;'>✅ Multi-language</p>
        </div>
        """, unsafe_allow_html=True)

    # FILE UPLOAD
    st.markdown("### 📄 Upload Your PDF")
    uploaded_file = st.file_uploader(
        "Drop PDF here or click to browse",
        type=['pdf'],
        help="Supports all PDF sizes!"
    )

    if uploaded_file is not None:

        pdf_bytes = uploaded_file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_info = get_pdf_info(pdf_file)

        st.markdown("---")
        st.markdown("### 📊 PDF Information")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class='info-card'>
                <h3>📄 {pdf_info['pages']}</h3>
                <p>Total Pages</p>
            </div>""", unsafe_allow_html=True)

        with col2:
            size_kb = len(pdf_bytes) / 1024
            size_display = (f"{size_kb:.1f} KB"
                           if size_kb < 1024
                           else f"{size_kb/1024:.1f} MB")
            st.markdown(f"""
            <div class='info-card'>
                <h3>💾 {size_display}</h3>
                <p>File Size</p>
            </div>""", unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class='info-card'>
                <h3>📝</h3>
                <p>{notes_style}</p>
            </div>""", unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class='info-card'>
                <h3>🌍</h3>
                <p>{language}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            generate_btn = st.button(
                "🚀 Generate Smart Notes",
                disabled=not api_key,
                use_container_width=True
            )

        if not api_key:
            st.error("❌ Please enter Gemini API Key in sidebar!")

        if generate_btn and api_key:

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Extract Text
            status_text.markdown("### 📖 Extracting text from PDF...")
            progress_bar.progress(10)

            extractor = PDFExtractor()

            pdf_file = io.BytesIO(pdf_bytes)
            full_text, page_texts, total_pages = \
                extractor.extract_text_pdfplumber(pdf_file)

            if not full_text:
                pdf_file = io.BytesIO(pdf_bytes)
                full_text, page_texts, total_pages = \
                    extractor.extract_text_pypdf2(pdf_file)

            if not full_text:
                st.error("❌ Could not extract text. Make sure PDF has text, not scanned images.")
                return

            progress_bar.progress(25)
            status_text.markdown(f"### ✅ Extracted {total_pages} pages!")
            time.sleep(0.5)

            # Detect Chapters
            status_text.markdown("### 🔍 Detecting structure...")
            progress_bar.progress(35)
            has_chapters, chapter_list = extractor.detect_chapters(full_text)

            # Initialize AI
            status_text.markdown("### 🤖 Connecting to Gemini AI...")
            try:
                generator = NotesGenerator(api_key)
                if generator.model is None:
                    st.error("❌ Could not connect to Gemini AI. Check API key!")
                    return
                status_text.markdown(f"### ✅ Connected! Using: {generator.model_name}")
                time.sleep(0.5)
            except Exception as e:
                st.error(f"❌ API Error: {str(e)}")
                return

            # Generate Notes
            all_notes_data = []

            if has_chapters:
                chapters = extractor.split_by_chapters(full_text)
                total_chapters = len(chapters)
                status_text.markdown(
                    f"### 📚 Found {total_chapters} chapters! Generating notes..."
                )
                progress_bar.progress(40)

                for idx, chapter in enumerate(chapters):
                    chapter_progress = 40 + int((idx / total_chapters) * 45)
                    progress_bar.progress(chapter_progress)
                    status_text.markdown(
                        f"### 📝 Chapter {idx+1}/{total_chapters}: {chapter['title']}"
                    )

                    notes = generator.generate_notes_for_chapter(
                        chapter['title'],
                        chapter['content'],
                        notes_style,
                        language
                    )
                    all_notes_data.append({
                        "title": chapter['title'],
                        "notes": notes,
                        "word_count": len(chapter['content'].split())
                    })
                    time.sleep(1)

            else:
                status_text.markdown("### 📝 Generating complete notes...")
                progress_bar.progress(50)

                chunk_size = 8000
                text_chunks = [
                    full_text[i:i+chunk_size]
                    for i in range(0, len(full_text), chunk_size)
                ]

                if len(text_chunks) > 1:
                    combined_notes = ""
                    for chunk_idx, chunk in enumerate(text_chunks[:5]):
                        chunk_progress = 50 + int(
                            (chunk_idx / len(text_chunks[:5])) * 35
                        )
                        progress_bar.progress(chunk_progress)
                        status_text.markdown(
                            f"### 📝 Section {chunk_idx+1}/{min(len(text_chunks),5)}..."
                        )
                        notes = generator.generate_notes_no_chapters(
                            chunk, notes_style, language
                        )
                        combined_notes += f"\n\n{notes}"
                        time.sleep(1)
                    main_notes = combined_notes
                else:
                    main_notes = generator.generate_notes_no_chapters(
                        full_text, notes_style, language
                    )

                all_notes_data = main_notes

            progress_bar.progress(88)

            # Extra Features
            key_points_text = ""
            flashcards_text = ""

            if generate_keypoints:
                status_text.markdown("### 🔑 Generating key points...")
                key_points_text = generator.generate_key_points(full_text, language)
                time.sleep(1)

            if generate_flashcards:
                status_text.markdown("### 🃏 Creating flashcards...")
                flashcards_text = generator.generate_flashcards(full_text, language)
                time.sleep(1)

            progress_bar.progress(100)
            status_text.markdown("### ✅ Done!")
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()

            # SUCCESS MESSAGE
            st.markdown("""
            <div class='success-box'>
                🎉 Your Smart Study Notes are Ready!
            </div>
            """, unsafe_allow_html=True)

            # TABS
            tabs_list = ["📚 Full Notes"]
            if generate_keypoints:
                tabs_list.append("🔑 Key Points")
            if generate_flashcards:
                tabs_list.append("🃏 Flashcards")
            tabs_list.append("⬇️ Download")

            tabs = st.tabs(tabs_list)
            tab_index = 0

            # TAB: FULL NOTES
            with tabs[tab_index]:
                tab_index += 1
                if has_chapters:
                    st.markdown(f"### 📚 {len(all_notes_data)} Chapter Notes")
                    for chapter_data in all_notes_data:
                        st.markdown(f"""
                        <div class='chapter-header'>
                            📖 {chapter_data['title']}
                        </div>""", unsafe_allow_html=True)

                        st.markdown(f"""
                        <div class='highlight-box'>
                            <small>📊 Words: {chapter_data['word_count']:,}</small>
                        </div>""", unsafe_allow_html=True)

                        with st.expander(
                            f"📝 {chapter_data['title']}", expanded=True
                        ):
                            st.markdown(chapter_data['notes'])
                        st.markdown("---")
                else:
                    st.markdown("### 📄 Complete Document Notes")
                    st.markdown(all_notes_data)

            # TAB: KEY POINTS
            if generate_keypoints:
                with tabs[tab_index]:
                    tab_index += 1
                    st.markdown("### 🔑 Key Points & Quick Revision")
                    st.markdown(key_points_text)

            # TAB: FLASHCARDS
            if generate_flashcards:
                with tabs[tab_index]:
                    tab_index += 1
                    st.markdown("### 🃏 Flashcards")
                    if flashcards_text:
                        cards = flashcards_text.split("---")
                        for i, card in enumerate(cards):
                            if card.strip() and "CARD" in card:
                                with st.expander(f"🃏 Card {i+1}"):
                                    st.markdown(card.strip())
                        if len(cards) <= 1:
                            st.markdown(flashcards_text)

            # TAB: DOWNLOAD
            with tabs[tab_index]:
                st.markdown("### ⬇️ Download Notes")
                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    download_content = create_download_text(
                        all_notes_data, has_chapters
                    )
                    st.download_button(
                        "📥 Download Notes (.txt)",
                        data=download_content,
                        file_name=f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                with col_d2:
                    if key_points_text:
                        st.download_button(
                            "📥 Download Key Points (.txt)",
                            data=key_points_text,
                            file_name=f"keypoints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                if flashcards_text:
                    st.download_button(
                        "📥 Download Flashcards (.txt)",
                        data=flashcards_text,
                        file_name=f"flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

    else:
        # WELCOME SCREEN
        st.markdown("""
        <div style='text-align:center; padding:50px 20px;'>
            <h2 style='color:#667eea;'>👆 Upload a PDF to Get Started</h2>
            <p style='color:#888; font-size:1.1rem;'>
                Textbooks, research papers, any PDF supported!
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class='info-card'>
                <h3>📖</h3>
                <h4 style='color:#667eea;'>Chapter Detection</h4>
                <p>Auto detects chapters and creates organized notes</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class='info-card'>
                <h3>🤖</h3>
                <h4 style='color:#667eea;'>AI Powered</h4>
                <p>Gemini AI extracts only important information</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class='info-card'>
                <h3>🃏</h3>
                <h4 style='color:#667eea;'>Flashcards</h4>
                <p>Auto generates flashcards for exam prep</p>
            </div>""", unsafe_allow_html=True)

    # FOOTER
    st.markdown("""
    <div class='footer'>
        <p>📚 Smart PDF Notes Generator | Powered by Google Gemini AI</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    main()
