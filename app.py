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
# CUSTOM CSS STYLING
# ============================================================
st.markdown("""
<style>
    /* Main Background */
    .main {
        background-color: #0e1117;
    }
    
    /* Header Style */
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
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 10px;
    }
    
    /* Upload Box */
    .upload-section {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px dashed #667eea;
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Notes Container */
    .notes-container {
        background: #1a1a2e;
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* Chapter Header */
    .chapter-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 20px 0 15px 0;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Success Box */
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        font-weight: 600;
        text-align: center;
        margin: 15px 0;
    }
    
    /* Info Cards */
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
        font-size: 0.9rem;
    }
    
    /* Progress Bar Color */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Button Style */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 30px;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar Style */
    .css-1d391kg {
        background-color: #1a1a2e;
    }
    
    /* Tab Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #1a1a2e;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #16213e;
        border-radius: 10px;
        color: white;
        padding: 10px 20px;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
    }
    ::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 4px;
    }
    
    .highlight-box {
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid #667eea;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
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
# PDF TEXT EXTRACTION CLASS
# ============================================================
class PDFExtractor:
    
    def extract_text_pdfplumber(self, pdf_file):
        """Extract text using pdfplumber - better for complex PDFs"""
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
        """Fallback extraction using PyPDF2"""
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
        """Detect if PDF has chapters"""
        chapter_patterns = [
            r'Chapter\s+\d+',
            r'CHAPTER\s+\d+',
            r'Chapter\s+[IVXLCDM]+',
            r'CHAPTER\s+[IVXLCDM]+',
            r'Unit\s+\d+',
            r'UNIT\s+\d+',
            r'Section\s+\d+',
            r'SECTION\s+\d+',
            r'Part\s+\d+',
            r'PART\s+[IVXLCDM]+',
            r'Module\s+\d+',
            r'Lesson\s+\d+',
            r'Topic\s+\d+',
        ]
        
        found_chapters = []
        for pattern in chapter_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_chapters.extend(matches)
        
        return len(found_chapters) > 1, list(set(found_chapters))
    
    def split_by_chapters(self, text):
        """Split text into chapters"""
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
# AI NOTES GENERATOR CLASS
# ============================================================
class NotesGenerator:
    
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_notes_for_chapter(self, chapter_title, chapter_content, notes_style, language):
        """Generate structured notes for a chapter"""
        
        style_prompts = {
            "Detailed": "comprehensive and detailed",
            "Concise": "brief and concise (bullet points only)",
            "Mind Map Style": "mind map style with main topics and sub-topics",
            "Q&A Format": "question and answer format",
            "Exam Ready": "exam-focused with important definitions, formulas, and key points highlighted"
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
        3. Organize information in a clear, structured format
        4. Use bullet points for key facts
        5. Highlight definitions with "📌 Definition:"
        6. Mark important formulas with "📐 Formula:"
        7. Mark key concepts with "🔑 Key Concept:"
        8. Mark examples with "💡 Example:"
        9. Add "⚠️ Important:" for critical points
        10. Create a "📝 Quick Summary" at the end
        11. Write notes in {language} language
        
        Format the notes beautifully with proper sections and emojis.
        Make sure notes are student-friendly and easy to understand.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating notes: {str(e)}"
    
    def generate_notes_no_chapters(self, full_text, notes_style, language):
        """Generate notes when no chapters detected"""
        
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
        Create {style_desc} study notes from the following document content.
        
        Content:
        {full_text[:10000]}
        
        Instructions:
        1. Identify and organize main topics automatically
        2. Extract ONLY the most important information
        3. Create proper sections based on content flow
        4. Use bullet points for key facts
        5. Highlight definitions with "📌 Definition:"
        6. Mark important formulas with "📐 Formula:"
        7. Mark key concepts with "🔑 Key Concept:"
        8. Mark examples with "💡 Example:"
        9. Add "⚠️ Important:" for critical points
        10. Create a "📝 Quick Summary" at the end
        11. Write notes in {language} language
        12. Add topic headers for each main topic
        
        Format beautifully with proper structure.
        Make notes student-friendly and comprehensive.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating notes: {str(e)}"
    
    def generate_key_points(self, full_text, language):
        """Generate overall key points"""
        
        prompt = f"""
        From the following content, extract:
        1. Top 10 most important key points
        2. 5 most important definitions
        3. Critical formulas or rules (if any)
        4. Common exam questions that might be asked
        
        Content: {full_text[:5000]}
        
        Language: {language}
        
        Format with clear sections and bullet points.
        Use emojis to make it visually appealing.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def generate_flashcards(self, full_text, language):
        """Generate flashcards for quick revision"""
        
        prompt = f"""
        Create 15 flashcards from this content for quick revision.
        
        Format each flashcard as:
        
        🃏 CARD [NUMBER]
        Q: [Question]
        A: [Answer]
        ---
        
        Content: {full_text[:5000]}
        Language: {language}
        
        Make questions diverse - definitions, concepts, applications.
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
    """Get basic PDF information"""
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
    """Create downloadable text file content"""
    content = "=" * 60 + "\n"
    content += "📚 SMART STUDY NOTES\n"
    content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
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
    """Estimate reading time in minutes"""
    words = len(text.split())
    minutes = words // 200
    return max(1, minutes)


# ============================================================
# MAIN APP
# ============================================================
def main():
    
    # ---- HEADER ----
    st.markdown("""
    <div class="main-header">
        <h1>📚 Smart PDF Notes Generator</h1>
        <p>Upload any PDF → Get Beautiful Study Notes Instantly with AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ---- SIDEBAR ----
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        st.markdown("---")
        
        # API Key Input
        st.markdown("### 🔑 Gemini API Key")
        api_key = st.text_input(
            "Enter your Google Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Get free API key from: aistudio.google.com"
        )
        
        if not api_key:
            st.warning("⚠️ Please enter Gemini API Key to generate notes")
            st.markdown("**Get Free API Key:**")
            st.markdown("🔗 [Google AI Studio](https://aistudio.google.com/app/apikey)")
        else:
            st.success("✅ API Key Added!")
        
        st.markdown("---")
        
        # Notes Style
        st.markdown("### 📝 Notes Style")
        notes_style = st.selectbox(
            "Choose Notes Format",
            ["Detailed", "Concise", "Mind Map Style", "Q&A Format", "Exam Ready"],
            index=0
        )
        
        # Language
        st.markdown("### 🌍 Language")
        language = st.selectbox(
            "Notes Language",
            ["English", "Hindi", "Hinglish", "Gujarati", "Marathi", "Bengali", "Tamil"],
            index=0
        )
        
        # Features
        st.markdown("---")
        st.markdown("### 🎯 Extra Features")
        generate_flashcards = st.checkbox("🃏 Generate Flashcards", value=True)
        generate_keypoints = st.checkbox("🔑 Key Points Summary", value=True)
        
        st.markdown("---")
        
        # Info Box
        st.markdown("""
        <div style='background:#1a1a2e; padding:15px; border-radius:10px; border:1px solid #667eea;'>
            <h4 style='color:#667eea; margin:0 0 10px 0;'>✨ Features</h4>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Any PDF size supported</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Chapter-wise notes</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ AI-powered extraction</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Multiple formats</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Download notes</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Flashcards</p>
            <p style='color:#aaa; font-size:0.85rem; margin:3px 0;'>✅ Multi-language</p>
        </div>
        """, unsafe_allow_html=True)
    
    # ---- MAIN CONTENT ----
    
    # File Upload Section
    st.markdown("### 📄 Upload Your PDF")
    
    uploaded_file = st.file_uploader(
        "Drop your PDF here or click to browse",
        type=['pdf'],
        help="Supports all PDF sizes - textbooks, notes, research papers, etc."
    )
    
    if uploaded_file is not None:
        
        # PDF Info Cards
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
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            size_kb = len(pdf_bytes) / 1024
            size_display = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            st.markdown(f"""
            <div class='info-card'>
                <h3>💾 {size_display}</h3>
                <p>File Size</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class='info-card'>
                <h3>📝 {notes_style[:8]}</h3>
                <p>Notes Style</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class='info-card'>
                <h3>🌍 {language[:6]}</h3>
                <p>Language</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Generate Button
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            generate_btn = st.button(
                "🚀 Generate Smart Notes",
                disabled=not api_key,
                use_container_width=True
            )
        
        if not api_key:
            st.error("❌ Please enter your Gemini API Key in the sidebar first!")
        
        if generate_btn and api_key:
            
            # ---- EXTRACTION PHASE ----
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.markdown("### ⏳ Processing your PDF...")
            
            # Extract Text
            status_text.markdown("### 📖 Extracting text from PDF...")
            progress_bar.progress(10)
            
            extractor = PDFExtractor()
            
            # Try pdfplumber first, then PyPDF2
            pdf_file = io.BytesIO(pdf_bytes)
            full_text, page_texts, total_pages = extractor.extract_text_pdfplumber(pdf_file)
            
            if not full_text:
                pdf_file = io.BytesIO(pdf_bytes)
                full_text, page_texts, total_pages = extractor.extract_text_pypdf2(pdf_file)
            
            if not full_text:
                st.error("❌ Could not extract text from PDF. Please ensure PDF contains text (not scanned images).")
                return
            
            progress_bar.progress(25)
            status_text.markdown(f"### ✅ Extracted text from {total_pages} pages!")
            time.sleep(0.5)
            
            # Detect Chapters
            status_text.markdown("### 🔍 Detecting document structure...")
            progress_bar.progress(35)
            
            has_chapters, chapter_list = extractor.detect_chapters(full_text)
            
            # Initialize Notes Generator
            try:
                generator = NotesGenerator(api_key)
            except Exception as e:
                st.error(f"❌ API Key Error: {str(e)}")
                return
            
            # ---- NOTES GENERATION PHASE ----
            all_notes_data = []
            
            if has_chapters:
                status_text.markdown(f"### 📚 Found {len(chapter_list)} chapters! Generating chapter-wise notes...")
                progress_bar.progress(40)
                
                chapters = extractor.split_by_chapters(full_text)
                total_chapters = len(chapters)
                
                for idx, chapter in enumerate(chapters):
                    chapter_progress = 40 + int((idx / total_chapters) * 45)
                    progress_bar.progress(chapter_progress)
                    status_text.markdown(f"### 📝 Generating notes: {chapter['title']} ({idx+1}/{total_chapters})")
                    
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
                    
                    time.sleep(1)  # Rate limiting
            
            else:
                status_text.markdown("### 📝 No chapters found. Generating complete notes...")
                progress_bar.progress(50)
                
                # Split large text into chunks if needed
                chunk_size = 8000
                text_chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
                
                if len(text_chunks) > 1:
                    combined_notes = ""
                    for chunk_idx, chunk in enumerate(text_chunks[:5]):  # Max 5 chunks
                        chunk_progress = 50 + int((chunk_idx / len(text_chunks[:5])) * 35)
                        progress_bar.progress(chunk_progress)
                        status_text.markdown(f"### 📝 Processing section {chunk_idx+1} of {min(len(text_chunks), 5)}...")
                        
                        notes = generator.generate_notes_no_chapters(chunk, notes_style, language)
                        combined_notes += f"\n\n{notes}"
                        time.sleep(1)
                    
                    main_notes = combined_notes
                else:
                    main_notes = generator.generate_notes_no_chapters(full_text, notes_style, language)
                
                all_notes_data = main_notes
            
            progress_bar.progress(88)
            
            # Generate Extra Features
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
            status_text.markdown("### ✅ Notes Generated Successfully!")
            time.sleep(1)
            
            progress_bar.empty()
            status_text.empty()
            
            # ============================================================
            # DISPLAY RESULTS
            # ============================================================
            
            st.markdown("""
            <div class='success-box'>
                🎉 Your Smart Study Notes are Ready! Scroll down to read them.
            </div>
            """, unsafe_allow_html=True)
            
            # Create Tabs
            if generate_keypoints and generate_flashcards:
                tab1, tab2, tab3, tab4 = st.tabs(["📚 Full Notes", "🔑 Key Points", "🃏 Flashcards", "⬇️ Download"])
            elif generate_keypoints:
                tab1, tab2, tab4 = st.tabs(["📚 Full Notes", "🔑 Key Points", "⬇️ Download"])
                tab3 = None
            elif generate_flashcards:
                tab1, tab3, tab4 = st.tabs(["📚 Full Notes", "🃏 Flashcards", "⬇️ Download"])
                tab2 = None
            else:
                tab1, tab4 = st.tabs(["📚 Full Notes", "⬇️ Download"])
                tab2 = None
                tab3 = None
            
            # ---- TAB 1: FULL NOTES ----
            with tab1:
                
                if has_chapters:
                    st.markdown(f"### 📚 Chapter-wise Notes ({len(all_notes_data)} chapters)")
                    
                    for chapter_data in all_notes_data:
                        st.markdown(f"""
                        <div class='chapter-header'>
                            📖 {chapter_data['title']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class='highlight-box'>
                            <small>📊 Original word count: {chapter_data['word_count']:,} words | 
                            ⏱️ Original reading time: ~{estimate_reading_time(' ' * chapter_data['word_count'])} min</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander(f"📝 View Notes - {chapter_data['title']}", expanded=True):
                            st.markdown(chapter_data['notes'])
                        
                        st.markdown("---")
                
                else:
                    st.markdown("### 📄 Complete Document Notes")
                    
                    total_words = len(full_text.split())
                    st.markdown(f"""
                    <div class='highlight-box'>
                        <small>📊 Total words extracted: {total_words:,} | 
                        ⏱️ Original reading time: ~{estimate_reading_time(full_text)} min</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(all_notes_data)
            
            # ---- TAB 2: KEY POINTS ----
            if tab2 is not None:
                with tab2:
                    st.markdown("### 🔑 Important Key Points & Quick Revision")
                    st.markdown(key_points_text)
            
            # ---- TAB 3: FLASHCARDS ----
            if tab3 is not None:
                with tab3:
                    st.markdown("### 🃏 Flashcards for Quick Revision")
                    
                    if flashcards_text:
                        cards = flashcards_text.split("---")
                        
                        for i, card in enumerate(cards):
                            if card.strip() and "CARD" in card:
                                with st.expander(f"🃏 Flashcard {i+1}", expanded=False):
                                    st.markdown(card.strip())
                        
                        if len(cards) <= 1:
                            st.markdown(flashcards_text)
            
            # ---- TAB 4: DOWNLOAD ----
            with tab4:
                st.markdown("### ⬇️ Download Your Notes")
                
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    # Download Notes as TXT
                    download_content = create_download_text(all_notes_data, has_chapters)
                    
                    st.download_button(
                        label="📥 Download Notes (.txt)",
                        data=download_content,
                        file_name=f"smart_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col_d2:
                    # Download Key Points
                    if key_points_text:
                        st.download_button(
                            label="📥 Download Key Points (.txt)",
                            data=key_points_text,
                            file_name=f"key_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                
                if flashcards_text:
                    st.download_button(
                        label="📥 Download Flashcards (.txt)",
                        data=flashcards_text,
                        file_name=f"flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                st.markdown("""
                <div class='highlight-box'>
                    <p>💡 <strong>Tip:</strong> You can also copy-paste the notes directly from the app into 
                    Word, Notion, Google Docs, or any note-taking app!</p>
                </div>
                """, unsafe_allow_html=True)
    
    else:
        # Welcome Screen
        st.markdown("""
        <div style='text-align:center; padding:50px 20px;'>
            <h2 style='color:#667eea;'>👆 Upload a PDF to Get Started</h2>
            <p style='color:#888; font-size:1.1rem;'>
                Support for textbooks, research papers, notes, any PDF!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature Cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class='info-card'>
                <h3>📖</h3>
                <h4 style='color:#667eea;'>Chapter Detection</h4>
                <p>Automatically detects chapters and creates organized chapter-wise notes</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class='info-card'>
                <h3>🤖</h3>
                <h4 style='color:#667eea;'>AI-Powered</h4>
                <p>Google Gemini AI extracts only the most important information</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class='info-card'>
                <h3>🃏</h3>
                <h4 style='color:#667eea;'>Flashcards</h4>
                <p>Auto-generates flashcards for quick revision and exam preparation</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class='footer'>
        <p>📚 Smart PDF Notes Generator | Powered by Google Gemini AI</p>
        <p style='font-size:0.8rem;'>Built with Streamlit | For Educational Purpose</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# RUN APP
# ============================================================
if __name__ == "__main__":
    main()