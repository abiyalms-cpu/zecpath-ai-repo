"""
Reads a PDF resume and returns its raw text.

PDFs store text where it is drawn, not as sentences. So we use each line's
position on the page to (1) read two-column layouts one column at a time and
(2) stitch back sentences that were split because they ran out of room.
"""

import re

import pdfplumber

from utils.logger import get_logger

logger = get_logger(__name__)

BULLET_START = re.compile(r"^\s*[●•▪■◦○▫◆*–-]\s")


def starts_new_item(text: str) -> bool:
    """True if this line begins a bullet or is an ALL-CAPS heading."""
    return bool(BULLET_START.match(text)) or text.isupper()


def find_gutter(page):
    """Return the x-position of the empty strip between two columns, or None."""
    words = page.extract_words()
    if len(words) < 30:
        return None

    # Look for the x-position that the fewest words cross over
    best_x, best_cover = None, None
    x = int(page.width * 0.2)
    while x < page.width * 0.8:
        cover = sum(1 for w in words if w["x0"] < x < w["x1"])
        if best_cover is None or cover < best_cover:
            best_x, best_cover = x, cover
        x += 2

    if best_cover > 2:                   # words cross it, so it is not a gutter
        return None

    # A real gutter has plenty of text on both sides of it
    left = sum(1 for w in words if w["x1"] <= best_x)
    right = sum(1 for w in words if w["x0"] >= best_x)
    if left < 0.15 * len(words) or right < 0.15 * len(words):
        return None
    return best_x


def font_of(char) -> tuple:
    return (char["fontname"], round(char["size"]))


def first_word_width(line) -> float:
    """Approximate width of the first word on a line."""
    text = line["text"]
    average_char_width = (line["x1"] - line["x0"]) / max(len(text), 1)
    return len(text.split()[0]) * average_char_width


def read_region(region) -> list:
    """Read one column (or a whole page) and rejoin its wrapped lines."""
    lines = region.extract_text_lines(return_chars=True)
    if not lines:
        return []

    right_edge = max(line["x1"] for line in lines)

    out = []
    previous_x0 = 0
    previous_x1 = 0
    previous_font = None
    for line in lines:
        text = line["text"]
        # The previous line wrapped if the first word of this line would not
        # have fitted in the space it had left before the right edge.
        did_not_fit = (right_edge - previous_x1) < first_word_width(line)
        is_continuation = (
            out
            and did_not_fit
            and not starts_new_item(text)
            and line["x0"] >= previous_x0 - 1                    # same indent
            and font_of(line["chars"][0]) == previous_font       # same font
        )
        if is_continuation:
            joiner = "" if out[-1].endswith("-") else " "        # e- + commerce
            out[-1] = out[-1] + joiner + text
        else:
            out.append(text)
            previous_x0 = line["x0"]
        previous_x1 = line["x1"]
        previous_font = font_of(line["chars"][-1])
    return out


def read_pdf(file_path: str) -> str:
    """Return all the text in a PDF, in reading order."""
    logger.info(f"Reading PDF: {file_path}")

    lines = []
    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            gutter = find_gutter(page)
            if gutter is None:
                regions = [page]
            else:
                logger.info(f"Two-column layout on page {page_number}")
                regions = [                                # left column first
                    page.crop((0, 0, gutter, page.height)),
                    page.crop((gutter, 0, page.width, page.height)),
                ]
            for region in regions:
                lines.extend(read_region(region))

    return "\n".join(lines)