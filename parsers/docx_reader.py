"""
Reads a DOCX resume and returns its raw text.

Handles both normal paragraphs and tables, in the order they appear in the
document, so nothing inside a table is lost.
"""

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from utils.logger import get_logger

logger = get_logger(__name__)


def is_bullet(paragraph) -> bool:
    """True if Word treats this paragraph as a bullet/list item."""
    pPr = paragraph._p.pPr
    if pPr is not None and pPr.numPr is not None:
        return True                      # bullet set directly on the paragraph
    style = paragraph.style
    return style is not None and style.name.startswith("List")   # bullet set by style


def table_to_lines(table) -> list:
    """Turn each table row into one line, cells separated by ' | '."""
    lines = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = " ".join(cell.text.split())
            # Merged cells repeat their text in python-docx, so skip repeats
            if text and (not cells or cells[-1] != text):
                cells.append(text)
        if cells:
            lines.append(" | ".join(cells))
    return lines


def read_docx(file_path: str) -> str:
    """Return all the text in a DOCX file, one paragraph or table row per line."""
    logger.info(f"Reading DOCX: {file_path}")

    doc = Document(file_path)
    lines = []
    # Walk the document body in order so tables stay where they belong
    for block in doc.element.body.iterchildren():
        if block.tag.endswith("}p"):
            paragraph = Paragraph(block, doc)
            text = paragraph.text
            if is_bullet(paragraph) and text.strip():
                text = "● " + text
            lines.append(text)
        elif block.tag.endswith("}tbl"):
            lines.extend(table_to_lines(Table(block, doc)))

    return "\n".join(lines)