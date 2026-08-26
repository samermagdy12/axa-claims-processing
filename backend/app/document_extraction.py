from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any


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
    structure: dict[str, Any] | None = None


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
        # Retain the established strategy string for API consumers.
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
def _ocr_pipelines():
    """Load PP-StructureV3 once per language, with layout processing enabled.

    PP-OCRv5 is used for English. PaddleOCR's current Arabic recognition model
    is PP-OCRv3, so its supplementary pass preserves Arabic and mixed-language
    documents instead of relying on the English model for Arabic text.
    """
    from paddleocr import PPStructureV3

    shared_options = {
        "use_doc_orientation_classify": True,
        "use_doc_unwarping": True,
        "use_textline_orientation": True,
        "use_table_recognition": True,
        "use_formula_recognition": False,
        "use_seal_recognition": False,
    }
    return (
        ("english", PPStructureV3(lang="en", ocr_version="PP-OCRv5", **shared_options)),
        ("arabic", PPStructureV3(lang="ar", ocr_version="PP-OCRv3", **shared_options)),
    )


def _extract_images_with_ocr(images: list, strategy: str) -> ExtractedDocument:
    pages: list[dict[str, Any]] = []
    try:
        pipelines = _ocr_pipelines()
        for page_index, image in enumerate(images):
            page = _extract_page_structure(image, pipelines, page_index)
            pages.append(page)
    except Exception as exc:
        raise DocumentExtractionError("OCR could not read the document") from exc
    blocks = [block for page in pages for block in page["blocks"]]
    text = _normalise_text("\n".join(block["text"] for block in blocks))
    if not text:
        raise DocumentExtractionError("OCR could not find readable text in the document")
    confidences = [block["confidence"] for block in blocks if block["confidence"] is not None]
    structure = {
        "version": 1,
        "reading_order": "top_to_bottom_left_to_right",
        "pages": pages,
    }
    return ExtractedDocument(strategy=strategy, text=text, confidence=sum(confidences) / len(confidences) if confidences else None, structure=structure)


def _extract_page_structure(image, pipelines, page_index: int) -> dict[str, Any]:
    import numpy as np

    page_blocks: list[dict[str, Any]] = []
    layout: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    orientation: int | None = None
    image_array = np.asarray(image.convert("RGB"))
    for language, pipeline in pipelines:
        for prediction in pipeline.predict(image_array):
            payload = _prediction_payload(prediction)
            if orientation is None:
                orientation = _orientation(payload)
            layout.extend(_layout_blocks(payload))
            tables.extend(_table_blocks(payload))
            page_blocks.extend(_ocr_blocks(payload, language))
    blocks = _deduplicate_and_sort_blocks(page_blocks)
    return {"page": page_index + 1, "orientation": orientation, "blocks": blocks, "layout": layout, "tables": tables}


def _prediction_payload(prediction: Any) -> dict[str, Any]:
    if isinstance(prediction, dict):
        payload = prediction
    else:
        value = getattr(prediction, "json", None)
        value = value() if callable(value) else value
        if isinstance(value, str):
            payload = json.loads(value)
        elif isinstance(value, dict):
            payload = value
        else:
            payload = dict(prediction)
    return payload.get("res", payload)


def _orientation(payload: dict[str, Any]) -> int | None:
    value = payload.get("doc_preprocessor_res", {}).get("angle")
    return int(value) if isinstance(value, (int, float)) else None


def _ocr_blocks(payload: dict[str, Any], language: str) -> list[dict[str, Any]]:
    result = payload.get("overall_ocr_res", {})
    texts = result.get("rec_texts", []) or []
    scores = result.get("rec_scores", []) or []
    polygons = result.get("rec_polys", result.get("dt_polys", [])) or []
    blocks = []
    for index, text in enumerate(texts):
        cleaned = str(text).strip()
        if not cleaned:
            continue
        score = scores[index] if index < len(scores) else None
        blocks.append({
            "type": "text",
            "text": cleaned,
            "confidence": float(score) if isinstance(score, (int, float)) else None,
            "bbox": _bbox(polygons[index]) if index < len(polygons) else None,
            "language_pass": language,
        })
    return blocks


def _layout_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    boxes = payload.get("layout_det_res", {}).get("boxes", []) or []
    return [
        {"type": box.get("label", "unknown"), "bbox": _number_list(box.get("coordinate")), "confidence": _float_or_none(box.get("score"))}
        for box in boxes if isinstance(box, dict)
    ]


def _table_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tables = payload.get("table_res_list", payload.get("table_res", [])) or []
    if isinstance(tables, dict):
        tables = [tables]
    return [{"html": item.get("pred_html"), "bbox": _number_list(item.get("bbox"))} for item in tables if isinstance(item, dict)]


def _deduplicate_and_sort_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, tuple | None], dict[str, Any]] = {}
    for block in blocks:
        bbox = tuple(block["bbox"]) if block["bbox"] else None
        key = (block["text"], bbox)
        existing = unique.get(key)
        if existing is None or (block["confidence"] or 0) > (existing["confidence"] or 0):
            unique[key] = block
    return sorted(unique.values(), key=lambda block: ((block["bbox"] or [0, 0])[1], (block["bbox"] or [0, 0])[0]))


def _bbox(points: Any) -> list[float] | None:
    values = _number_list(points)
    if len(values) < 4:
        return None
    xs, ys = values[::2], values[1::2]
    return [min(xs), min(ys), max(xs), max(ys)]


def _number_list(value: Any) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        return []
    flattened = [item for group in value for item in group] if value and isinstance(value[0], (list, tuple)) else value
    return [float(item) for item in flattened if isinstance(item, (int, float))]


def _float_or_none(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _normalise_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
