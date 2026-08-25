from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


VISUAL_EVIDENCE_DOCUMENT_TYPES = {"Photos of Damage", "Spare Key"}
PDF_MIME_TYPES = {"application/pdf"}
DOCX_MIME_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
TEXT_MIME_TYPES = {"text/plain"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class DocumentExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedDocument:
    strategy: str
    text: str
    confidence: float | None


def extract_document_content(path: Path, mime_type: str, document_type: str) -> ExtractedDocument:
    if document_type in VISUAL_EVIDENCE_DOCUMENT_TYPES:
        return ExtractedDocument(strategy="visual_evidence_preserved", text="", confidence=None)

    suffix = path.suffix.lower()
    normalized_mime_type = (mime_type or "").lower()
    if normalized_mime_type in PDF_MIME_TYPES or suffix == ".pdf":
        text = _extract_pdf_text(path)
        if text:
            return ExtractedDocument(strategy="native_pdf_text", text=text, confidence=1.0)
        return _extract_scanned_pdf_text(path)
    if normalized_mime_type in DOCX_MIME_TYPES or suffix == ".docx":
        return ExtractedDocument(strategy="native_docx_text", text=_extract_docx_text(path), confidence=1.0)
    if normalized_mime_type in TEXT_MIME_TYPES or suffix == ".txt":
        return ExtractedDocument(strategy="native_text", text=_read_plain_text(path), confidence=1.0)
    if normalized_mime_type in IMAGE_MIME_TYPES or suffix in IMAGE_SUFFIXES:
        return _extract_image_text(path, strategy="image_ocr")
    raise DocumentExtractionError("This file type is not supported for document content extraction")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        return _normalise_text("\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception as exc:
        raise DocumentExtractionError("The PDF could not be read") from exc


def _extract_scanned_pdf_text(path: Path) -> ExtractedDocument:
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(path)
        images = []
        for page in document:
            bitmap = page.render(scale=2)
            images.append(bitmap.to_pil())
        document.close()
    except Exception as exc:
        raise DocumentExtractionError("The scanned PDF could not be rendered") from exc
    try:
        return _extract_images_with_ocr(images, strategy="scanned_pdf_ocr")
    finally:
        for image in images:
            image.close()


def _extract_image_text(path: Path, strategy: str) -> ExtractedDocument:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return _extract_images_with_ocr([image.copy()], strategy=strategy)
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("The image could not be read") from exc


def _extract_docx_text(path: Path) -> str:
    try:
        from docx import Document

        document = Document(path)
        rows = [paragraph.text for paragraph in document.paragraphs]
        rows.extend(" | ".join(cell.text for cell in row.cells) for table in document.tables for row in table.rows)
        text = _normalise_text("\n".join(rows))
    except Exception as exc:
        raise DocumentExtractionError("The DOCX file could not be read") from exc
    if not text:
        raise DocumentExtractionError("The DOCX file contains no extractable text")
    return text


def _read_plain_text(path: Path) -> str:
    try:
        text = _normalise_text(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("The text file is not UTF-8 encoded") from exc
    except OSError as exc:
        raise DocumentExtractionError("The text file could not be read") from exc
    if not text:
        raise DocumentExtractionError("The text file contains no extractable text")
    return text


@lru_cache(maxsize=1)
def _ocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _extract_images_with_ocr(images: list, strategy: str) -> ExtractedDocument:
    lines: list[str] = []
    confidences: list[float] = []
    try:
        engine = _ocr_engine()
        for image in images:
            output, _ = engine(image)
            for item in output or []:
                lines.append(item[1])
                confidences.append(float(item[2]))
    except Exception as exc:
        raise DocumentExtractionError("OCR could not read the document") from exc
    text = _normalise_text("\n".join(lines))
    if not text:
        raise DocumentExtractionError("OCR could not find readable text in the document")
    return ExtractedDocument(strategy=strategy, text=text, confidence=sum(confidences) / len(confidences) if confidences else None)


def _normalise_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
