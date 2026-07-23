from typing import cast

import PyPDF2
import docx
from streamlit.runtime.uploaded_file_manager import UploadedFile


def extract_text_from_file(uploaded_file: UploadedFile) -> str:
    """Safely extracts text based on file extension."""
    filename: str = cast(str, uploaded_file.name).lower()
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            text += (extracted or "") + "\n"
        return text
    elif filename.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        # Fallback for plain text like .txt or .md
        return uploaded_file.getvalue().decode("utf-8")


def extract_text_from_files(uploaded_files: list[UploadedFile]) -> list[tuple[str, str]]:
    """Extracts text from multiple uploaded chapter files, preserving upload order.

    Returns a list of (filename, text) pairs."""
    return [(cast(str, f.name), extract_text_from_file(f)) for f in uploaded_files]
