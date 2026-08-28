"""
Text extraction from an uploaded report file.

PDFs: try direct text extraction first (fast, exact). If a PDF has almost
no extractable text (i.e. it's a scan), fall back to rasterizing each page
and running OCR on the image, same as a photographed report.

Images (jpg/jpeg/png): OCR directly.

Both paths degrade gracefully: if Tesseract isn't installed on the host,
we raise a clear, catchable error instead of crashing the request, so the
rest of the app still runs -- the report upload endpoint turns this into
a normal 4xx response asking the user to check their file or the server
OCR setup, rather than a 500.
"""
import io
from typing import Tuple

MIN_CHARS_ASSUME_TEXT_PDF = 40


class OCRUnavailableError(RuntimeError):
    pass


def _ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise OCRUnavailableError(f"OCR dependencies not installed: {e}")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        raise OCRUnavailableError(
            "Tesseract OCR binary not found on this server. Install tesseract-ocr "
            "(see README) or upload a text-based PDF instead."
        )


def _extract_pdf_text(pdf_bytes: bytes) -> Tuple[str, bool]:
    """Returns (text, used_ocr_fallback)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise OCRUnavailableError(f"PDF dependencies not installed: {e}")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    text = "\n".join(text_parts).strip()

    if len(text) >= MIN_CHARS_ASSUME_TEXT_PDF:
        return text, False

    # Likely a scanned PDF with no embedded text layer -- rasterize and OCR.
    ocr_parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        ocr_parts.append(_ocr_image_bytes(pix.tobytes("png")))
    return "\n".join(ocr_parts).strip(), True


def extract_text(file_bytes: bytes, filename: str) -> dict:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text, used_ocr = _extract_pdf_text(file_bytes)
        return {"text": text, "method": "ocr_fallback" if used_ocr else "pdf_text_layer"}
    if lower.endswith((".jpg", ".jpeg", ".png")):
        text = _ocr_image_bytes(file_bytes)
        return {"text": text, "method": "image_ocr"}
    raise ValueError(f"Unsupported file type for: {filename}. Use PDF, JPG, JPEG, or PNG.")
