"""
Main entry point of the resume text extraction engine.

Give it a resume (PDF or DOCX) and it picks the right reader, cleans the
text, and returns the result. It can also process a whole folder and save
each result as a structured JSON file.
"""

import json
import os
from datetime import datetime

from parsers.docx_reader import read_docx
from parsers.pdf_reader import read_pdf
from parsers.text_cleaner import clean_text
from utils.logger import get_logger

logger = get_logger(__name__)

READERS = {".docx": read_docx, ".pdf": read_pdf}


def extract_resume_text(file_path: str) -> dict:
    """Extract and clean the text of one resume."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in READERS:
        raise ValueError(f"Unsupported file type: {ext}")

    raw_text = READERS[ext](file_path)
    text = clean_text(raw_text)

    if text:
        status = "ok"
    else:
        status = "no_text_found"
        logger.warning(f"No text found in {file_path} (scanned or image-only?)")  

    return {
        "source_file": os.path.basename(file_path),
        "file_type": ext.lstrip("."),
        "status": status,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "char_count": len(text),
        "line_count": len(text.splitlines()),
        "text": text,
    }


def extract_folder(input_dir: str, output_dir: str) -> list:
    """Extract every PDF/DOCX in a folder and save each one as a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for name in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext not in READERS:
            continue
        try:
            result = extract_resume_text(os.path.join(input_dir, name))
        except Exception as error:
            # One bad file should not stop the rest of the batch
            logger.error(f"Failed to extract {name}: {error}")
            continue

        out_name = os.path.splitext(name)[0] + "_" + ext.lstrip(".") + ".json"
        with open(os.path.join(output_dir, out_name), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {out_name}")
        results.append(result)

    return results