# app.py
import re
import streamlit as st

# ------------- Instant UI -------------
st.set_page_config(page_title="Instant Summarizer", layout="centered")
st.title("⚡ Instant Summarizer (opens immediately)")
st.caption("Paste text below and click Summarize. File upload is optional and disabled by default to keep startup instant.")

# ------------- Tiny, fast summarizer (no ML, no extra imports) -------------
STOPWORDS = {
    "the","a","an","and","or","but","if","then","else","when","while","for","to","of","in","on","at",
    "from","by","with","about","as","into","like","through","after","over","between","out","against",
    "during","without","before","under","around","among","is","are","was","were","be","been","being",
    "this","that","these","those","it","its","i","you","he","she","they","we","my","your","their",
    "our","me","him","her","them","us","do","does","did","doing","done","can","could","should","would",
    "may","might","must","will","just","than","so","such","not","no","nor","very"
}

def _clean(s: str) -> str:
    s = re.sub(r"-\s*\n\s*", "", s)     # infor-\nmation -> information
    s = re.sub(r"\s*\n\s*", " ", s)     # newlines -> spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _split_sentences(text: str):
    text = _clean(text)
    # split at sentence enders or before inline bullets (• or -)
    parts = re.split(r"(?<=[.!?])\s+|(?=•\s)|(?=-\s)", text)
    return [p.strip().lstrip("•- ").strip() for p in parts if len(p.strip()) > 2]

def _word_freq(text: str):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    freqs = {}
    for w in words:
        if w in STOPWORDS:
            continue
        freqs[w] = freqs.get(w, 0) + 1
    if not freqs:
        return {}
    m = max(freqs.values())
    return {k: v / m for k, v in freqs.items()}

def summarize(text: str, n: int) -> list[str]:
    sents = _split_sentences(text)
    if not sents:
        return []
    if len(sents) <= n:
        return sents
    freqs = _word_freq(text)
    if not freqs:
        return sents[:n]
    scores = []
    for i, s in enumerate(sents):
        words = re.findall(r"[a-zA-Z]+", s.lower())
        score = sum(freqs.get(w, 0.0) for w in words) / max(len(words), 1) if words else 0.0
        scores.append((i, score))
    top = sorted(scores, key=lambda x: x[1], reverse=True)[:n]
    top_sorted = sorted(top, key=lambda x: x[0])  # keep original order
    return [sents[i] for i, _ in top_sorted]

def _end_at_sentence(text: str) -> str:
    m = re.search(r"[.!?](?=[^.!?]*$)", text)
    return text[:m.end()].strip() if m else text.strip()

# ------------- Sidebar controls -------------
with st.sidebar:
    target = st.slider("Summary length (sentences)", 3, 20, 10, 1)
    style = st.radio("Output style", ["Bullet points", "Paragraph"], index=0)
    show_upload = st.checkbox("Enable file upload (off = fastest startup)", value=False)

# ------------- A) Instant: pasted text -------------
st.subheader("Paste text")
text = st.text_area("Paste text and click Summarize:", height=160, placeholder="Paste 2–5 paragraphs…")
if st.button("Summarize pasted text"):
    sentences = summarize(text or "", target)

    st.subheader("✅ Final Summary (pasted text)")
    if sentences:
        if style == "Bullet points":
            # one bullet per line (real Markdown list)
            for s in sentences:
                st.markdown(f"- {s}")
            st.download_button("📥 Download Summary", "\n".join(sentences), file_name="summary.txt")
        else:
            paragraph = _end_at_sentence(" ".join(sentences))
            st.write(paragraph)
            st.download_button("📥 Download Summary", paragraph, file_name="summary.txt")
    else:
        st.info("No summary could be generated. Paste more text and try again.")

st.markdown("---")

# ------------- B) Optional: file upload (imports only after enabled) -------------
if show_upload:
    st.subheader("Upload file (PDF / DOCX / TXT)")
    uploaded = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])
    if uploaded:
        ext = uploaded.name.rsplit(".", 1)[-1].lower()

        def _extract(u, e) -> str:
            if e == "txt":
                try:
                    return u.read().decode("utf-8", errors="ignore")
                except Exception:
                    return ""
            if e == "docx":
                try:
                    import docx  # imported only when needed
                    d = docx.Document(u)
                    return "\n".join(p.text for p in d.paragraphs)
                except Exception:
                    return ""
            if e == "pdf":
                # Try PyMuPDF (fast), else PyPDF2
                try:
                    import fitz  # imported only when needed
                    data = u.read()
                    with fitz.open(stream=data, filetype="pdf") as doc:
                        return "\n".join(p.get_text("text") for p in doc)
                except Exception:
                    try:
                        from PyPDF2 import PdfReader
                        u.seek(0)
                        r = PdfReader(u)
                        return "\n".join((pg.extract_text() or "") for pg in r.pages)
                    except Exception:
                        return ""
            return ""

        raw = _extract(uploaded, ext)
        cleaned = _clean(raw)

        st.subheader("✅ Final Summary (uploaded file)")
        if cleaned:
            sentences = summarize(cleaned, target)
            if sentences:
                if style == "Bullet points":
                    for s in sentences:
                        st.markdown(f"- {s}")
                    st.download_button("📥 Download Summary (file)", "\n".join(sentences), file_name="summary_from_file.txt")
                else:
                    paragraph = _end_at_sentence(" ".join(sentences))
                    st.write(paragraph)
                    st.download_button("📥 Download Summary (file)", paragraph, file_name="summary_from_file.txt")
            else:
                st.info("Could not generate a summary from this file. Try increasing sentence count.")
        else:
            st.error("No selectable text found. If your PDF is scanned (images), OCR it first and retry.")
# Safety: ensure 'cleaned' exists even if extraction failed
if 'cleaned' not in locals():
    cleaned = ""
