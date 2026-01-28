import streamlit as st
import requests
import json
import os
import re
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="LegalGuard AI - Enterprise Legal Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI (as you already have) …
st.markdown("""
<style>
  /* your existing CSS … */
</style>
""", unsafe_allow_html=True)

API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')

class StreamlitRichRenderer:
    @staticmethod
    def print_welcome_banner(pii_enabled: bool):
        mode_text = "🛡️ PRIVACY MODE" if pii_enabled else "⚡ FAST MODE"
        mode_color = "#FFD700" if pii_enabled else "#50C878"
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid {mode_color};
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        ">
            <h1 style="color: white; margin: 0; font-size: 2.5em;">⚖️ LEGALGUARD AI</h1>
            <p style="color: #4A90E2; margin: 5px 0; font-size: 1.2em; font-weight: bold;">
                Legal Document Analysis System
            </p>
            <div style="color: {mode_color}; font-weight: bold; font-size: 1.1em; margin: 10px 0;">
                {mode_text}
            </div>
            <p style="color: #50C878; margin: 5px 0;">AI-Powered • Professional</p>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def print_pii_status(pii_entities: list, pii_enabled: bool):
        if not pii_entities:
            return
        status_text = "detected and redacted" if pii_enabled else "found (not redacted)"
        badge_class = "badge-warning" if pii_enabled else "badge-info"
        st.markdown(f"""
        <div class="rich-panel {'panel-privacy' if pii_enabled else 'panel-fast'}">
            <div style="margin-bottom: 10px;">
                <strong>{'🛡️ Privacy Guard Active' if pii_enabled else '🔍 PII Visibility Mode'}</strong>
            </div>
            <span class="status-badge {badge_class}">
                🔒 {len(pii_entities)} sensitive items {status_text}
            </span>
            <span class="status-badge {badge_class}">
                📋 Types: {[entity['label'] for entity in pii_entities]}
            </span>
        </div>""", unsafe_allow_html=True)

    @staticmethod
    def print_final_answer(answer: str, pii_enabled: bool):
        mode_indicator = "Privacy-First Analysis" if pii_enabled else "Full-Data Analysis"
        st.markdown(f"""
        <div class="rich-panel panel-answer">
            <div style="margin-bottom: 15px;"><strong>💎 LegalGuard AI - {mode_indicator}</strong></div>
        """, unsafe_allow_html=True)
        st.markdown(answer)
        st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pii_enabled" not in st.session_state:
    st.session_state.pii_enabled = True
if "thinking_steps" not in st.session_state:
    st.session_state.thinking_steps = []

# Sidebar
with st.sidebar:
    st.title("⚖️ LegalGuard AI")
    st.subheader("🛡️ Privacy Settings")
    pii_toggle = st.checkbox("Enable PII Protection", value=st.session_state.pii_enabled)
    st.session_state.pii_enabled = pii_toggle
    st.markdown("---")
    st.subheader("💬 Session Info")
    st.write(f"Messages: {len(st.session_state.messages)}")
    st.write(f"Thinking Steps: {len(st.session_state.thinking_steps)}")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.thinking_steps = []
        st.rerun()

# Main Interface
StreamlitRichRenderer.print_welcome_banner(st.session_state.pii_enabled)
st.markdown("Ask questions about your legal documents with AI-powered analysis and privacy protection.")

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "processing_time" in msg:
            st.caption(f"Processed in {msg['processing_time']} seconds")

# Input prompt
prompt = st.chat_input("Ask a question about your legal documents...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Reset thinking steps
    st.session_state.thinking_steps = []

    # Make API request
    payload = {"query": prompt, "activate_pii_detector": st.session_state.pii_enabled}
    with st.spinner("🔍 Analyzing legal documents..."):
        try:
            resp = requests.post(f"{API_BASE_URL}/query", json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
        else:
            # Show PII status if any
            if result.get("pii_detected"):
                st.session_state.thinking_steps.append({
                    "type": "pii_status",
                    "entities": result["pii_detected"],
                    "pii_enabled": st.session_state.pii_enabled
                })

            # Add assistant answer
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "processing_time": result["processing_time"]
            })

            with st.chat_message("assistant"):
                StreamlitRichRenderer.print_final_answer(result["answer"], st.session_state.pii_enabled)
                st.caption(f"Processed in {result['processing_time']} seconds")

    st.rerun()
