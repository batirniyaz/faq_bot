"""Files tab: upload, manage, and preview FAQ documents."""

import base64
import io
from pathlib import Path

import pypdf
import streamlit as st
import docx as python_docx

import rag
import vectorstore

ACCEPTED_TYPES = ["pdf", "docx", "md", "txt"]
UPLOADS_DIR = Path("./uploads")

_EXT_ICON  = {"pdf": "📕", "docx": "📘", "doc": "📘", "md": "📗", "txt": "📄"}
_EXT_COLOR = {"pdf": "#e05252", "docx": "#4a90d9", "doc": "#4a90d9", "md": "#52b788", "txt": "#8a8a9a"}

_CSS = """
<style>
.stat-card {
    background: #0d1421;
    border: 1px solid #1f3a5f;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.stat-number {
    font-size: 2rem;
    font-weight: 700;
    color: #4a90d9;
    line-height: 1.1;
}
.stat-label {
    font-size: 0.78rem;
    color: #6a737d;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.section-title {
    font-size: 0.73rem;
    font-weight: 700;
    color: #4a5568;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin: 22px 0 8px 2px;
}
.empty-box {
    background: #0d1421;
    border: 2px dashed #1f3a5f;
    border-radius: 12px;
    padding: 36px;
    text-align: center;
    color: #4a5568;
    font-size: 0.95rem;
}
.empty-box .icon { font-size: 2.2rem; display: block; margin-bottom: 10px; }
.doc-meta {
    display: flex;
    align-items: center;
    gap: 10px;
}
.doc-icon-lg { font-size: 1.7rem; }
.doc-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.preview-header {
    background: #0d1421;
    border: 1px solid #1f3a5f;
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 14px;
    color: #c9d1d9;
    font-weight: 600;
}
</style>
"""


# ── disk helpers ──────────────────────────────────────────────────────────────

def _save_upload(filename: str, data: bytes):
    UPLOADS_DIR.mkdir(exist_ok=True)
    (UPLOADS_DIR / filename).write_bytes(data)


def _load_upload(filename: str) -> bytes | None:
    p = UPLOADS_DIR / filename
    return p.read_bytes() if p.exists() else None


def _delete_upload(filename: str):
    p = UPLOADS_DIR / filename
    if p.exists():
        p.unlink(missing_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"


def _render_preview(filename: str, file_bytes: bytes):
    ext = _ext(filename)
    icon = _EXT_ICON.get(ext, "📄")
    color = _EXT_COLOR.get(ext, "#8a8a9a")

    st.markdown(
        f'<div class="preview-header">{icon} &nbsp; {filename}</div>',
        unsafe_allow_html=True,
    )

    if ext == "pdf":
        # Chrome blocks data: URIs for PDFs — offer download + text extraction
        col_dl, _ = st.columns([2, 5])
        with col_dl:
            st.download_button(
                "⬇️ Download PDF",
                data=file_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = "\n\n— page break —\n\n".join(
            p.extract_text() or "" for p in reader.pages
        ).strip()
        if text:
            with st.expander("📄 Extracted text", expanded=True):
                st.text_area(
                    "", text, height=480,
                    disabled=True, label_visibility="collapsed",
                )
        else:
            st.info("No extractable text found in this PDF (might be scanned).", icon="ℹ️")

    elif ext in ("docx", "doc"):
        doc = python_docx.Document(io.BytesIO(file_bytes))
        text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        st.text_area("", text, height=480, disabled=True, label_visibility="collapsed")

    elif ext == "md":
        st.markdown(file_bytes.decode("utf-8", errors="replace"))

    else:  # txt
        st.text_area(
            "", file_bytes.decode("utf-8", errors="replace"),
            height=480, disabled=True, label_visibility="collapsed",
        )


# ── main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title("Knowledge Base")

    # persist upload/delete feedback across rerun
    result = st.session_state.pop("upload_result", None)
    if result:
        for msg in result.get("successes", []):
            st.success(msg, icon="✅")
        for msg in result.get("errors", []):
            st.error(msg, icon="❌")

    # ── stats ─────────────────────────────────────────────────────────────────
    docs = vectorstore.list_documents()
    total_chunks = sum(d["chunks"] for d in docs)
    formats = list({_ext(d["filename"]) for d in docs})
    fmt_str = ", ".join(f.upper() for f in formats) if formats else "—"

    c1, c2, c3 = st.columns(3)
    for col, number, label in [
        (c1, len(docs), "Documents"),
        (c2, total_chunks, "Chunks indexed"),
        (c3, fmt_str, "Formats"),
    ]:
        num_style = "font-size:1rem;padding-top:10px" if isinstance(number, str) else ""
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-number" style="{num_style}">{number}</div>'
                f'<div class="stat-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── upload ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Upload new documents</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "files",
        type=ACCEPTED_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        names = "  ·  ".join(f.name for f in uploaded)
        st.caption(f"Selected: {names}")
        if st.button("⚡ Embed & Add to Knowledge Base", type="primary", use_container_width=True):
            successes, errors = [], []
            bar = st.progress(0, text="Starting…")
            for i, f in enumerate(uploaded):
                bar.progress(i / len(uploaded), text=f"Embedding {f.name}…")
                try:
                    data = f.read()
                    _save_upload(f.name, data)
                    doc_id, n = rag.process_upload(data, f.name)
                    successes.append(f"**{f.name}** — {n} chunks indexed")
                except Exception as e:
                    errors.append(f"**{f.name}**: {e}")
            bar.progress(1.0, text="Done!")
            st.session_state.upload_result = {"successes": successes, "errors": errors}
            st.rerun()
    else:
        st.markdown(
            '<div class="empty-box"><span class="icon">📂</span>'
            'Drop files here or click to browse<br>'
            '<span style="font-size:0.82rem;opacity:0.6">PDF · DOCX · MD · TXT</span></div>',
            unsafe_allow_html=True,
        )

    # ── document list ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Indexed documents</div>', unsafe_allow_html=True)

    if not docs:
        st.markdown(
            '<div class="empty-box" style="border-style:solid;">'
            '<span class="icon">🗄️</span>'
            'No documents yet — upload something above</div>',
            unsafe_allow_html=True,
        )
    else:
        for doc in docs:
            ext   = _ext(doc["filename"])
            icon  = _EXT_ICON.get(ext, "📄")
            color = _EXT_COLOR.get(ext, "#8a8a9a")
            on_disk = (UPLOADS_DIR / doc["filename"]).exists()

            with st.container(border=True):
                info_col, view_col, del_col = st.columns([7, 1.2, 1.2])

                with info_col:
                    badge = (
                        f'<span class="doc-badge" '
                        f'style="background:{color}22;color:{color};">{ext.upper()}</span>'
                    )
                    st.markdown(
                        f'<div class="doc-meta">'
                        f'  <span class="doc-icon-lg">{icon}</span>'
                        f'  <div>'
                        f'    <strong style="color:#e2e8f0">{doc["filename"]}</strong><br>'
                        f'    <span style="font-size:0.8rem;color:#6a737d">'
                        f'      {doc["chunks"]} chunks &nbsp; {badge}'
                        f'    </span>'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with view_col:
                    if st.button(
                        "👁 View",
                        key=f"view_{doc['doc_id']}",
                        use_container_width=True,
                        disabled=not on_disk,
                        help="Preview file" if on_disk else "Original file not on disk",
                    ):
                        st.session_state["preview_target"] = doc["filename"]
                        st.rerun()

                with del_col:
                    if st.button(
                        "🗑 Delete",
                        key=f"del_{doc['doc_id']}",
                        use_container_width=True,
                    ):
                        vectorstore.delete_document(doc["doc_id"])
                        _delete_upload(doc["filename"])
                        if st.session_state.get("preview_target") == doc["filename"]:
                            st.session_state.pop("preview_target", None)
                        st.session_state.upload_result = {
                            "successes": [
                                f"**{doc['filename']}** removed ({doc['chunks']} chunks deleted)"
                            ],
                            "errors": [],
                        }
                        st.rerun()

    # ── preview ───────────────────────────────────────────────────────────────
    target = st.session_state.get("preview_target")
    if target:
        data = _load_upload(target)
        if data:
            st.markdown('<div class="section-title">File preview</div>', unsafe_allow_html=True)
            close_col, _ = st.columns([1, 7])
            with close_col:
                if st.button("✕ Close preview", use_container_width=True):
                    st.session_state.pop("preview_target", None)
                    st.rerun()
            _render_preview(target, data)
        else:
            st.session_state.pop("preview_target", None)
