"""
Regression tests for the hybrid-PDF extraction bug: a PDF whose embedded
text layer is real (letterhead, patient details, accreditation numbers)
but whose actual results table is a scanned image. The old whole-document
character-count heuristic was fooled by the letterhead alone clearing the
"looks like a text PDF" threshold, so the table image -- containing the
real lab values -- was never OCR'd and the values were silently lost.

These tests build a synthetic PDF of exactly that shape (real text +
embedded image covering most of the page) and assert the real values in
the image are recovered. Skipped automatically if PyMuPDF, Pillow, or a
working Tesseract binary aren't available on the host running the tests --
same graceful-skip philosophy as the rest of the OCR-dependent code.
"""
import io

import pytest

fitz = pytest.importorskip("fitz", reason="PyMuPDF not installed")
Image = pytest.importorskip("PIL.Image", reason="Pillow not installed")
ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="Pillow not installed")

from app.ocr.extraction import extract_text, OCRUnavailableError, _page_image_coverage


_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _build_hybrid_pdf(table_lines) -> bytes:
    """A one-page PDF: real embedded text (letterhead-only, >40 chars) plus
    a portrait scanned-looking image containing the real results table."""
    img = Image.new("RGB", (1400, 1700), "white")
    draw = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(_FONT_PATH, 36)
    except Exception:
        font = None
    for i, line in enumerate(table_lines):
        draw.text((30, 60 + i * 80), line, fill="black", font=font)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 50), "AN ISO 9001:2015 CERTIFIED LABORATORY")
    page.insert_text((50, 70), "REG/REF: DWH 8515 PAGE 1 of 3")
    page.insert_text((50, 90), "Patient: Anjana AGE/GENDER 48 Yrs./Male")
    page.insert_image(fitz.Rect(30, 150, 580, 760), stream=img_bytes.read())
    return doc.tobytes()


def _tesseract_available() -> bool:
    try:
        extract_text(_build_hybrid_pdf(["Hemoglobin 12.2 g/dL 13-17"]), "probe.pdf")
        return True
    except OCRUnavailableError:
        return False


@pytest.mark.skipif(not _tesseract_available(), reason="Tesseract binary not available on this host")
def test_hybrid_pdf_with_letterhead_text_and_scanned_table_extracts_real_values():
    pdf_bytes = _build_hybrid_pdf([
        "Hemoglobin 12.2 g/dL 13-17",
        "Triglycerides 217.27 mg/dL 30 - 200",
        "HDL Cholesterol 38.34 mg/dL 40 - 60",
    ])

    # Sanity check the fixture actually reproduces the old bug's precondition:
    # embedded text alone clears the old whole-document 40-char threshold.
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc[0].get_text().strip()) >= 40
    assert _page_image_coverage(doc[0]) >= 0.35

    result = extract_text(pdf_bytes, "hybrid_report.pdf")

    # The letterhead is real text, but the table is a scanned image -- OCR
    # must have run for this page to recover the real values at all.
    assert result["method"] == "ocr_fallback"
    assert "Hemoglobin" in result["text"]
    assert "12.2" in result["text"]
    assert "Triglycerides" in result["text"]
    assert "217.27" in result["text"]


@pytest.mark.skipif(not _tesseract_available(), reason="Tesseract binary not available on this host")
def test_pure_text_pdf_does_not_trigger_unnecessary_ocr():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 50), "Hemoglobin: 13.5 g/dL (12.0-17.0)")
    page.insert_text((50, 70), "Fasting Glucose: 92 mg/dL (70-100)")
    pdf_bytes = doc.tobytes()

    result = extract_text(pdf_bytes, "plain_text_report.pdf")

    # No images at all on this page -- must stay on the fast, exact text
    # path rather than needlessly OCR'ing a page that has no scanned content.
    assert result["method"] == "pdf_text_layer"
    assert "Hemoglobin" in result["text"]
