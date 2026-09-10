"""
Text extraction from an uploaded report file.

PDFs: decided PAGE BY PAGE, not once for the whole document. Real lab
reports are frequently "hybrid" PDFs: a digitally-generated letterhead,
patient details, and footer disclaimer (real embedded text) wrapped around
a SCANNED IMAGE of the actual results table.

Each page is OCR'd if EITHER:
  - it has too little embedded text to plausibly be the results page, OR
  - a large fraction of the page is covered by embedded images.

Images (jpg/jpeg/png): OCR directly.

Both paths degrade gracefully: if Tesseract isn't installed on the host,
we raise a clear, catchable error instead of crashing the request.
"""

import io
from typing import Tuple


# A page with fewer embedded characters than this is treated as having no
# real text layer for that page.
MIN_CHARS_ASSUME_TEXT_PAGE = 40


# If embedded images cover at least this fraction of a page's area,
# OCR is used even when some embedded text exists.
IMAGE_COVERAGE_OCR_THRESHOLD = 0.35


class OCRUnavailableError(RuntimeError):
    pass


def _ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise OCRUnavailableError(
            f"OCR dependencies not installed: {e}"
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))

        return pytesseract.image_to_string(image)

    except pytesseract.TesseractNotFoundError:
        raise OCRUnavailableError(
            "Tesseract OCR binary not found on this server. "
            "Install tesseract-ocr (see README) or upload a "
            "text-based PDF instead."
        )


def _page_image_coverage(page) -> float:
    """Fraction (0-1) of a page's area covered by embedded raster images."""

    try:
        infos = page.get_image_info()
    except Exception:
        return 0.0

    page_area = page.rect.width * page.rect.height

    if page_area <= 0 or not infos:
        return 0.0

    covered = 0.0

    for info in infos:
        bbox = info.get("bbox")

        if not bbox:
            continue

        x0, y0, x1, y1 = bbox

        covered += (
            max(0.0, x1 - x0)
            * max(0.0, y1 - y0)
        )

    return min(1.0, covered / page_area)


def _page_text_or_ocr(page) -> Tuple[str, bool]:
    """Returns (text_for_this_page, used_ocr_for_this_page)."""

    page_number = page.number + 1

    page_text = page.get_text().strip()

    coverage = _page_image_coverage(page)

    needs_ocr = (
        len(page_text) < MIN_CHARS_ASSUME_TEXT_PAGE
        or coverage >= IMAGE_COVERAGE_OCR_THRESHOLD
    )

    print(
        f"OCR DEBUG: page={page_number}, "
        f"text_chars={len(page_text)}, "
        f"image_coverage={coverage:.2f}, "
        f"needs_ocr={needs_ocr}",
        flush=True,
    )

    if not needs_ocr:
        print(
            f"OCR DEBUG: page={page_number} using embedded text",
            flush=True,
        )

        return page_text, False

    print(
        f"OCR DEBUG: page={page_number} rendering at 200 DPI",
        flush=True,
    )

    pix = page.get_pixmap(dpi=200)

    print(
        f"OCR DEBUG: page={page_number} rendering complete",
        flush=True,
    )

    print(
        f"OCR DEBUG: page={page_number} starting Tesseract",
        flush=True,
    )

    ocr_text = _ocr_image_bytes(
        pix.tobytes("png")
    ).strip()

    print(
        f"OCR DEBUG: page={page_number} Tesseract complete, "
        f"chars={len(ocr_text)}",
        flush=True,
    )

    combined = "\n".join(
        part
        for part in (page_text, ocr_text)
        if part
    )

    return combined, True


def _extract_pdf_text(pdf_bytes: bytes) -> Tuple[str, bool]:
    """Returns (text, used_ocr_for_any_page)."""

    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise OCRUnavailableError(
            f"PDF dependencies not installed: {e}"
        )

    print(
        f"OCR DEBUG: opening PDF, bytes={len(pdf_bytes)}",
        flush=True,
    )

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    print(
        f"OCR DEBUG: PDF opened, pages={len(doc)}",
        flush=True,
    )

    text_parts = []
    used_ocr = False

    for page in doc:
        page_text, page_used_ocr = _page_text_or_ocr(page)

        text_parts.append(page_text)

        used_ocr = used_ocr or page_used_ocr

    text = "\n".join(
        part
        for part in text_parts
        if part
    ).strip()

    print(
        f"OCR DEBUG: PDF extraction complete, "
        f"text_chars={len(text)}, "
        f"used_ocr={used_ocr}",
        flush=True,
    )

    return text, used_ocr


def extract_text(file_bytes: bytes, filename: str) -> dict:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text, used_ocr = _extract_pdf_text(file_bytes)

        return {
            "text": text,
            "method": (
                "ocr_fallback"
                if used_ocr
                else "pdf_text_layer"
            ),
        }

    if lower.endswith((".jpg", ".jpeg", ".png")):
        print(
            "OCR DEBUG: processing image file",
            flush=True,
        )

        text = _ocr_image_bytes(file_bytes)

        print(
            f"OCR DEBUG: image OCR complete, chars={len(text)}",
            flush=True,
        )

        return {
            "text": text,
            "method": "image_ocr",
        }

    raise ValueError(
        f"Unsupported file type for: {filename}. "
        "Use PDF, JPG, JPEG, or PNG."
    )