# =====================================================
# FULL CONFIDENTIALITY CLASSIFIER (ORIGINAL + UPGRADED)
# Run: streamlit run confidentiality_classifier_full.py
# =====================================================

import io
import re
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List

import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document

# -----------------------------
# DATA STRUCTURES
# -----------------------------
@dataclass
class Finding:
    category: str
    count: int
    examples: List[str]
    weight: float

# -----------------------------
# TEXT EXTRACTION
# -----------------------------
def extract_text(uploaded_file):
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith(".txt") or name.endswith(".csv"):
        return file_bytes.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join([p.extract_text() or "" for p in reader.pages])

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])

    raise ValueError("Unsupported file type")

# -----------------------------
# ORIGINAL DETECTION (v1)
# -----------------------------
def classify_v1(text):
    score = 0

    if "confidential" in text.lower():
        score += 30
    if "salary" in text.lower():
        score += 25
    if "price" in text.lower():
        score += 20
    if "@" in text:
        score += 5

    if score < 15:
        return "Public", score
    elif score < 35:
        return "Internal", score
    elif score < 70:
        return "Confidential", score
    else:
        return "Highly Confidential", score

# -----------------------------
# ADVANCED DETECTION (v2)
# -----------------------------
def detect_sensitive(text):
    findings = []
    score = 0

    patterns = {
        "salary": (r"\$\d{2,6}", 25),
        "email": (r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", 5),
        "ssn": (r"\d{3}-\d{2}-\d{4}", 40),
        "confidential": (r"confidential|internal use only|do not distribute", 30),
        "pricing": (r"price|cost|rate|discount", 20)
    }

    for key, (pattern, weight) in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            findings.append(Finding(key, len(matches), matches[:3], weight))
            score += weight * len(matches)

    return score, findings

def classify_v2(score):
    if score < 15:
        return "Public"
    elif score < 35:
        return "Internal"
    elif score < 70:
        return "Confidential"
    else:
        return "Restricted"

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Confidentiality Classifier", layout="wide")

st.title("AI Document Confidentiality Classifier (Full Version)")

# Session state
if "review_queue" not in st.session_state:
    st.session_state.review_queue = []

if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "txt", "csv"],
    accept_multiple_files=True
)

text_input = st.text_area("Or paste text here")

if st.button("Run Classification"):
    documents = []

    if text_input:
        documents.append(("pasted_text", text_input))

    for file in uploaded_files or []:
        try:
            text = extract_text(file)
            documents.append((file.name, text))
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    for name, text in documents:
        st.subheader(name)

        # V1
        label_v1, score_v1 = classify_v1(text)
        st.write(f"V1 → {label_v1} (Score: {score_v1})")

        # V2
        score_v2, findings = detect_sensitive(text)
        label_v2 = classify_v2(score_v2)

        st.write(f"V2 → {label_v2} (Score: {score_v2})")

        st.write("Findings:")
        for f in findings:
            st.write(f"- {f.category} ({f.count}) examples: {f.examples}")

        # Add to review queue
        if label_v2 in ["Confidential", "Restricted"]:
            st.session_state.review_queue.append({
                "doc": name,
                "text": text,
                "label": label_v2,
                "time": datetime.now()
            })

        # Log
        st.session_state.audit_log.append({
            "doc": name,
            "time": datetime.now(),
            "label": label_v2,
            "score": score_v2
        })

# Review Queue
st.header("Review Queue")
for i, item in enumerate(st.session_state.review_queue):
    with st.expander(f"{item['doc']} - {item['label']}"):
        st.write(item["text"][:300])

        if st.button("Approve", key=f"approve_{i}"):
            st.session_state.review_queue.pop(i)
            st.success("Approved")

# Audit Log
st.header("Audit Log")
if st.session_state.audit_log:
    df = pd.DataFrame(st.session_state.audit_log)
    st.dataframe(df)
