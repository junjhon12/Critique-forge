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
