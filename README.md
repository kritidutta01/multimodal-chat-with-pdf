# 📚 Multimodal Chat with PDFs - Text + Image Understanding

Upload a PDF (reports, research papers, scanned docs, manuals) and **chat with it**.  
Unlike most RAG apps, this one is **multimodal**: it understands both the **text** and the **images/figures/tables** inside the document.  

- Ask about text → retrieves relevant passages.  
- Ask about charts, tables, or diagrams → uses OCR + vision-language models.  
- Get a **combined, context-aware answer**.  

---

## 🚀 Features
- 📄 **PDF Text Understanding** – chunked, embedded, and stored in vector DB.  
- 🖼 **Image/Diagram Extraction** – OCR + Vision-Language Model (e.g., LLaVA, GPT-4o, Qwen-VL).  
- 🔍 **Hybrid Retrieval** – retrieves from both text chunks and image captions.  
- 💬 **Multimodal Chat UI** – Streamlit/Gradio app for interactive Q&A.  
- 🐳 **Deployment Ready** – Docker + HuggingFace Spaces configs included.  
- 📊 **Evaluation Built-In** – track relevance, latency, and cost.  

---

## 🏗️ Architecture

PDF → [Text Extraction] → [Embeddings → Vector DB] ┐
[Image Extraction → OCR + Caption + Embeddings] ┘
Query → Hybrid Retrieval (Text + Image) → LLM → Answer


---

## 🎥 Demo
- [Live Demo on HuggingFace Spaces](#) *(coming soon)*  
- Example Q&A:
  - **Q:** What does Figure 2 in the PDF represent?  
  - **A:** It’s a bar chart comparing revenue growth across three regions.  

---

## ⚙️ Installation

```bash
git clone https://github.com/<your-username>/multimodal-chat-with-pdf.git
cd multimodal-chat-with-pdf
pip install -r requirements.txt

# Run locally
streamlit run src/app.py

---

## 🐳 Docker Deployment

You can containerize the app and run it anywhere using Docker.  

### Build the image
```bash
docker build -t multimodal-chat-pdf .




