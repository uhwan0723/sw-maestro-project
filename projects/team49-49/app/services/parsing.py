from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def parse_document(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension in TEXT_EXTENSIONS:
        return content.decode("utf-8-sig").strip()
    if extension == ".csv":
        dataframe = pd.read_csv(StringIO(content.decode("utf-8-sig")))
        return dataframe.to_csv(index=False).strip()
    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if not text:
            raise ValueError("PDF text extraction failed. Upload a text-based PDF or convert it to txt/md.")
        return text
    raise ValueError(f"Unsupported file type: {extension or 'unknown'}")
