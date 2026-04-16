"""Chat tab: RAG-powered conversational interface."""

import html as html_lib
import streamlit as st

import llm
import vectorstore
from config import TOP_K

_CSS = """
<style>
/* ── page chrome ── */
.chat-header-meta {
    font-size: 0.78rem;
    color: #6a737d;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 2px;
}
/* ── user bubble ── */
.u-row {
    display: flex;
    justify-content: flex-end;
    margin: 6px 0;
}
.u-bubble {
    background: linear-gradient(135deg, #1a4aaa, #1a6acf);
    color: #ffffff;
    padding: 10px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    word-wrap: break-word;
    font-size: 0.94rem;
    line-height: 1.6;
    white-space: pre-wrap;
    box-shadow: 0 2px 8px rgba(26,74,170,0.3);
}
/* ── bot bubble ── */
.b-row {
    display: flex;
    justify-content: flex-start;
    margin: 6px 0;
}
.b-bubble {
    background: #141d2e;
    border: 1px solid #243050;
    color: #c9d1d9;
    padding: 10px 16px;
    border-radius: 18px 18px 18px 4px;
    max-width: 70%;
    word-wrap: break-word;
    font-size: 0.94rem;
    line-height: 1.6;
    white-space: pre-wrap;
}
/* ── thinking bubble ── */
.thinking-row {
    display: flex;
    justify-content: flex-start;
    margin: 6px 0;
}
.thinking-bubble {
    background: #141d2e;
    border: 1px solid #243050;
    color: #6a737d;
    padding: 10px 16px;
    border-radius: 18px 18px 18px 4px;
    font-size: 0.88rem;
    font-style: italic;
}
/* ── dots animation ── */
@keyframes blink { 0%,80%,100%{opacity:0} 40%{opacity:1} }
.dot { display:inline-block; width:5px; height:5px; border-radius:50%;
       background:#6a737d; margin:0 2px; animation: blink 1.4s infinite; }
.dot:nth-child(2){ animation-delay:0.2s; }
.dot:nth-child(3){ animation-delay:0.4s; }
/* ── empty state ── */
.chat-empty {
    text-align: center;
    padding: 64px 20px;
    color: #3d4a5c;
}
.chat-empty .icon { font-size: 2.8rem; display: block; margin-bottom: 12px; }
.chat-empty .hint { font-size: 0.88rem; margin-top: 8px; }
/* ── source pill ── */
.src-pill {
    display: inline-block;
    background: #0d1421;
    border: 1px solid #1f3a5f;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    color: #4a90d9;
    margin: 3px 4px 3px 0;
}
</style>
"""


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "generating" not in st.session_state:
        st.session_state.generating = False


def _user_bubble(text: str):
    st.markdown(
        f'<div class="u-row"><div class="u-bubble">{html_lib.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def _bot_bubble(text: str):
    st.markdown(
        f'<div class="b-row"><div class="b-bubble">{html_lib.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def _thinking_bubble():
    st.markdown(
        '<div class="thinking-row">'
        '  <div class="thinking-bubble">'
        '    <span class="dot"></span>'
        '    <span class="dot"></span>'
        '    <span class="dot"></span>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render():
    _init_state()
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── header ────────────────────────────────────────────────────────────────
    h_col, stat_col, btn_col = st.columns([5, 3, 1.2])
    with h_col:
        st.title("FAQ Chatbot")
    with stat_col:
        doc_count = vectorstore.collection_count()
        msgs = len(st.session_state.messages)
        st.markdown(
            f'<div style="padding-top:22px">'
            f'<span style="font-size:0.8rem;color:#4a5568">'
            f'📚 {doc_count} chunks indexed &nbsp;·&nbsp; 💬 {msgs // 2} exchange(s)'
            f'</span></div>',
            unsafe_allow_html=True,
        )
    with btn_col:
        st.write("")
        if st.session_state.messages:
            if st.button("🗑 Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.pop("last_sources", None)
                st.session_state.generating = False
                st.rerun()

    # no-docs warning
    if doc_count == 0:
        st.info(
            "Knowledge base is empty. Upload documents in the **Files** tab first.",
            icon="ℹ️",
        )

    # ── chat window ───────────────────────────────────────────────────────────
    # Render messages FIRST so user message is always visible during generation
    with st.container(border=True):
        if not st.session_state.messages:
            st.markdown(
                '<div class="chat-empty">'
                '  <span class="icon">🤖</span>'
                '  <strong style="color:#c9d1d9">Ask anything about your documents</strong>'
                '  <div class="hint">Upload PDFs, DOCX, or MD files in the Files tab, then start chatting</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    _user_bubble(msg["content"])
                else:
                    _bot_bubble(msg["content"])

            # Show animated thinking dots while waiting for response
            if st.session_state.generating:
                _thinking_bubble()

    # ── generate response AFTER chat renders (keeps user msg visible) ─────────
    if st.session_state.generating:
        last_q = st.session_state.messages[-1]["content"]
        chunks = vectorstore.query(last_q, top_k=TOP_K) if doc_count > 0 else []
        history = st.session_state.messages[:-1]
        try:
            answer = llm.ask(last_q, chunks, history)
        except Exception as e:
            answer = f"⚠️ Error generating response: {e}"
            chunks = []
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state["last_sources"] = chunks
        st.session_state.generating = False
        st.rerun()

    # ── sources for last answer ───────────────────────────────────────────────
    sources = st.session_state.get("last_sources", [])
    if sources:
        pills = "".join(
            f'<span class="src-pill">📄 {c["filename"]} · {c["score"]}</span>'
            for c in sources
        )
        with st.expander(f"Sources — {len(sources)} relevant chunks", expanded=False):
            st.markdown(f'<div style="margin-bottom:8px">{pills}</div>', unsafe_allow_html=True)
            for i, c in enumerate(sources, 1):
                st.caption(f"**[{i}]** {c['text'][:280]}{'…' if len(c['text']) > 280 else ''}")

    # ── input ─────────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask a question about your documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pop("last_sources", None)
        st.session_state.generating = True
        st.rerun()
